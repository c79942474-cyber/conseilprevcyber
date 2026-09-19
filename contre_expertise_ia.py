# -*- coding: utf-8 -*-
"""CONTRE-EXPERTISE D'UNE AI FACTORY EN COURS DE DÉPLOIEMENT.

CE MODULE N'EST NI `ia_factory` NI `chaine_autonomie`, et les trois se
complètent sans se recouvrir :

    · `ia_factory`        CONSTRUIT l'usine — postes, planning, chiffrage ;
    · `chaine_autonomie`  COTE UN SYSTÈME — cinq maillons, autonomie contre
                          maîtrise, le pire écart commande ;
    · celui-ci            CONTESTE LE PROGRAMME — ce qui part en production
                          pendant qu'on écrit encore le cadre de sécurité.

« Contre-expertise » n'est pas « évaluation ». Évaluer, c'est noter ce qui
existe. Contester, c'est s'adresser à des choix DÉJÀ FAITS par des équipes qui
les défendent, avec un calendrier business derrière elles.

═══════════════════════════════════════════════════════════════════════════
 LA DÉCISION QUI COMMANDE TOUTES LES AUTRES
═══════════════════════════════════════════════════════════════════════════

    QU'EST-CE QUI EST DÉJÀ EN PRODUCTION SANS LE CONTRÔLE QUI LE COUVRE ?

Une usine « en cours de déploiement » veut dire que des cas d'usage passent en
production PENDANT qu'on écrit le cadre. Chaque cas parti avant que son
contrôle prérequis n'existe crée une DETTE D'ANTÉRIORITÉ, et cette dette a
trois propriétés qui la rendent différente de tout le reste :

  1. ELLE NE SE REMBOURSE JAMAIS AU MÊME PRIX. Poser un filtrage sur un cas
     d'usage avant sa mise en service, c'est une configuration. Le poser
     après, c'est une reprise sur un service que des métiers utilisent déjà,
     avec des faux positifs qui deviennent des incidents de production.

  2. ELLE EST INVISIBLE DANS UN SCORE DE MATURITÉ. Un tableau de maturité
     mesure ce qu'on A. Il ne mesure pas ce qui est PARTI SANS. Une usine qui
     monte de 40 % à 70 % de maturité pendant que douze cas d'usage passent
     en production sans contrôle a l'air de progresser, et sa dette double.

  3. ELLE SE CHIFFRE EN JOURS, ce qui la rend opposable. Ce n'est pas un avis
     de sécurité : c'est un écart entre deux dates, et personne ne discute
     une soustraction.

═══════════════════════════════════════════════════════════════════════════
 CE QUI REND L'ALERTE AU MANAGEMENT ARITHMÉTIQUE
═══════════════════════════════════════════════════════════════════════════

Alerter quand « les ambitions business ne sont pas compatibles avec les
exigences de sécurité » est la partie du métier qui se transmet le plus mal,
parce qu'elle se joue en réunion et qu'elle ressemble à une opinion contre une
autre. Elle cesse d'y ressembler dès qu'on pose les deux nombres :

    une ambition a une DATE et un PÉRIMÈTRE ;
    un contrôle a un DÉLAI DE MISE EN PLACE ;
    l'incompatibilité est une soustraction.

D'où le champ `delai_jours` sur chaque contrôle. Sans lui, le module rendrait
des avis ; avec lui, il rend des écarts.

ET L'ALERTE PORTE TOUJOURS SES TROIS ISSUES : réduire le périmètre, décaler la
date, ou accepter le risque par écrit avec un porteur nommé. Un « non » sans
issue ne remonte pas — il se contourne, et celui qui l'a porté apprend
l'arbitrage après coup.

═══════════════════════════════════════════════════════════════════════════
 CE QUE CE MODULE NE FAIT PAS
═══════════════════════════════════════════════════════════════════════════

IL NE CHIFFRE AUCUN DÉLAI À VOTRE PLACE. Les `delai_jours` des contrôles sont
des ORDRES DE GRANDEUR de mise en place dans un grand compte régulé, pas des
engagements ; chacun porte ce qu'il suppose. Un délai affiché comme une
certitude serait une promesse que rien ne tient, et c'est le chiffre qu'un
comité retient.

IL N'AUDITE RIEN. Personne n'est venu voir, rien n'a été éprouvé. Il structure
un constat déclaré, et la restitution le dit avant son premier chiffre.

IL NE REMPLACE PAS LA COTATION DES SYSTÈMES. La dette dit ce qui est parti
sans contrôle ; `chaine_autonomie` dit ce qu'un système peut faire. Un cas
d'usage parfaitement couvert par des contrôles existants peut rester
dangereux si sa chaîne d'autonomie est ouverte — le module renvoie à l'autre
plutôt que de prétendre s'en passer.
"""

import datetime

import chaine_autonomie


# ═══════════════════════════════════════════════════════════════════════════
#  LES SOURCES PROPRES À CE MODULE
# ═══════════════════════════════════════════════════════════════════════════
#
# LES AUTRES SONT CELLES DE `chaine_autonomie`, ET ON NE LES RECOPIE PAS :
# OWASP agentique, MITRE ATLAS, ANSSI, ISO/IEC 27090 y sont déjà déclarées
# avec leur licence. Une seconde table les ferait diverger au premier
# amendement. `sources()` rend les deux, en le disant.

SOURCES = (
    {"nom": "Règlement (UE) 2022/2554 — résilience opérationnelle numérique "
            "du secteur financier (DORA)",
     "court": "DORA",
     "nature": "texte juridique",
     "url": "http://data.europa.eu/eli/reg/2022/2554/oj",
     "licence": "Réutilisation autorisée — décision 2011/833/UE, avec "
                "attribution. Seul le texte publié au Journal officiel fait foi.",
     "lu": True},
    {"nom": "Directive (UE) 2022/2555 — mesures pour un niveau élevé commun "
            "de cybersécurité (NIS 2)",
     "court": "NIS 2",
     "nature": "texte juridique",
     "url": "http://data.europa.eu/eli/dir/2022/2555/oj",
     "licence": "Réutilisation autorisée — décision 2011/833/UE, avec "
                "attribution.",
     "lu": True},
    {"nom": "Règlement (UE) 2024/1689 établissant des règles harmonisées "
            "concernant l'intelligence artificielle",
     "court": "Règlement sur l'IA",
     "nature": "texte juridique",
     "url": "http://data.europa.eu/eli/reg/2024/1689/oj",
     "licence": "Réutilisation autorisée — décision 2011/833/UE, avec "
                "attribution.",
     "lu": True},
)


def sources():
    """Les sources de ce module ET celles de la chaîne d'autonomie.

    POURQUOI LES DEUX ENSEMBLE. Le lecteur d'une contre-expertise reçoit une
    analyse qui s'appuie sur les deux modules ; lui servir la moitié du
    registre lui ferait croire que le reste n'est adossé à rien.
    """
    return {
        "propres": list(SOURCES),
        "heritees": list(chaine_autonomie.SOURCES),
        "dit": "Les sources du catalogue de menaces — OWASP agentique, MITRE "
               "ATLAS, ANSSI, ISO/IEC 27090 — sont celles de la chaîne "
               "d'autonomie et ne sont pas recopiées ici : deux tables "
               "divergeraient au premier amendement.",
    }


# ═══════════════════════════════════════════════════════════════════════════
#  LES PHASES D'UN DÉPLOIEMENT — ET CE QUI S'Y DÉCIDE VRAIMENT
# ═══════════════════════════════════════════════════════════════════════════
#
# CE QUE CE DÉCOUPAGE APPORTE À UNE CONTRE-EXPERTISE. Arriver sur une usine en
# cours de déploiement sans savoir où elle en est conduit à poser les
# questions de la phase 1 à une équipe qui est en phase 3 — et à perdre en
# dix minutes le crédit dont on a besoin pour les six mois suivants.

PHASES = (
    {"cle": "socle", "rang": 0, "nom": "Socle en construction",
     "ce_qui_s_y_decide": "Le choix des modèles, l'hébergement, le réseau, "
                          "l'identité. Tout ce qui sera irréversible.",
     "la_question": "Ces choix supposent-ils un contrôle qui n'existe pas "
                    "encore, et qui le sait ?",
     "cout_du_retard": "Faible. Rien n'est en production ; une objection "
                       "coûte une réunion."},
    {"cle": "pilotes", "rang": 1, "nom": "Cas d'usage pilotes",
     "ce_qui_s_y_decide": "Ce qu'on s'autorise à faire avec l'IA, sur quelles "
                          "données, et qui valide.",
     "la_question": "Un pilote est-il en train de devenir un service sans que "
                    "personne n'ait prononcé la bascule ?",
     "cout_du_retard": "Modéré. Un pilote s'arrête ; un service non."},
    {"cle": "industrialisation", "rang": 2,
     "nom": "Industrialisation",
     "ce_qui_s_y_decide": "Le passage à l'échelle : plusieurs équipes, "
                          "plusieurs cas d'usage, des agents qui appellent "
                          "d'autres systèmes.",
     "la_question": "Les contrôles suivent-ils le rythme des mises en "
                    "service, ou l'écart se creuse-t-il ?",
     "cout_du_retard": "Élevé. Chaque semaine ajoute des cas d'usage à "
                       "rattraper."},
    {"cle": "generalisation", "rang": 3, "nom": "Généralisation",
     "ce_qui_s_y_decide": "L'ouverture au plus grand nombre, souvent en "
                          "libre-service.",
     "la_question": "Sait-on encore énumérer les cas d'usage en production ?",
     "cout_du_retard": "Très élevé. On ne rattrape plus : on reprend."},
)

PHASES_PAR_CLE = {p["cle"]: p for p in PHASES}


# ═══════════════════════════════════════════════════════════════════════════
#  LES FAMILLES DE CONTRÔLE — ET LEUR DÉLAI, QUI EST LE POINT
# ═══════════════════════════════════════════════════════════════════════════
#
# `delai_jours` EST CE QUI REND L'ALERTE OPPOSABLE, et c'est aussi le champ le
# plus facile à mal lire. Ce sont des ORDRES DE GRANDEUR de mise en place dans
# un grand compte régulé — décision, achat, intégration, recette, bascule —
# pas des engagements. Chaque contrôle dit ce que son délai SUPPOSE ; servi
# sans cette hypothèse, un délai devient une promesse.
#
# ET AUCUN N'EST UN PRODUIT. Le module nomme des FAMILLES : nommer un éditeur
# ferait de la contre-expertise une recommandation d'achat, ce qui est
# exactement ce qu'on reproche aux architectures qu'on vient contester.

# ═══════════════════════════════════════════════════════════════════════════
#  LES ÉQUIPES QUI PORTENT — CAR LE RESPONSABLE SÉCURITÉ IA NE CONSTRUIT RIEN
# ═══════════════════════════════════════════════════════════════════════════
#
# CE QUE CETTE TABLE ÉVITE, ET C'EST LE DÉFAUT CLASSIQUE D'UNE FEUILLE DE
# ROUTE DE SÉCURITÉ : une liste de contrôles que personne n'a accepté de
# construire. Le responsable sécurité IA n'écrit ni le filtrage, ni l'IAM, ni
# la chaîne de production — il fait construire, par des équipes qui ont leur
# propre file d'attente et leurs propres arbitrages.
#
# UN CONTRÔLE SANS ÉQUIPE QUI LE PORTE NE SERA JAMAIS CONSTRUIT. La garde en
# bas de fichier refuse donc tout contrôle orphelin : c'est la seule façon
# d'empêcher une feuille de route de redevenir une liste de vœux.

EQUIPES = (
    {"cle": "data_office", "nom": "Data Office & Services",
     "ce_qu_elle_tient": "La gouvernance de la donnée et des cas d'usage IA, "
                         "l'inventaire, la politique d'usage.",
     "ce_qu_elle_attend_de_vous": "Une position de sécurité qui ne bloque "
                                  "pas l'adoption, et qui se tient devant "
                                  "un métier pressé."},
    {"cle": "integration_projets",
     "nom": "Intégration Sécurité dans les Projets",
     "ce_qu_elle_tient": "Les jalons de sécurité du cycle projet, et le "
                         "refus de passage quand un jalon n'est pas tenu.",
     "ce_qu_elle_attend_de_vous": "Des critères d'entrée et de sortie "
                                  "spécifiques à l'IA — sans eux, elle "
                                  "applique les critères applicatifs, qui "
                                  "ne voient ni le modèle ni l'invite."},
    {"cle": "design_authority", "nom": "Cyber Design Authority",
     "ce_qu_elle_tient": "Les politiques, guides et standards, et leur "
                         "cohérence entre eux.",
     "ce_qu_elle_attend_de_vous": "Des patterns d'architecture, pas des "
                                  "principes. Un standard qui dit « il faut "
                                  "filtrer » ne se met pas en œuvre ; un "
                                  "pattern qui montre où, si."},
    {"cle": "devsecops", "nom": "DevSecOps",
     "ce_qu_elle_tient": "La chaîne de production des applications et des "
                         "modèles, et les contrôles qui s'y branchent.",
     "ce_qu_elle_attend_de_vous": "Des contrôles qui bloquent la fusion "
                                  "plutôt que des consignes. Une consigne "
                                  "sans blocage technique tient trois "
                                  "semaines."},
    {"cle": "cyberdefense", "nom": "Cyberdéfense",
     "ce_qu_elle_tient": "La détection, la réponse, et les exercices "
                         "d'attaque.",
     "ce_qu_elle_attend_de_vous": "Ce qu'il faut journaliser pour qu'un "
                                  "incident IA soit explicable après coup — "
                                  "et la liste n'est pas celle d'une "
                                  "application."},
    {"cle": "vulnerabilites", "nom": "Gestion des vulnérabilités",
     "ce_qu_elle_tient": "Le stock de vulnérabilités, les délais de "
                         "remédiation, la dette.",
     "ce_qu_elle_attend_de_vous": "Une aide mesurable sur le MTTR, pas un "
                                  "outil de plus à administrer."},
    {"cle": "securite_ia", "nom": "Sécurité IA (vous)",
     "ce_qu_elle_tient": "La contre-expertise, l'alerte, et rien d'autre en "
                         "propre.",
     "ce_qu_elle_attend_de_vous": "Que vous ne vous mettiez pas à construire "
                                  ": une équipe de sécurité qui livre "
                                  "elle-même cesse de pouvoir contester."},
)

EQUIPES_PAR_CLE = {e["cle"]: e for e in EQUIPES}


CONTROLES = (
    {"cle": "filtrage_ia", "equipe": "design_authority", "nom": "Filtrage IA (garde-fous entrée et sortie)",
     "famille": "protection",
     "quoi": "Inspecter ce qui entre dans le modèle et ce qui en sort : "
             "invites hostiles, données à caractère personnel, secrets, "
             "contenus interdits par la politique maison.",
     "ce_qu_il_ne_fait_pas": "Il ne comprend pas l'intention. Un filtrage "
                             "rattrape des formes connues ; il ne décide pas "
                             "qu'une demande légitime en apparence sert un "
                             "détournement.",
     "delai_jours": 60,
     "suppose": "Qu'une politique de contenu existe DÉJÀ et qu'elle soit "
                "écrite. Sans elle, le filtrage se règle au jugé et produit "
                "des faux positifs que les métiers font retirer.",
     "maillons": ("perception", "effet"),
     "prerequis": ()},
    {"cle": "iam_agents", "equipe": "devsecops", "nom": "IAM — identité et habilitations des agents",
     "famille": "protection",
     "quoi": "Donner à chaque agent une identité distincte de celle de son "
             "utilisateur, des habilitations propres, une durée de vie, et "
             "une trace de ce qu'il a fait en son nom.",
     "ce_qu_il_ne_fait_pas": "Il n'empêche pas l'agent d'employer correctement "
                             "un droit qu'on lui a donné à tort. Le mauvais "
                             "périmètre d'habilitation reste le premier "
                             "défaut, et aucun IAM ne le corrige.",
     "delai_jours": 120,
     "suppose": "Que l'annuaire accepte des identités non humaines. Dans "
                "beaucoup de grands comptes, c'est le chantier lui-même — "
                "pas une configuration.",
     "maillons": ("decision", "action"),
     "prerequis": ()},
    {"cle": "mlops", "equipe": "devsecops", "nom": "MLOps / LLMOps — chaîne de mise en service",
     "famille": "industrialisation",
     "quoi": "Versionner modèles, invites et jeux d'évaluation ; savoir quelle "
             "version sert quel cas d'usage ; pouvoir revenir en arrière.",
     "ce_qu_il_ne_fait_pas": "Il ne dit pas si le modèle est bon. Il dit "
                             "lequel tourne, depuis quand, et ce qu'on peut "
                             "restaurer.",
     "delai_jours": 90,
     "suppose": "Que les invites soient tenues comme du code. Tant qu'elles "
                "vivent dans des documents partagés, il n'y a rien à "
                "versionner.",
     "maillons": ("raisonnement",),
     "prerequis": ()},
    {"cle": "validation_modeles", "equipe": "data_office", "nom": "Validation de modèles",
     "famille": "assurance",
     "quoi": "Éprouver un modèle avant mise en service et à intervalles "
             "réguliers : jeux d'évaluation, essais d'adversité, dérive.",
     "ce_qu_il_ne_fait_pas": "Elle ne vaut que pour la version éprouvée. Un "
                             "modèle mis à jour par son fournisseur est un "
                             "modèle non validé, et la mise à jour ne "
                             "s'annonce pas toujours.",
     "delai_jours": 150,
     "suppose": "Qu'une fonction indépendante de celle qui construit puisse "
                "refuser. En banque, c'est la validation indépendante des "
                "modèles — elle existe déjà pour le risque de crédit, et "
                "elle n'a presque jamais été étendue aux modèles de langage.",
     "maillons": ("raisonnement", "decision"),
     "prerequis": ("mlops",)},
    {"cle": "mcp", "equipe": "design_authority", "nom": "MCP — maîtrise des serveurs d'outils",
     "famille": "protection",
     "quoi": "Inventorier les serveurs d'outils auxquels un agent est "
             "raccordé, qui les tient, ce que chaque outil peut faire, et "
             "avec quelles habilitations il s'exécute.",
     "ce_qu_il_ne_fait_pas": "Il ne protège pas d'un outil légitime employé à "
                             "contretemps. Et la DESCRIPTION d'un outil entre "
                             "dans l'invite du modèle : un serveur d'outils "
                             "est une surface d'injection, pas seulement une "
                             "surface d'exécution.",
     "delai_jours": 45,
     "suppose": "Qu'on sache déjà énumérer les serveurs raccordés. C'est le "
                "point où la plupart des inventaires s'arrêtent, parce qu'un "
                "raccordement se fait en une ligne de configuration.",
     "maillons": ("action",),
     "prerequis": ("iam_agents",)},
    {"cle": "api", "equipe": "devsecops", "nom": "Sécurité des API exposées et consommées",
     "famille": "protection",
     "quoi": "Authentification, quotas, journalisation et cloisonnement des "
             "interfaces par lesquelles l'usine appelle et se fait appeler.",
     "ce_qu_il_ne_fait_pas": "Elle ne distingue pas un appel légitime d'un "
                             "appel légitime de trop. Les quotas protègent le "
                             "service, pas la donnée.",
     "delai_jours": 60,
     "suppose": "Une passerelle déjà en place. Si l'usine expose en direct, "
                "le délai est celui d'une passerelle, pas d'une "
                "configuration.",
     "maillons": ("action", "effet"),
     "prerequis": ()},
    {"cle": "revue_code_ia", "equipe": "devsecops", "nom": "Revue du code produit par l'IA",
     "famille": "assurance",
     "quoi": "Une relecture humaine nommée, une vérification des dépendances "
             "proposées, et l'interdiction de fusionner sans les deux.",
     "ce_qu_il_ne_fait_pas": "Elle ne remplace pas les essais. Un code relu "
                             "et non éprouvé reste un code non éprouvé.",
     "delai_jours": 30,
     "suppose": "Que la chaîne de construction refuse la fusion. Une consigne "
                "sans blocage technique tient trois semaines.",
     "maillons": ("action",),
     "prerequis": ()},
    {"cle": "journal_agents", "equipe": "cyberdefense", "nom": "Journalisation des actions d'agents",
     "famille": "detection",
     "quoi": "Conserver ce que l'agent a reçu, décidé et appelé, avec de quoi "
             "reconstituer un enchaînement après coup.",
     "ce_qu_il_ne_fait_pas": "Elle n'empêche rien. Elle rend l'incident "
                             "explicable — et sans elle, l'incident reste une "
                             "hypothèse.",
     "delai_jours": 75,
     "suppose": "Un puits de journaux capable d'absorber le volume d'invites "
                "et de réponses, et une durée de conservation tranchée avec "
                "le délégué à la protection des données.",
     "maillons": ("perception", "raisonnement", "decision", "action", "effet"),
     "prerequis": ()},
    {"cle": "inventaire", "equipe": "data_office", "nom": "Inventaire des cas d'usage en service",
     "famille": "gouvernance",
     "quoi": "Savoir ce qui tourne, pour qui, sur quelles données, avec quel "
             "modèle, et qui en répond.",
     "ce_qu_il_ne_fait_pas": "Il ne dit pas si c'est sûr. Il dit ce qu'il y a "
                             "à regarder — et c'est le seul contrôle dont "
                             "l'absence rend tous les autres incalculables.",
     "delai_jours": 30,
     "suppose": "Rien. C'est pour cela qu'il n'a aucune excuse d'être absent, "
                "et qu'il est le prérequis de la dette elle-même.",
     "maillons": (),
     "prerequis": ()},
    {"cle": "jalons_projet", "equipe": "integration_projets",
     "nom": "Jalons de sécurité IA dans le cycle projet",
     "famille": "assurance",
     "quoi": "Des critères d'entrée et de sortie propres à l'IA aux jalons "
             "du cycle projet : quel modèle, sur quelles données, avec "
             "quels outils raccordés, qui répond de la sortie, et ce qui "
             "est refusé tant qu'un de ces points reste vide.",
     "ce_qu_il_ne_fait_pas": "Il ne regarde le cas d'usage qu'aux moments "
                             "où il est convoqué. Entre deux jalons, un "
                             "modèle change de version, un outil se "
                             "raccorde en une ligne de configuration, un "
                             "périmètre de données s'élargit — et rien de "
                             "tout cela ne repasse par un jalon. Un projet "
                             "clos ne repasse plus par aucun.",
     "delai_jours": 75,
     "suppose": "Que la filière projet sache dire quels projets sont des "
                "projets d'IA. Sans l'inventaire, le jalon ne se déclenche "
                "que pour ceux qui se sont déclarés — c'est-à-dire pour "
                "ceux qui posaient déjà le moins de difficulté.",
     "maillons": ("raisonnement", "decision"),
     "prerequis": ("inventaire",)},
    # ── LA GOUVERNANCE DE L'USAGE ────────────────────────────────────────
    {"cle": "politique_usage", "equipe": "data_office",
     "nom": "Politique d'usage des outils d'IA générative",
     "famille": "gouvernance",
     "quoi": "Écrire ce qui est permis, avec quels outils, sur quelles "
             "données, et ce qui ne l'est pas — en nommant les outils "
             "autorisés plutôt qu'en énumérant les interdits.",
     "ce_qu_il_ne_fait_pas": "Elle n'empêche personne. Une politique sans "
                             "outil autorisé qui fasse le travail produit du "
                             "Shadow AI — elle le CRÉE, même.",
     "delai_jours": 45,
     "suppose": "Qu'un outil conforme soit disponible AVANT la publication "
                "de la politique. Publier l'interdit sans l'alternative est "
                "la façon la plus sûre de perdre la visibilité.",
     "maillons": (),
     "prerequis": ()},
    {"cle": "shadow_ai", "equipe": "cyberdefense",
     "nom": "Détection et encadrement du Shadow AI",
     "famille": "detection",
     "quoi": "Voir les usages d'IA qui n'ont demandé la permission à "
             "personne : services en ligne appelés depuis le poste de "
             "travail, extensions de navigateur, clés d'API personnelles.",
     "ce_qu_il_ne_fait_pas": "Il ne dit pas pourquoi l'usage existe. Et "
                             "c'est la seule chose qui permette de le "
                             "traiter : un Shadow AI est presque toujours un "
                             "besoin réel mal servi par l'outillage officiel.",
     "delai_jours": 60,
     "suppose": "Un filtrage de flux sortant déjà en place et une liste "
                "tenue des services d'IA connus — laquelle vieillit en "
                "semaines.",
     "maillons": (),
     "prerequis": ("politique_usage",)},
    # ── LA CHAÎNE DE PRODUCTION ──────────────────────────────────────────
    {"cle": "securite_datasets", "equipe": "devsecops",
     "nom": "Sécurité des jeux de données",
     "famille": "industrialisation",
     "quoi": "Savoir d'où vient chaque jeu, qui y a accès, ce qu'il "
             "contient de sensible, et ce qui a été fait pour le préparer.",
     "ce_qu_il_ne_fait_pas": "Elle ne détecte pas l'empoisonnement. Elle "
                             "rend la provenance traçable, ce qui permet de "
                             "savoir QUOI reprendre le jour où on l'apprend.",
     "delai_jours": 90,
     "suppose": "Que les jeux vivent dans un magasin et non dans des "
                "partages de fichiers. Sinon le chantier est celui du "
                "magasin.",
     "maillons": ("raisonnement",),
     "prerequis": ()},
    {"cle": "provenance_modeles", "equipe": "devsecops",
     "nom": "Signature et provenance des modèles",
     "famille": "industrialisation",
     "quoi": "Signer ce qui entre en production, vérifier la signature au "
             "déploiement, et conserver de quoi dire d'où vient un poids.",
     "ce_qu_il_ne_fait_pas": "Elle ne dit rien de ce que le modèle a appris. "
                             "Un modèle authentiquement signé par un tiers "
                             "reste un modèle qu'on n'a pas éprouvé.",
     "delai_jours": 75,
     "suppose": "Une autorité de signature déjà en service pour les "
                "artefacts logiciels. L'étendre aux poids coûte peu ; la "
                "créer coûte un projet.",
     "maillons": ("raisonnement",),
     "prerequis": ("mlops",)},
    {"cle": "deps_ml", "equipe": "devsecops",
     "nom": "Scan des dépendances ML",
     "famille": "industrialisation",
     "quoi": "Passer les bibliothèques, les formats de poids et les "
             "conteneurs d'entraînement au même crible que le reste du code.",
     "ce_qu_il_ne_fait_pas": "Il ne couvre pas les formats de "
                             "sérialisation qui exécutent du code au "
                             "chargement — ceux-là se traitent en les "
                             "interdisant, pas en les scannant.",
     "delai_jours": 45,
     "suppose": "Une chaîne de scan de dépendances déjà branchée. Les "
                "formats ML s'y ajoutent ; sans elle, c'est un projet.",
     "maillons": ("action",),
     "prerequis": ()},
    {"cle": "secrets", "equipe": "devsecops",
     "nom": "Gestion des secrets de la chaîne IA",
     "famille": "protection",
     "quoi": "Sortir les clés d'API de modèles des dépôts, des cahiers de "
             "notes et des variables d'environnement partagées, et les faire "
             "tourner.",
     "ce_qu_il_ne_fait_pas": "Elle ne rattrape pas une clé déjà partie dans "
                             "une invite. Une clé collée dans un message à "
                             "un modèle externe est une clé compromise.",
     "delai_jours": 60,
     "suppose": "Un coffre déjà en service. C'est presque toujours le cas en "
                "banque — et presque jamais branché sur les cahiers de "
                "notes des équipes de science des données.",
     "maillons": ("perception",),
     "prerequis": ()},
    {"cle": "durcissement", "equipe": "devsecops",
     "nom": "Durcissement des environnements d'entraînement et d'inférence",
     "famille": "protection",
     "quoi": "Cloisonner, réduire les droits, fermer les sorties réseau, et "
             "séparer ce qui entraîne de ce qui sert.",
     "ce_qu_il_ne_fait_pas": "Il n'empêche pas l'exfiltration par la réponse "
                             "du modèle. Le durcissement ferme les portes "
                             "techniques, pas le canal prévu pour parler.",
     "delai_jours": 105,
     "suppose": "Que l'entraînement et l'inférence soient déjà séparés. S'ils "
                "partagent l'environnement, le durcissement commence par une "
                "séparation, et le délai double.",
     "maillons": ("action", "effet"),
     "prerequis": ()},
    # ── L'ÉPREUVE, ET LES GENS ───────────────────────────────────────────
    {"cle": "red_team_ia", "equipe": "cyberdefense",
     "nom": "Exercices d'attaque spécifiques à l'IA",
     "famille": "assurance",
     "quoi": "Éprouver pour de bon : injection indirecte par un document "
             "déposé, détournement d'un outil raccordé, extraction de "
             "l'invite système, enchaînement d'agents.",
     "ce_qu_il_ne_fait_pas": "Il ne remplace pas les contrôles. Un exercice "
                             "sur une usine sans filtrage ni journal produit "
                             "un rapport prévisible et n'apprend rien.",
     "delai_jours": 90,
     "suppose": "Que les journaux existent. Sans eux, l'exercice ne se "
                "rejoue pas et ses constats ne se vérifient pas.",
     "maillons": ("perception", "raisonnement", "decision", "action", "effet"),
     "prerequis": ("journal_agents",)},
    {"cle": "sensibilisation", "equipe": "securite_ia",
     "nom": "Ateliers métiers et formation des équipes cyber",
     "famille": "gouvernance",
     "quoi": "Deux publics et deux contenus : aux métiers, ce que l'outil "
             "fait de leurs données et ce qu'il invente ; aux équipes cyber, "
             "ce qu'un incident IA a de différent d'un incident applicatif.",
     "ce_qu_il_ne_fait_pas": "Elle ne tient pas lieu de contrôle. Une "
                             "sensibilisation employée à la place d'un "
                             "garde-fou transfère la charge sur "
                             "l'utilisateur, et c'est lui qui portera la "
                             "faute.",
     "delai_jours": 30,
     "suppose": "Que la politique d'usage existe — sinon l'atelier enseigne "
                "des règles qui ne sont écrites nulle part.",
     "maillons": (),
     "prerequis": ("politique_usage",)},
)

CONTROLES_PAR_CLE = {c["cle"]: c for c in CONTROLES}


# ═══════════════════════════════════════════════════════════════════════════
#  LES RISQUES — TROIS FAMILLES, ET CHACUNE ATTAQUE UN MAILLON
# ═══════════════════════════════════════════════════════════════════════════
#
# CHAQUE RISQUE EST ATTACHÉ À UN MAILLON DE LA CHAÎNE D'AUTONOMIE ET, QUAND
# ELLE EXISTE, À UNE MENACE DU CATALOGUE. Ce n'est pas de l'ornement : sans ce
# rattachement, on obtient deux listes qui parlent du même sujet et qui
# divergent — un risque « injection de prompt » d'un côté, un maillon
# « perception » mal coté de l'autre, et personne ne fait le lien.
#
# LA RÈGLE DE GARDE EN BAS DE FICHIER VÉRIFIE QUE CHAQUE MAILLON ET CHAQUE
# MENACE CITÉS EXISTENT VRAIMENT chez `chaine_autonomie`. Un rattachement
# vers une clé inventée se lirait comme un lien et ne mènerait nulle part.

RISQUES = (
    # ── LLM ───────────────────────────────────────────────────────────────
    {"cle": "injection_indirecte", "famille": "llm",
     "nom": "Injection indirecte par le contenu",
     "quoi": "Le contenu que le modèle lit — un document, une page, un "
             "ticket, la description d'un outil — porte des instructions "
             "qu'il exécute comme si elles venaient de l'utilisateur.",
     "pourquoi_ca_passe": "Rien ne distingue, dans une invite, ce qui est "
                          "consigne de ce qui est donnée. C'est une propriété "
                          "du procédé, pas un défaut d'implémentation : aucun "
                          "correctif ne la fera disparaître.",
     "maillon": "perception", "menace": "ASI02",
     "controles": ("filtrage_ia", "journal_agents")},
    {"cle": "fuite_par_invite", "famille": "llm",
     "nom": "Fuite de données par l'invite",
     "quoi": "Des données confidentielles entrent dans l'invite — coller un "
             "extrait, joindre un document, raccorder une base — et sortent "
             "du périmètre où elles étaient protégées.",
     "pourquoi_ca_passe": "L'invite est vécue comme une conversation, pas "
                          "comme un transfert de données. Personne ne remplit "
                          "d'analyse d'impact pour coller un paragraphe.",
     "maillon": "perception", "menace": "ANSSI-EXF",
     "controles": ("filtrage_ia", "journal_agents", "inventaire")},
    {"cle": "derive_modele", "famille": "llm",
     "nom": "Dérive et mise à jour silencieuse du modèle",
     "quoi": "Le fournisseur change le modèle derrière la même adresse. Les "
             "réponses changent, les évaluations d'hier ne valent plus, et "
             "rien ne l'a annoncé.",
     "pourquoi_ca_passe": "Le contrat porte sur un service, pas sur une "
                          "version. C'est le seul risque de cette liste qui "
                          "se traite d'abord par une clause, pas par un "
                          "outil.",
     "maillon": "raisonnement", "menace": None,
     "controles": ("validation_modeles", "mlops")},
    # ── IA GÉNÉRATIVE ─────────────────────────────────────────────────────
    {"cle": "dependance_hallucinee", "famille": "generative",
     "nom": "Dépendance hallucinée",
     "quoi": "Le modèle propose un paquet qui n'existe pas. Quelqu'un publie "
             "ce nom, et l'installation suivante le télécharge.",
     "pourquoi_ca_passe": "Le nom proposé est plausible, et la chaîne de "
                          "construction ne distingue pas un paquet neuf d'un "
                          "paquet établi. L'attaquant n'a rien à casser : il "
                          "attend.",
     "maillon": "action", "menace": "ASI04",
     "controles": ("revue_code_ia", "mlops")},
    {"cle": "contenu_produit", "famille": "generative",
     "nom": "Contenu produit engageant la maison",
     "quoi": "Une réponse rendue à un client, un courrier, une position "
             "réglementaire : le modèle produit du texte qui engage, et "
             "personne n'a relu.",
     "pourquoi_ca_passe": "La qualité rédactionnelle fait présumer la justesse. "
                          "Plus le texte est bien écrit, moins on le relit.",
     "maillon": "effet", "menace": "ASI09",
     "controles": ("filtrage_ia", "inventaire")},
    {"cle": "donnees_entrainement", "famille": "generative",
     "nom": "Empoisonnement des données d'ajustement",
     "quoi": "Les données employées pour spécialiser un modèle portent ce "
             "qu'un tiers y a mis — contenus publics, contributions "
             "internes, tickets.",
     "pourquoi_ca_passe": "La collecte est massive et la relecture ne l'est "
                          "pas. L'effet n'apparaît qu'à l'usage, longtemps "
                          "après l'ajustement.",
     "maillon": "raisonnement", "menace": "ANSSI-INF",
     "controles": ("validation_modeles", "mlops")},
    # ── AGENTIQUE ─────────────────────────────────────────────────────────
    {"cle": "outil_a_contretemps", "famille": "agentique",
     "nom": "Outil légitime appelé à contretemps",
     "quoi": "L'agent appelle un outil qu'il a le droit d'appeler, avec des "
             "paramètres qu'il a le droit d'employer, au mauvais moment ou "
             "sur le mauvais objet.",
     "pourquoi_ca_passe": "Chaque appel est conforme. C'est l'ENCHAÎNEMENT "
                          "qui ne l'est pas, et aucun contrôle unitaire ne "
                          "regarde l'enchaînement.",
     "maillon": "action", "menace": "ASI02",
     "controles": ("mcp", "journal_agents", "iam_agents")},
    {"cle": "identite_empruntee", "famille": "agentique",
     "nom": "Agent agissant sous l'identité de l'utilisateur",
     "quoi": "L'agent hérite des droits de la personne qui l'a lancé, y "
             "compris ceux dont son cas d'usage n'a aucun besoin.",
     "pourquoi_ca_passe": "C'est le chemin le plus court pour livrer. "
                          "Distinguer l'identité de l'agent suppose un "
                          "annuaire qui l'accepte, et c'est un chantier.",
     "maillon": "decision", "menace": "ASI03",
     "controles": ("iam_agents", "journal_agents")},
    {"cle": "chaine_agents", "nom": "Enchaînement d'agents sans frontière",
     "famille": "agentique",
     "quoi": "Un agent en appelle un autre, qui en appelle un troisième. "
             "Chaque appel passe un contexte que personne ne contrôle plus.",
     "pourquoi_ca_passe": "Le cloisonnement est pensé au niveau du système, "
                          "pas de la conversation. Les frontières de sécurité "
                          "n'ont pas été dessinées là où le flux passe.",
     "maillon": "action", "menace": "ASI07",
     "controles": ("mcp", "api", "journal_agents")},
    {"cle": "effet_irreversible", "famille": "agentique",
     "nom": "Effet irréversible sans point d'arrêt",
     "quoi": "Virement, suppression, envoi, publication : l'agent produit un "
             "effet que rien ne rattrape, et aucun humain n'a tranché.",
     "pourquoi_ca_passe": "La validation humaine a été retirée parce qu'elle "
                          "ralentissait la démonstration, et personne ne l'a "
                          "remise pour la mise en service.",
     "maillon": "effet", "menace": "ASI01",
     "controles": ("iam_agents", "journal_agents", "api")},
)

RISQUES_PAR_CLE = {r["cle"]: r for r in RISQUES}
FAMILLES_RISQUE = {
    "llm": "Modèles de langage",
    "generative": "IA générative",
    "agentique": "Systèmes agentiques",
}


# ═══════════════════════════════════════════════════════════════════════════
#  LES CAS D'USAGE — DONT LES DEUX QUE LA DEMANDE NOMME
# ═══════════════════════════════════════════════════════════════════════════
#
# CE QUE LE DÉPÔT IGNORAIT, ET ÇA A ÉTÉ MESURÉ AVANT D'ÊTRE ÉCRIT : « vibe
# coding » ne figurait dans aucun fichier des deux plateformes, et MCP n'y
# existait que comme CLIENT du cabinet vers un serveur externe — jamais comme
# surface à sécuriser chez un client.

CAS_USAGE = (
    {"cle": "vibe_coding", "nom": "Vibe coding",
     "quoi_vraiment": "Ce n'est pas « du code produit par une IA ». C'est du "
                      "code ACCEPTÉ SANS RELECTURE parce qu'il compile et "
                      "qu'il fait ce qu'on voulait. La production d'un code "
                      "par un modèle n'a rien de problématique ; son "
                      "acceptation sans lecture est le cas d'usage réel, et "
                      "c'est lui qu'il faut nommer pour pouvoir l'encadrer.",
     "ce_qui_se_voit_pas": "La propriété du code. Six mois plus tard, "
                           "personne dans l'équipe ne sait dire pourquoi une "
                           "fonction est écrite ainsi — et la corriger "
                           "devient une réécriture.",
     "risques": ("dependance_hallucinee", "fuite_par_invite"),
     "controles_requis": ("revue_code_ia", "inventaire"),
     "le_bon_encadrement": "Interdire la fusion sans relecture nommée et sans "
                           "vérification des dépendances proposées. Pas "
                           "interdire l'outil : l'interdiction déplace "
                           "l'usage hors de vue, et on perd à la fois le "
                           "gain et le contrôle.",
     "signal_d_alerte": "Le volume de code fusionné augmente pendant que le "
                        "nombre de relectures reste constant."},
    {"cle": "agents_autonomes", "nom": "Agents autonomes",
     "quoi_vraiment": "Un système qui décide de la suite de ses propres "
                      "actions. La question n'est pas « est-il autonome » "
                      "mais « à quel maillon », et la chaîne d'autonomie "
                      "répond à celle-là système par système.",
     "ce_qui_se_voit_pas": "Le moment où le pilote devient un service. "
                           "Personne ne prononce la bascule : le nombre "
                           "d'utilisateurs monte, et l'encadrement de "
                           "démonstration reste en place.",
     "risques": ("outil_a_contretemps", "identite_empruntee", "chaine_agents",
                 "effet_irreversible"),
     "controles_requis": ("iam_agents", "mcp", "journal_agents"),
     "le_bon_encadrement": "Une identité propre, des outils énumérés, un "
                           "point d'arrêt humain sur tout effet "
                           "irréversible, et de quoi reconstituer un "
                           "enchaînement après coup.",
     "signal_d_alerte": "On ne sait plus énumérer les outils auxquels un "
                        "agent est raccordé."},
    {"cle": "assistant_interne", "nom": "Assistant interne sur documents",
     "quoi_vraiment": "Le cas d'usage le plus répandu et le plus sous-estimé : "
                      "un modèle branché sur la documentation maison.",
     "ce_qui_se_voit_pas": "Le périmètre réel des documents indexés. Il suit "
                           "les droits du compte qui a fait l'indexation, "
                           "pas ceux de la personne qui pose la question.",
     "risques": ("injection_indirecte", "fuite_par_invite"),
     "controles_requis": ("filtrage_ia", "inventaire"),
     "le_bon_encadrement": "Le contrôle d'accès s'applique à la RECHERCHE, "
                           "pas seulement à la réponse. Filtrer la réponse "
                           "après coup laisse le modèle raisonner sur ce "
                           "qu'il n'aurait pas dû lire.",
     "signal_d_alerte": "Deux personnes aux droits différents obtiennent la "
                        "même réponse."},
    {"cle": "decision_client", "nom": "Aide à la décision sur un client",
     "quoi_vraiment": "Scoring, pré-instruction, détection : le modèle "
                      "contribue à une décision qui affecte une personne.",
     "ce_qui_se_voit_pas": "Que le cas relève du règlement sur l'IA au titre "
                           "de l'annexe III quand il porte sur la solvabilité "
                           "de personnes physiques — et que l'équipe qui le "
                           "construit l'ignore souvent.",
     "risques": ("derive_modele", "contenu_produit", "donnees_entrainement"),
     "controles_requis": ("validation_modeles", "mlops", "journal_agents"),
     "le_bon_encadrement": "La validation indépendante des modèles existe "
                           "déjà en banque pour le risque de crédit. "
                           "L'étendre coûte moins que de la créer, et "
                           "presque personne ne l'a fait.",
     "signal_d_alerte": "Le modèle est décrit comme « une aide » alors que le "
                        "taux de suivi de sa recommandation dépasse 90 %."},
    {"cle": "soc_augmente", "nom": "SOC augmenté par l'IA",
     "quoi_vraiment": "L'IA employée DANS la défense : tri d'alertes, "
                      "corrélation, rédaction de rapports d'incident.",
     "ce_qui_se_voit_pas": "Que ce système d'IA est un système d'IA. Il "
                           "appartient à l'équipe sécurité, il n'entre dans "
                           "aucun inventaire de cas d'usage, et il lit les "
                           "données les plus sensibles de la maison.",
     "risques": ("injection_indirecte", "fuite_par_invite", "derive_modele"),
     "controles_requis": ("inventaire", "journal_agents", "validation_modeles"),
     "le_bon_encadrement": "Le mettre à l'inventaire comme les autres. La "
                           "contre-expertise de l'arsenal défensif est la "
                           "même que celle du reste — et elle est presque "
                           "toujours sautée.",
     "signal_d_alerte": "L'inventaire des cas d'usage ne contient aucun cas "
                        "porté par l'équipe sécurité."},
)

CAS_PAR_CLE = {c["cle"]: c for c in CAS_USAGE}


# ═══════════════════════════════════════════════════════════════════════════
#  LES DATES — INJECTÉES, JAMAIS LUES À L'HORLOGE
# ═══════════════════════════════════════════════════════════════════════════
#
# UNE ÉCHÉANCE CALCULÉE SUR `date.today()` REND UNE RÈGLE QUI PASSE AUJOURD'HUI
# ET TOMBE DEMAIN. La discipline est celle des autres modules du cabinet : la
# date entre par la porte.

def _jour(valeur, defaut=None):
    if isinstance(valeur, datetime.date):
        return valeur
    t = str(valeur or "").strip()
    if not t:
        return defaut
    try:
        return datetime.date(*(int(x) for x in t.split("-")))
    except (TypeError, ValueError):
        return defaut


def _aujourdhui(valeur=None):
    return _jour(valeur) or datetime.date.today()


# ═══════════════════════════════════════════════════════════════════════════
#  LA DETTE D'ANTÉRIORITÉ — LE CŒUR DU MODULE
# ═══════════════════════════════════════════════════════════════════════════

def dette(cas_declares=None, controles_declares=None, aujourdhui=None):
    """Ce qui est en service sans le contrôle qui le couvre — et de combien.

    ═══ CE QUE CETTE FONCTION REFUSE DE FAIRE ═══════════════════════════
    Rendre un pourcentage de couverture. « 78 % des contrôles en place » est
    exactement le chiffre qui a laissé passer la dette : il monte pendant que
    des cas d'usage partent sans contrôle, parce qu'il compte les contrôles
    et non les cas découverts.

    ═══ CE QU'ELLE REND À LA PLACE ══════════════════════════════════════
    Le nombre de cas d'usage EN SERVICE dont un contrôle requis n'existe pas,
    et pour chacun depuis combien de jours. Un compte et des jours : les deux
    se discutent avec un directeur, un pourcentage non.

    ═══ ET L'INVENTAIRE EST À PART ══════════════════════════════════════
    Sans inventaire, la dette n'est pas « nulle » : elle est INCALCULABLE, et
    c'est pire. Un module qui rendrait zéro sur un périmètre inconnu ferait
    exactement ce qu'on lui demande de dénoncer.
    """
    jour = _aujourdhui(aujourdhui)
    cas = cas_declares or []
    if not isinstance(cas, list):
        return {"ok": False, "motif": "cas_illisibles"}
    dispo = controles_declares or {}
    if not isinstance(dispo, dict):
        return {"ok": False, "motif": "controles_illisibles"}

    # ── QUAND CHAQUE CONTRÔLE EXISTE-T-IL, S'IL EXISTE ? ─────────────────
    etat = {}
    for cle in CONTROLES_PAR_CLE:
        d = dispo.get(cle)
        if isinstance(d, str):
            d = {"depuis": d}
        d = d if isinstance(d, dict) else {}
        depuis = _jour(d.get("depuis"))
        en_place = bool(d.get("en_place")) or depuis is not None
        etat[cle] = {"cle": cle, "nom": CONTROLES_PAR_CLE[cle]["nom"],
                     "en_place": en_place and (depuis is None or depuis <= jour),
                     "depuis": depuis.isoformat() if depuis else None,
                     "prevu_le": (d.get("prevu_le") or None)}

    inventaire_tenu = etat["inventaire"]["en_place"]

    lignes, total_jours = [], 0
    for i, c in enumerate(cas):
        c = c if isinstance(c, dict) else {}
        nom = str(c.get("nom") or "").strip()
        type_cle = c.get("type") if c.get("type") in CAS_PAR_CLE else None
        en_service = bool(c.get("en_service"))
        depuis = _jour(c.get("depuis"))
        requis = list(c.get("controles_requis") or
                      (CAS_PAR_CLE[type_cle]["controles_requis"]
                       if type_cle else ()))
        requis = [r for r in requis if r in CONTROLES_PAR_CLE]

        manquants = [r for r in requis if not etat[r]["en_place"]]
        # ── L'ANCIENNETÉ, QUI EST LA MESURE ──────────────────────────────
        #
        # Un cas en service depuis six mois sans contrôle ne vaut pas un cas
        # parti la semaine dernière : le premier a produit des usages, des
        # habitudes et des données qu'il faudra reprendre.
        anciennete = ((jour - depuis).days
                      if (en_service and depuis and depuis <= jour) else None)
        if en_service and manquants and anciennete:
            total_jours += anciennete

        lignes.append({
            "rang": i, "nom": nom or "(sans nom)",
            "type": (dict(CAS_PAR_CLE[type_cle], cle=type_cle)
                     if type_cle else None),
            "en_service": en_service,
            "depuis": depuis.isoformat() if depuis else None,
            "anciennete_jours": anciennete,
            "controles_requis": requis,
            "manquants": [dict(CONTROLES_PAR_CLE[m], cle=m)
                          for m in manquants],
            "en_dette": bool(en_service and manquants),
            "sans_type": type_cle is None and not c.get("controles_requis"),
        })

    en_dette = [l for l in lignes if l["en_dette"]]
    en_service = [l for l in lignes if l["en_service"]]
    sans_date = [l for l in en_dette if l["anciennete_jours"] is None]
    sans_type = [l["nom"] for l in lignes if l["sans_type"]]

    return {
        "ok": True,
        "aujourdhui": jour.isoformat(),
        "lignes": lignes,
        "controles": [etat[c["cle"]] for c in CONTROLES],
        "cas_declares": len(lignes),
        "cas_en_service": len(en_service),
        "cas_en_dette": len(en_dette),
        "jours_cumules": total_jours,
        "sans_date": [l["nom"] for l in sans_date],
        "sans_controle_requis": sans_type,
        # ═══ LE POINT QUI DÉCIDE DE LA VALIDITÉ DE TOUT LE RESTE ═════════
        "inventaire_tenu": inventaire_tenu,
        "calculable": inventaire_tenu,
        "dit": _dit_dette(inventaire_tenu, len(en_dette), len(en_service),
                          total_jours, sans_type),
    }


def _dit_dette(inventaire, en_dette, en_service, jours, sans_type):
    if not inventaire:
        return ("L'inventaire des cas d'usage en service n'est pas tenu. La "
                "dette affichée ne porte que sur ce qui a été déclaré ici, "
                "et le périmètre réel est inconnu — ce n'est pas une dette "
                "nulle, c'est une dette INCALCULABLE, et c'est la situation "
                "la plus coûteuse des deux.")
    if not en_service:
        return ("Aucun cas d'usage déclaré en service : rien n'est encore "
                "parti sans contrôle. C'est le seul moment où poser un "
                "contrôle coûte une configuration plutôt qu'une reprise.")
    if not en_dette:
        return ("Aucun cas d'usage en service sans son contrôle. À tenir "
                "pendant la montée en charge : c'est l'écart entre le rythme "
                "des mises en service et celui des contrôles qui creuse la "
                "dette, pas une décision isolée.")
    base = ("%d cas d'usage sur %d en service tournent sans un contrôle "
            "requis, soit %d jours-cas cumulés d'antériorité. Ce chiffre ne "
            "baisse pas tout seul : chaque semaine l'augmente."
            % (en_dette, en_service, jours))
    if sans_type:
        base += (" Et %d cas ne déclarent aucun contrôle requis : ils ne "
                 "comptent pas dans la dette, ce qui la sous-estime."
                 % len(sans_type))
    return base


# ═══════════════════════════════════════════════════════════════════════════
#  LA FEUILLE DE ROUTE — DÉRIVÉE, JAMAIS ÉCRITE À LA MAIN
# ═══════════════════════════════════════════════════════════════════════════

def feuille_de_route(controles_declares=None, depart=None, jours_par_lot=None):
    """L'ordre des contrôles, imposé par leurs prérequis et leurs délais.

    ═══ POURQUOI ELLE EST DÉRIVÉE ══════════════════════════════════════
    Une feuille de route écrite à la main est une liste de vœux : on y met ce
    qu'on veut faire, dans l'ordre où on veut le présenter. Celle-ci se déduit
    du graphe des prérequis — la maîtrise des serveurs d'outils ne se pose pas
    avant l'identité des agents, la validation de modèles pas avant la chaîne
    de mise en service — et les dates viennent des délais.

    CE QUE ÇA CHANGE EN RÉUNION : on ne discute plus l'ordre, on discute les
    délais. Et un délai se discute avec celui qui le tient.

    ═══ CE QU'ELLE NE FAIT PAS ══════════════════════════════════════════
    Elle ne compresse rien. Deux contrôles sans lien de prérequis peuvent être
    menés de front ; le module les place dans le même LOT et ne prétend pas
    savoir combien d'équipes sont disponibles. Le lot dit « ceux-là peuvent
    commencer ensemble », pas « ceux-là seront faits ensemble ».
    """
    dispo = controles_declares or {}
    if not isinstance(dispo, dict):
        return {"ok": False, "motif": "controles_illisibles"}
    debut = _jour(depart) or datetime.date.today()

    faits = set()
    for cle in CONTROLES_PAR_CLE:
        d = dispo.get(cle)
        if isinstance(d, str):
            d = {"depuis": d}
        d = d if isinstance(d, dict) else {}
        if bool(d.get("en_place")) or _jour(d.get("depuis")):
            faits.add(cle)

    # ── L'ORDRE TOPOLOGIQUE, PAR LOTS ────────────────────────────────────
    restants = [c for c in CONTROLES if c["cle"] not in faits]
    lots, vus, curseur, garde = [], set(faits), debut, 0
    while restants and garde < len(CONTROLES) + 2:
        garde += 1
        pret = [c for c in restants
                if all(p in vus for p in c["prerequis"])]
        if not pret:
            # UN CYCLE DE PRÉREQUIS. On ne boucle pas : on le NOMME, parce
            # qu'une feuille de route qui s'arrête sans dire pourquoi se lit
            # comme un périmètre réduit.
            return {"ok": False, "motif": "prerequis_circulaires",
                    "bloques": sorted(c["cle"] for c in restants)}
        duree = max(c["delai_jours"] for c in pret)
        fin = curseur + datetime.timedelta(days=duree)
        # ── CHAQUE CONTRÔLE PORTE SA PROPRE DATE DE FIN ──────────────────
        #
        # CE QUE ÇA CORRIGE, ET C'ÉTAIT MESURABLE : sans cette ligne, un lot
        # rendait UNE date de fin — la plus lointaine — et l'inventaire, qui
        # tient en trente jours, paraissait en demander cent vingt. Le
        # lecteur en concluait que rien n'arrive avant quatre mois, alors que
        # le premier livrable tombe au premier.
        lots.append({
            "rang": len(lots),
            "debut": curseur.isoformat(), "fin": fin.isoformat(),
            "duree_jours": duree,
            "controles": [
                dict(c, cle=c["cle"],
                     fin=(curseur + datetime.timedelta(
                         days=c["delai_jours"])).isoformat(),
                     prerequis_nommes=[CONTROLES_PAR_CLE[p]["nom"]
                                       for p in c["prerequis"]])
                for c in sorted(pret, key=lambda x: x["delai_jours"])],
            "commande": max(pret, key=lambda x: x["delai_jours"])["nom"],
            "premier_livrable": min(pret, key=lambda x: x["delai_jours"])["nom"],
        })
        for c in pret:
            vus.add(c["cle"])
            restants.remove(c)
        curseur = fin

    return {
        "ok": True,
        "depart": debut.isoformat(),
        "deja_en_place": sorted(faits),
        "lots": lots,
        "fin": lots[-1]["fin"] if lots else debut.isoformat(),
        "duree_totale_jours": sum(l["duree_jours"] for l in lots),
        # LE CHEMIN CRITIQUE SE NOMME TOUT SEUL : c'est le contrôle qui
        # commande la durée de chaque lot.
        "chemin_critique": [l["commande"] for l in lots],
        "dit": ("Rien à faire : tous les contrôles sont déclarés en place."
                if not lots else
                "%d lot(s), %d jours au total si les lots s'enchaînent. "
                "L'ordre vient des prérequis, pas d'une préférence : ce qui "
                "se discute ici, ce sont les délais — et un délai se discute "
                "avec celui qui le tient."
                % (len(lots), sum(l["duree_jours"] for l in lots))),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  L'ALERTE AU MANAGEMENT — UNE SOUSTRACTION, PAS UN AVIS
# ═══════════════════════════════════════════════════════════════════════════

ISSUES = (
    {"cle": "reduire", "nom": "Réduire le périmètre",
     "quoi": "Tenir la date avec moins de cas d'usage, ou des cas d'usage "
             "dont les contrôles requis sont déjà en place.",
     "qui_tranche": "Le métier porteur de l'ambition.",
     "ce_que_ca_coute": "Une promesse faite en interne ou au marché, qu'il "
                        "faut reprendre."},
    {"cle": "decaler", "nom": "Décaler la date",
     "quoi": "Tenir le périmètre en donnant aux contrôles le temps qu'ils "
             "demandent.",
     "qui_tranche": "Le sponsor du programme.",
     "ce_que_ca_coute": "Le rang concurrentiel invoqué pour justifier la "
                        "date — argument souvent juste, et rarement chiffré."},
    {"cle": "accepter", "nom": "Accepter le risque, par écrit",
     "quoi": "Tenir la date ET le périmètre, en actant l'écart, avec un "
             "porteur nommé, une échéance de revue et le geste de repli si "
             "l'incident survient.",
     "qui_tranche": "Celui qui porte le risque, pas la sécurité.",
     "ce_que_ca_coute": "Rien tout de suite. C'est pour cela que c'est "
                        "l'issue choisie par défaut — et pour cela qu'elle "
                        "doit être ÉCRITE et NOMMÉE, sinon elle est prise "
                        "sans avoir été décidée."},
)


def alerte(ambition=None, controles_declares=None, aujourdhui=None):
    """L'ambition tient-elle dans le temps que les contrôles demandent ?

    ═══ POURQUOI CETTE FONCTION EXISTE ══════════════════════════════════
    « Alerter et challenger le management lorsque les ambitions business ne
    sont pas compatibles avec les exigences de sécurité » est la part du
    métier qui se transmet le plus mal : elle se joue en réunion, et elle
    ressemble à une opinion contre une autre. Elle cesse d'y ressembler dès
    qu'on pose les deux nombres.

    ═══ CE QU'ELLE REND, ET CE QU'ELLE NE REND PAS ══════════════════════
    Elle rend un ÉCART EN JOURS et les trois issues. Elle ne rend PAS de
    recommandation : choisir entre réduire, décaler et accepter n'appartient
    pas à la sécurité, et un module qui trancherait à la place du porteur
    produirait exactement le réflexe qu'on cherche à éviter — celui qui
    consiste à contourner la sécurité plutôt qu'à décider avec elle.
    """
    a = ambition or {}
    if not isinstance(a, dict):
        return {"ok": False, "motif": "ambition_illisible"}
    intitule = str(a.get("intitule") or "").strip()
    if not intitule:
        return {"ok": False, "motif": "intitule_manquant"}
    cible = _jour(a.get("date_cible"))
    if cible is None:
        return {"ok": False, "motif": "date_cible_manquante"}
    jour = _aujourdhui(aujourdhui)

    requis = [c for c in (a.get("controles_requis") or [])
              if c in CONTROLES_PAR_CLE]
    for cle in (a.get("cas_usage") or []):
        if cle in CAS_PAR_CLE:
            requis += [c for c in CAS_PAR_CLE[cle]["controles_requis"]]
    requis = sorted(set(requis))
    if not requis:
        return {"ok": False, "motif": "aucun_controle_requis"}

    route = feuille_de_route(controles_declares, depart=jour)
    if not route.get("ok"):
        return route
    # ── LA DATE À LAQUELLE CHAQUE CONTRÔLE REQUIS EST PRÊT ───────────────
    prets, deja = {}, set(route["deja_en_place"])
    for lot in route["lots"]:
        for c in lot["controles"]:
            prets[c["cle"]] = _jour(c["fin"])
    manquants = []
    for cle in requis:
        if cle in deja:
            continue
        fin = prets.get(cle)
        manquants.append({
            "cle": cle, "nom": CONTROLES_PAR_CLE[cle]["nom"],
            "pret_le": fin.isoformat() if fin else None,
            "delai_jours": CONTROLES_PAR_CLE[cle]["delai_jours"],
            "suppose": CONTROLES_PAR_CLE[cle]["suppose"],
            "retard_jours": ((fin - cible).days
                             if (fin and fin > cible) else 0),
        })
    en_retard = [m for m in manquants if m["retard_jours"] > 0]
    ecart = max([m["retard_jours"] for m in en_retard] or [0])
    commande = (max(en_retard, key=lambda m: m["retard_jours"])
                if en_retard else None)

    return {
        "ok": True,
        "intitule": intitule,
        "date_cible": cible.isoformat(),
        "aujourdhui": jour.isoformat(),
        "jours_disponibles": (cible - jour).days,
        "controles_requis": requis,
        "deja_en_place": [c for c in requis if c in deja],
        "manquants": manquants,
        "en_retard": en_retard,
        "ecart_jours": ecart,
        "commande": commande,
        "compatible": not en_retard,
        "issues": list(ISSUES) if en_retard else [],
        "dit": _dit_alerte(intitule, cible, ecart, commande, len(en_retard)),
        "reserve": "Les délais employés sont des ordres de grandeur de mise "
                   "en place, pas des engagements : chacun porte ce qu'il "
                   "suppose. Un délai contesté se rediscute avec l'équipe "
                   "qui le tient — c'est le bon endroit pour le contester, "
                   "et c'est le but de cette restitution.",
    }


def _dit_alerte(intitule, cible, ecart, commande, combien):
    if not ecart:
        return ("« %s » tient dans le temps disponible : tous les contrôles "
                "requis sont en place ou le seront avant le %s. Rien à "
                "arbitrer." % (intitule, cible.isoformat()))
    return ("« %s » vise le %s ; %d contrôle(s) requis ne seront pas prêts, "
            "et le plus tardif — %s — arrive %d jours après. Ce n'est pas un "
            "avis de sécurité : c'est un écart entre deux dates. Trois issues "
            "existent, et aucune n'appartient à la sécurité : réduire le "
            "périmètre, décaler la date, ou accepter l'écart par écrit avec "
            "un porteur nommé."
            % (intitule, cible.isoformat(), combien, commande["nom"], ecart))


# ═══════════════════════════════════════════════════════════════════════════
#  CHALLENGER L'ARCHITECTURE — CHAQUE QUESTION DIT À QUOI RESSEMBLE UNE
#  MAUVAISE RÉPONSE
# ═══════════════════════════════════════════════════════════════════════════
#
# UNE LISTE DE QUESTIONS SANS CRITÈRE DE RÉPONSE NE CHALLENGE RIEN : elle se
# remplit, elle est archivée, et elle rassure. Ce qui rend une revue
# d'architecture utile, c'est de savoir à l'avance ce qu'on entendra quand la
# réponse est mauvaise — et ces réponses-là sont peu nombreuses et très
# reconnaissables.

ARCHITECTURE = (
    {"cle": "frontiere", "nom": "Où est la frontière de confiance ?",
     "question": "Entre le modèle, les outils, les données et l'utilisateur, "
                 "où passe la limite que rien ne franchit sans contrôle ?",
     "mauvaise_reponse": "« Tout est dans notre VPC. » Le cloisonnement "
                         "réseau ne dit rien du flux d'instructions : une "
                         "injection voyage dans une donnée parfaitement "
                         "bien cloisonnée.",
     "ce_qui_le_prouve": "Un schéma où la frontière est tracée, et un exemple "
                         "d'instruction hostile suivie de bout en bout.",
     "risques": ("injection_indirecte", "chaine_agents")},
    {"cle": "identite", "nom": "Sous quelle identité l'agent agit-il ?",
     "question": "Quand l'agent appelle un système tiers, qui ce système "
                 "voit-il — l'agent, ou la personne qui l'a lancé ?",
     "mauvaise_reponse": "« Il agit au nom de l'utilisateur. » C'est le "
                         "chemin le plus court, et il donne à l'agent tous "
                         "les droits de la personne, y compris ceux dont son "
                         "cas d'usage n'a aucun besoin.",
     "ce_qui_le_prouve": "Une entrée d'annuaire au nom de l'agent, et un "
                         "journal où l'on distingue ses appels de ceux de "
                         "l'utilisateur.",
     "risques": ("identite_empruntee",)},
    {"cle": "reversibilite", "nom": "Qu'est-ce qui n'est pas rattrapable ?",
     "question": "Parmi les actions que l'agent peut déclencher, lesquelles "
                 "ne se défont pas — et laquelle de ces actions un humain "
                 "valide-t-il ?",
     "mauvaise_reponse": "« Il ne fait que des lectures. » Presque toujours "
                         "faux dès la deuxième version : l'écriture arrive "
                         "avec le premier retour utilisateur, et la "
                         "validation humaine a été retirée pour la "
                         "démonstration.",
     "ce_qui_le_prouve": "La liste des outils en écriture, et le point "
                         "d'arrêt qui les précède.",
     "risques": ("effet_irreversible",)},
    {"cle": "outils", "nom": "Qui décide des outils raccordés ?",
     "question": "Comment un serveur d'outils est-il raccordé, par qui, et "
                 "que faut-il pour en ajouter un ?",
     "mauvaise_reponse": "« C'est une ligne de configuration. » C'est "
                         "exactement le problème : la surface d'attaque "
                         "s'étend sans passer par personne, et la DESCRIPTION "
                         "de l'outil entre dans l'invite du modèle.",
     "ce_qui_le_prouve": "Un inventaire des serveurs raccordés, avec leur "
                         "propriétaire et la revue qui a précédé chaque "
                         "raccordement.",
     "risques": ("outil_a_contretemps", "chaine_agents")},
    {"cle": "version", "nom": "Quelle version du modèle sert en production ?",
     "question": "Si le fournisseur change le modèle demain derrière la même "
                 "adresse, qu'est-ce qui le détecte ?",
     "mauvaise_reponse": "« On est sur la dernière version. » Autrement dit : "
                         "sur une version qui change sans prévenir, et les "
                         "évaluations d'hier ne valent plus.",
     "ce_qui_le_prouve": "Une version épinglée, ou à défaut une évaluation "
                         "périodique qui compare et alerte.",
     "risques": ("derive_modele",)},
    {"cle": "donnees", "nom": "Le contrôle d'accès s'applique-t-il à la "
                              "RECHERCHE ou à la réponse ?",
     "question": "Quand le modèle va chercher un document, emploie-t-il les "
                 "droits de celui qui pose la question ou ceux du compte qui "
                 "a indexé ?",
     "mauvaise_reponse": "« On filtre la réponse. » Le modèle a donc lu ce "
                         "qu'il n'aurait pas dû, et raisonné dessus — le "
                         "filtrage de sortie rattrape la citation, pas "
                         "l'inférence.",
     "ce_qui_le_prouve": "Deux comptes aux droits différents qui posent la "
                         "même question et obtiennent des réponses "
                         "différentes.",
     "risques": ("fuite_par_invite",)},
    {"cle": "arret", "nom": "Comment arrête-t-on tout ?",
     "question": "Si un comportement anormal est constaté un vendredi soir, "
                 "quel geste coupe le service, et qui peut le faire ?",
     "mauvaise_reponse": "« On retire l'accès. » À qui ? L'agent a une "
                         "identité technique, souvent partagée, et la couper "
                         "arrête aussi ce qui fonctionne.",
     "ce_qui_le_prouve": "Un interrupteur nommé, une astreinte qui le "
                         "connaît, et un essai fait au moins une fois.",
     "risques": ("effet_irreversible", "outil_a_contretemps")},
)


# ═══════════════════════════════════════════════════════════════════════════
#  L'ARSENAL — L'IA DANS LA DÉFENSE, ET LE PIÈGE QU'ELLE CRÉE
# ═══════════════════════════════════════════════════════════════════════════
#
# DEUX DIRECTIONS QU'ON CONFOND, ET LA SECONDE CRÉE LA PREMIÈRE :
#
#     · la SÉCURITÉ DE L'IA — protéger les systèmes d'IA de la maison ;
#     · l'IA POUR LA SÉCURITÉ — s'en servir dans l'arsenal défensif.
#
# LE DÉFAUT QUI N'EST INVISIBLE QU'À CAUSE DE SON PROPRIÉTAIRE : un modèle
# déployé dans le centre opérationnel de sécurité EST un système d'IA. Il lit
# les données les plus sensibles de la maison — journaux, alertes, éléments
# d'enquête — et il n'entre dans aucun inventaire de cas d'usage, parce que
# l'inventaire est tenu par la sécurité et que la sécurité ne s'inventorie
# pas elle-même.

ARSENAL = (
    {"cle": "tri_alertes", "nom": "Tri et qualification des alertes",
     "apport": "Absorber un volume que l'équipe ne lit plus, et rendre du "
               "temps d'analyste sur ce qui mérite une enquête.",
     "ce_qu_on_croit_gagner": "La détection. Ce n'est pas ça : la détection "
                              "reste celle des règles et des capteurs. Ce "
                              "qu'on gagne, c'est le TRI.",
     "ce_que_ca_expose": "Le modèle lit les alertes, donc les noms de "
                         "machines, de comptes et de fichiers. Une injection "
                         "placée dans un champ d'alerte — un nom de fichier, "
                         "un en-tête — parle directement au modèle.",
     "condition": "Ne jamais laisser le tri CLORE une alerte sans trace. Un "
                  "faux négatif silencieux est pire que l'absence d'outil.",
     "risques": ("injection_indirecte",)},
    {"cle": "enquete", "nom": "Assistance à l'enquête",
     "apport": "Reconstituer un enchaînement, résumer des journaux, proposer "
               "des pistes.",
     "ce_qu_on_croit_gagner": "Une conclusion. On gagne une HYPOTHÈSE, et "
                              "une hypothèse bien écrite se confond avec une "
                              "conclusion.",
     "ce_que_ca_expose": "Les éléments d'enquête sortent du périmètre de "
                         "l'enquête s'ils transitent par un service externe. "
                         "En banque, c'est le point qui fait échouer la "
                         "revue juridique.",
     "condition": "L'hébergement de ce cas d'usage se tranche AVANT le choix "
                  "de l'outil, pas après.",
     "risques": ("fuite_par_invite",)},
    {"cle": "redaction", "nom": "Rédaction des comptes rendus d'incident",
     "apport": "Produire vite un récit lisible, en pleine crise, quand "
               "personne n'a le temps d'écrire.",
     "ce_qu_on_croit_gagner": "Du temps. On en gagne — à condition que le "
                              "récit soit relu par quelqu'un qui était là.",
     "ce_que_ca_expose": "Un compte rendu d'incident notifié à une autorité "
                         "engage. Sous DORA comme sous NIS 2, il part dans "
                         "des délais courts et il ne se reprend pas.",
     "condition": "Relecture nommée avant toute notification externe. C'est "
                  "le seul cas de cette liste où l'erreur devient "
                  "réglementaire.",
     "risques": ("contenu_produit",)},
    {"cle": "detection_code", "nom": "Revue de code assistée",
     "apport": "Passer sur du volume que la revue humaine ne couvre pas.",
     "ce_qu_on_croit_gagner": "Le remplacement de la relecture. Non : "
                              "l'élargissement de sa couverture.",
     "ce_que_ca_expose": "Le code de la maison entre dans le modèle. Et si "
                         "le même modèle a produit ce code, la revue et la "
                         "production partagent le même angle mort.",
     "condition": "Ne jamais faire relire par le modèle qui a écrit. Le "
                  "défaut se transmet tel quel.",
     "risques": ("dependance_hallucinee",)},
)

ARSENAL_RESERVE = {
    "quoi": "L'arsenal défensif est lui-même un parc de systèmes d'IA.",
    "consequence": "Les cas d'usage de cette liste se cotent avec la même "
                   "chaîne d'autonomie, entrent dans le même inventaire, et "
                   "relèvent de la même dette d'antériorité que les cas "
                   "d'usage métier. C'est presque toujours sauté.",
    "le_signe": "Si l'inventaire des cas d'usage ne contient aucun cas porté "
                "par l'équipe sécurité, ce n'est pas qu'il n'y en a pas.",
}


# ═══════════════════════════════════════════════════════════════════════════
#  LES PATTERNS D'ARCHITECTURE — CE QUE LA DESIGN AUTHORITY PEUT PUBLIER
# ═══════════════════════════════════════════════════════════════════════════
#
# POURQUOI DES PATTERNS ET NON DES PRINCIPES. Un standard qui dit « il faut
# filtrer les entrées » ne se met pas en œuvre : chacun l'applique où ça
# l'arrange, et deux équipes produisent deux architectures également
# « conformes » et inégalement sûres. Un pattern dit OÙ, et ce qu'on perd
# quand on déplace.

PATTERNS = (
    {"cle": "rag_droits", "nom": "RAG — le contrôle d'accès à la RECHERCHE",
     "pour": ("assistant_interne",),
     "le_geste": "La requête de recherche porte l'identité de celui qui pose "
                 "la question, et l'index filtre AVANT de rendre les "
                 "passages. Le modèle ne voit que ce que la personne a le "
                 "droit de voir.",
     "l_anti_pattern": "Indexer avec un compte de service qui voit tout, "
                       "puis filtrer la réponse. Le modèle a lu, il a "
                       "raisonné, et il répondra juste sur ce qu'il n'aurait "
                       "pas dû lire — sans citer sa source.",
     "ce_qu_on_perd_a_deplacer": "La qualité des réponses baisse pour les "
                                 "profils peu habilités. C'est le prix, il "
                                 "se constate, et il vaut mieux l'annoncer "
                                 "que le découvrir.",
     "controles": ("filtrage_ia", "journal_agents")},
    {"cle": "rag_provenance", "nom": "RAG — la citation obligatoire",
     "pour": ("assistant_interne", "soc_augmente"),
     "le_geste": "Toute réponse porte les passages qui l'ont produite, et "
                 "l'interface les montre. Sans passage, pas de réponse.",
     "l_anti_pattern": "Une réponse fluide sans source. Elle se relit moins, "
                       "elle se cite davantage, et son erreur voyage.",
     "ce_qu_on_perd_a_deplacer": "Un peu de fluidité, et l'aveu que le "
                                 "système ne sait pas quand il ne trouve "
                                 "rien. Les deux sont des gains déguisés.",
     "controles": ("journal_agents",)},
    {"cle": "agent_identite", "nom": "Agentique — une identité par agent",
     "pour": ("agents_autonomes",),
     "le_geste": "L'agent porte sa propre identité, ses propres "
                 "habilitations, une durée de vie, et les systèmes appelés "
                 "voient l'agent — pas la personne.",
     "l_anti_pattern": "L'agent agit sous l'identité de l'utilisateur. Le "
                       "chemin le plus court, et il donne à l'agent tout ce "
                       "que la personne peut faire.",
     "ce_qu_on_perd_a_deplacer": "Un chantier d'annuaire. C'est le vrai "
                                 "coût, il est réel, et c'est lui qu'il faut "
                                 "poser sur la table au lieu de la sécurité "
                                 "en général.",
     "controles": ("iam_agents", "journal_agents")},
    {"cle": "agent_outils", "nom": "Agentique — le catalogue d'outils fermé",
     "pour": ("agents_autonomes",),
     "le_geste": "Les outils d'un agent sont énumérés à l'avance et revus. "
                 "Ajouter un serveur d'outils passe par une revue, pas par "
                 "une ligne de configuration.",
     "l_anti_pattern": "Un raccordement libre. La surface s'étend sans "
                       "passer par personne, et la description de chaque "
                       "outil entre dans l'invite du modèle.",
     "ce_qu_on_perd_a_deplacer": "De la vitesse d'expérimentation. On la "
                                 "rend en créant un bac à sable où le "
                                 "raccordement reste libre et les données "
                                 "sont fausses.",
     "controles": ("mcp", "iam_agents")},
    {"cle": "agent_arret", "nom": "Agentique — le point d'arrêt humain",
     "pour": ("agents_autonomes",),
     "le_geste": "Tout effet irréversible — virement, suppression, envoi, "
                 "publication — s'arrête devant un humain qui voit ce qui "
                 "va se produire, pas un résumé.",
     "l_anti_pattern": "Retirer la validation « parce qu'elle ralentit la "
                       "démonstration », et ne pas la remettre pour la mise "
                       "en service. C'est le scénario le plus fréquent, et "
                       "personne ne l'a décidé.",
     "ce_qu_on_perd_a_deplacer": "Le gain d'automatisation sur ces actions "
                                 "précises. Il reste entier sur toutes les "
                                 "autres.",
     "controles": ("iam_agents", "api", "journal_agents")},
    {"cle": "code_barriere", "nom": "Vibe coding — la barrière de fusion",
     "pour": ("vibe_coding",),
     "le_geste": "La chaîne refuse la fusion sans relecture nommée et sans "
                 "vérification des dépendances proposées. Le blocage est "
                 "technique, pas contractuel.",
     "l_anti_pattern": "Une consigne dans un guide. Elle tient trois "
                       "semaines, puis un jour de pression la traverse.",
     "ce_qu_on_perd_a_deplacer": "Du délai sur les petites demandes. On le "
                                 "rend en n'interdisant PAS l'outil : "
                                 "l'interdiction déplace l'usage hors de "
                                 "vue et on perd le gain et le contrôle.",
     "controles": ("revue_code_ia", "deps_ml")},
)


# ═══════════════════════════════════════════════════════════════════════════
#  LES TROIS DIRECTIONS — ET LA TROISIÈME EST CELLE QU'ON OUBLIE
# ═══════════════════════════════════════════════════════════════════════════

DIRECTIONS = (
    {"cle": "cyber_for_ai", "nom": "Sécuriser l'IA (Cyber for AI)",
     "quoi": "Protéger les systèmes d'IA de la maison : gouvernance, "
             "standards, chaîne de production, épreuve, sensibilisation.",
     "le_perimetre_depend_de": "Ce que la maison déploie. Il se réduit en "
                               "renonçant à des cas d'usage."},
    {"cle": "ai_for_cyber", "nom": "Augmenter la cyber par l'IA (AI for Cyber)",
     "quoi": "Employer l'IA dans l'arsenal défensif : tri, enquête, "
             "rédaction, remédiation.",
     "le_perimetre_depend_de": "Ce que la direction cyber décide d'outiller. "
                               "Il se réduit en renonçant aux outils — et "
                               "chaque outil retenu rejoint la direction "
                               "précédente."},
    # ═══ LA TROISIÈME, ET LA SEULE QU'ON NE PEUT PAS RÉDUIRE ════════════
    {"cle": "ai_enabled", "nom": "Menaces armées par l'IA (AI-enabled)",
     "quoi": "L'attaquant emploie l'IA contre vous : hypertrucage, "
             "ingénierie sociale assistée, fraude générative.",
     "le_perimetre_depend_de": "RIEN QUE VOUS CONTRÔLIEZ. Une banque sans "
                               "aucun système d'IA y est exposée à "
                               "l'identique. C'est la seule des trois "
                               "directions dont le périmètre ne se réduit "
                               "pas en renonçant à l'IA — et c'est pour "
                               "cela qu'elle ne doit pas être traitée comme "
                               "un chapitre des deux autres."},
)

MENACES_ARMEES = (
    {"cle": "hypertrucage", "nom": "Hypertrucage (deepfake) de dirigeant",
     "quoi": "Voix ou visage imités pour obtenir un virement, une "
             "validation, un accès — sur un canal qui inspire confiance "
             "parce qu'on y reconnaît quelqu'un.",
     "ce_qui_la_rend_efficace": "Le canal, pas la qualité de l'imitation. Un "
                                "appel en urgence d'un supérieur au moment "
                                "d'une clôture réussit avec une imitation "
                                "médiocre.",
     "la_parade": "Un canal de contre-appel connu de tous et jamais "
                  "improvisé. La technique ne se détecte pas de façon "
                  "fiable ; le procédé, lui, se casse en changeant de canal.",
     "ce_qui_ne_marche_pas": "La détection d'hypertrucage comme unique "
                             "réponse. Elle court après un progrès plus "
                             "rapide qu'elle.",
     "equipe": "cyberdefense"},
    {"cle": "ingenierie_sociale", "nom": "Ingénierie sociale assistée",
     "quoi": "Des messages ciblés, sans faute, dans le contexte exact de la "
             "victime, produits en volume.",
     "ce_qui_la_rend_efficace": "La disparition des signaux sur lesquels on a "
                                "formé les collaborateurs pendant dix ans — "
                                "la faute d'orthographe, la formule "
                                "étrange, l'adresse approximative.",
     "la_parade": "Déplacer la sensibilisation du « repérer le faux » vers "
                  "le « vérifier la demande » : ce qui protège n'est plus "
                  "l'indice, c'est le geste.",
     "ce_qui_ne_marche_pas": "Les campagnes de simulation qui notent les "
                             "collaborateurs sur leur capacité à repérer un "
                             "indice qui n'existe plus.",
     "equipe": "securite_ia"},
    {"cle": "fraude_generative", "nom": "Fraude générative",
     "quoi": "Pièces justificatives, identités, historiques produits en "
             "série pour franchir des contrôles d'entrée en relation.",
     "ce_qui_la_rend_efficace": "Le volume. Un contrôle qui tient contre dix "
                                "dossiers falsifiés par mois cède contre "
                                "mille.",
     "la_parade": "Des contrôles qui s'appuient sur des sources tierces "
                  "vérifiables plutôt que sur l'apparence du document.",
     "ce_qui_ne_marche_pas": "Renforcer l'examen visuel. Il coûte "
                             "proportionnellement au volume, l'attaque non.",
     "equipe": "cyberdefense"},
)


# ═══════════════════════════════════════════════════════════════════════════
#  AI FOR CYBER — CE QUI SE MESURE, ET CE QU'ON PROMET À TORT
# ═══════════════════════════════════════════════════════════════════════════
#
# LA STRATÉGIE PLURIANNUELLE NE SE CHIFFRE PAS ICI, et c'est délibéré : elle
# dépend de l'outillage en place, des volumes, et des équipes. Ce que le
# module porte, c'est la DISTINCTION entre ce qui se mesure et ce qui se
# promet — parce que c'est sur cette confusion que ces programmes déçoivent.

AI_FOR_CYBER = (
    {"cle": "mttr", "nom": "Réduction du MTTR de remédiation",
     "ce_qui_se_mesure": "Le délai entre la publication d'une vulnérabilité "
                         "et sa remédiation effective, avant et après.",
     "ce_qu_on_promet_a_tort": "Que l'IA corrige. Elle ne corrige pas : elle "
                               "PRIORISE, elle rédige le ticket, elle "
                               "propose le correctif. La remédiation reste "
                               "un déploiement, avec sa fenêtre et son "
                               "risque de régression.",
     "le_vrai_gain": "Le tri. Sur un stock de plusieurs milliers de "
                     "vulnérabilités, l'essentiel du délai est le temps "
                     "passé à décider par quoi commencer.",
     "equipe": "vulnerabilites"},
    {"cle": "dette_vuln", "nom": "Résorption de la dette de vulnérabilités",
     "ce_qui_se_mesure": "Le stock, son âge moyen, et sa tendance.",
     "ce_qu_on_promet_a_tort": "Qu'elle disparaîtra. Le stock ne se vide "
                               "pas : il se stabilise, et le succès est un "
                               "âge moyen qui cesse de monter.",
     "le_vrai_gain": "L'exploitabilité réelle contextualisée : savoir "
                     "lesquelles des mille sont atteignables depuis "
                     "l'extérieur vaut mieux que corriger vite les mille.",
     "equipe": "vulnerabilites"},
    {"cle": "tri_soc", "nom": "Tri du flux d'alertes",
     "ce_qui_se_mesure": "La part d'alertes traitées, et le délai de "
                         "première qualification.",
     "ce_qu_on_promet_a_tort": "Moins de faux positifs. Le nombre ne baisse "
                               "pas — c'est le temps passé dessus qui "
                               "baisse.",
     "le_vrai_gain": "Le temps d'analyste rendu aux enquêtes. Encore "
                     "faut-il qu'il y soit affecté, sinon le gain se dissout "
                     "en réduction d'effectif et la capacité d'enquête "
                     "baisse.",
     "equipe": "cyberdefense"},
)


# ═══════════════════════════════════════════════════════════════════════════
#  LE CADRE BANCAIRE — TROIS TEXTES, ET AUCUN NE SE DÉDUIT DES DEUX AUTRES
# ═══════════════════════════════════════════════════════════════════════════

CADRE_BANCAIRE = {
    "dora": {
        "texte": "Règlement (UE) 2022/2554 (DORA)",
        "depuis": "2025-01-17",
        "ce_qu_il_impose_a_une_usine_ia": (
            "Le fournisseur de modèle est un prestataire tiers de services "
            "TIC : il entre au registre d'information, son contrat porte les "
            "clauses obligatoires, et une stratégie de sortie est approuvée "
            "par l'organe de direction.",
            "Les incidents majeurs liés aux TIC se notifient dans les délais "
            "du règlement — un incident d'IA n'a pas de régime à part.",
            "Les tests de résilience opérationnelle numérique couvrent les "
            "systèmes qui soutiennent des fonctions critiques : une usine IA "
            "qui en soutient une y entre.",
        ),
        "le_piege": "Le registre tenu au niveau groupe et jamais réconcilié "
                    "avec les raccordements réels des équipes. Un modèle "
                    "appelé depuis un cahier de notes de science des données "
                    "est un prestataire TIC non enregistré.",
    },
    "nis2": {
        "texte": "Directive (UE) 2022/2555 (NIS 2)",
        "ce_qu_il_faut_savoir": (
            "L'article 4 écarte les dispositions correspondantes de NIS 2 — "
            "supervision et exécution comprises — lorsqu'un acte sectoriel "
            "de l'Union impose des exigences d'effet AU MOINS ÉQUIVALENT. "
            "DORA est cet acte pour les entités financières.",
            "La conséquence pratique : on n'empile pas les deux régimes sur "
            "une même entité pour les matières que DORA couvre. Le faire "
            "coûte une double charge déclarative que personne n'exige.",
            "La réserve : lorsque l'acte sectoriel ne couvre pas TOUTES les "
            "entités d'un secteur, NIS 2 continue de s'appliquer aux entités "
            "non couvertes. Un groupe bancaire porte souvent les deux "
            "régimes selon l'entité.",
        ),
        "article": "art. 4, §§1 et 2",
    },
    "ia_act": {
        "texte": "Règlement (UE) 2024/1689 (règlement sur l'IA)",
        "ce_qui_touche_une_banque": (
            "L'évaluation de la solvabilité de personnes physiques et "
            "l'établissement de leur note de crédit relèvent de l'annexe III "
            "— donc du régime des systèmes à HAUT RISQUE, avec les "
            "obligations qui l'accompagnent.",
            "Beaucoup d'équipes qui construisent ces modèles l'ignorent, "
            "parce que le sujet est arrivé par la conformité et non par la "
            "chaîne de production.",
            "Les obligations de transparence s'appliquent aussi aux cas "
            "d'usage ordinaires : un assistant qui dialogue avec un client "
            "doit se faire connaître comme machine.",
        ),
    },
    "dit": "Les trois se combinent sur une usine IA bancaire, et aucun ne se "
           "déduit des deux autres : DORA regarde la résilience et les "
           "prestataires, le règlement sur l'IA regarde l'usage et ses "
           "effets sur les personnes, NIS 2 s'efface là où DORA le couvre et "
           "reste ailleurs.",
}


# ═══════════════════════════════════════════════════════════════════════════
#  LE RÉFÉRENTIEL, ET LA CONTRE-EXPERTISE D'ENSEMBLE
# ═══════════════════════════════════════════════════════════════════════════

def referentiel():
    """Tout ce que la page doit afficher, servi par le moteur.

    L'ÉCRAN NE RECOPIE RIEN. Dix-huit contrôles, dix risques, cinq cas
    d'usage, six patterns et trois directions recopiés dans le JavaScript
    auraient divergé du moteur au premier amendement — et la divergence se
    serait vue chez le client, pas ici.
    """
    return {
        "directions": list(DIRECTIONS),
        "phases": list(PHASES),
        "equipes": list(EQUIPES),
        "controles": [dict(c, equipe_nom=EQUIPES_PAR_CLE[c["equipe"]]["nom"],
                           maillons=list(c["maillons"]),
                           prerequis=list(c["prerequis"]))
                      for c in CONTROLES],
        "risques": [dict(r, famille_nom=FAMILLES_RISQUE[r["famille"]],
                         controles=list(r["controles"]))
                    for r in RISQUES],
        "familles_risque": dict(FAMILLES_RISQUE),
        "cas_usage": [dict(c, risques=list(c["risques"]),
                           controles_requis=list(c["controles_requis"]))
                      for c in CAS_USAGE],
        "patterns": [dict(p, pour=list(p["pour"]),
                          controles=list(p["controles"])) for p in PATTERNS],
        "architecture": [dict(a, risques=list(a["risques"]))
                         for a in ARCHITECTURE],
        "arsenal": [dict(a, risques=list(a["risques"])) for a in ARSENAL],
        "arsenal_reserve": ARSENAL_RESERVE,
        "ai_for_cyber": list(AI_FOR_CYBER),
        "menaces_armees": list(MENACES_ARMEES),
        "cadre_bancaire": CADRE_BANCAIRE,
        "issues": list(ISSUES),
        "sources": sources(),
        "reserve": "Ce module structure un constat DÉCLARÉ. Personne n'est "
                   "venu voir, rien n'a été éprouvé, et aucun délai affiché "
                   "n'est un engagement : ce sont des ordres de grandeur de "
                   "mise en place, chacun accompagné de ce qu'il suppose.",
    }


def contre_expertise(dossier=None, aujourdhui=None):
    """La contre-expertise complète — dette, feuille de route, alertes.

    L'ORDRE DE LA RESTITUTION EST CELUI D'UNE RÉUNION QUI SE PASSE BIEN :
    d'abord ce qui est déjà parti sans contrôle — le fait, que personne ne
    discute —, ensuite l'ordre imposé par les prérequis — qui n'est pas une
    préférence —, et seulement après les ambitions qui ne tiennent pas.
    Commencer par les alertes met la salle en défense avant le premier
    chiffre.
    """
    d = dossier or {}
    if not isinstance(d, dict):
        return {"ok": False, "motif": "dossier_illisible"}
    nom = str(d.get("nom") or "").strip()
    if not nom:
        return {"ok": False, "motif": "nom_manquant"}
    jour = _aujourdhui(aujourdhui)
    phase = d.get("phase") if d.get("phase") in PHASES_PAR_CLE else None

    la_dette = dette(d.get("cas_usage"), d.get("controles"), jour)
    if not la_dette.get("ok"):
        return la_dette
    route = feuille_de_route(d.get("controles"), depart=jour)
    if not route.get("ok"):
        return route

    alertes = []
    for a in (d.get("ambitions") or []):
        r = alerte(a, d.get("controles"), jour)
        if r.get("ok"):
            alertes.append(r)
    incompatibles = [a for a in alertes if not a["compatible"]]

    # ── CE QUI COMMANDE LA RESTITUTION ───────────────────────────────────
    if not la_dette["inventaire_tenu"]:
        tete, dit = "inventaire_absent", (
            "Rien d'autre ne se calcule tant que l'inventaire des cas "
            "d'usage n'est pas tenu. Ce n'est pas le contrôle le plus "
            "coûteux — trente jours, aucun prérequis — c'est celui sans "
            "lequel tous les chiffres suivants portent sur un périmètre "
            "inconnu.")
    elif la_dette["cas_en_dette"]:
        tete, dit = "dette", (
            "%d cas d'usage tournent sans un contrôle requis. C'est le fait "
            "à poser en premier : il ne se discute pas, il se soustrait."
            % la_dette["cas_en_dette"])
    elif incompatibles:
        tete, dit = "ambition", (
            "Rien n'est parti sans contrôle ; %d ambition(s) ne tiennent pas "
            "dans le temps que les contrôles demandent."
            % len(incompatibles))
    else:
        tete, dit = "tenu", (
            "Rien en dette, aucune ambition en écart. C'est le moment où la "
            "contre-expertise sert le plus et où on l'arrête le plus "
            "souvent : l'écart se creuse pendant la montée en charge, pas à "
            "son départ.")

    return {
        "ok": True,
        "nom": nom,
        "aujourdhui": jour.isoformat(),
        "phase": dict(PHASES_PAR_CLE[phase], cle=phase) if phase else None,
        "dette": la_dette,
        "feuille_de_route": route,
        "alertes": alertes,
        "incompatibles": len(incompatibles),
        "tete": tete,
        "dit": dit,
        "reserve": referentiel()["reserve"],
    }


# ═══════════════════════════════════════════════════════════════════════════
#  LA GARDE — CE QUE CE MODULE REFUSE DE LAISSER PASSER
# ═══════════════════════════════════════════════════════════════════════════

def _verifier():
    fautes = []

    # ── LES ÉQUIPES : UN CONTRÔLE ORPHELIN NE SERA JAMAIS CONSTRUIT ──────
    for c in CONTROLES:
        if c.get("equipe") not in EQUIPES_PAR_CLE:
            fautes.append("le contrôle « %s » ne nomme aucune équipe qui le "
                          "porte" % c["cle"])
    # UNE ÉQUIPE A UN RÔLE DANS L'UN DES DEUX SENS, PAS FORCÉMENT LES DEUX.
    # La gestion des vulnérabilités ne porte aucun contrôle « Cyber for AI »
    # et c'est normal : son rôle est dans l'autre sens, « AI for Cyber ».
    # Une garde qui n'aurait regardé que CONTROLES aurait réclamé un
    # contrôle inventé pour elle — et on l'aurait écrit.
    portes = ({c["equipe"] for c in CONTROLES}
              | {t["equipe"] for t in AI_FOR_CYBER})
    for e in EQUIPES:
        if e["cle"] not in portes:
            fautes.append("l'équipe « %s » ne porte ni contrôle « Cyber "
                          "for AI » ni chantier « AI for Cyber » : elle "
                          "figure au tableau sans y avoir de rôle"
                          % e["cle"])

    # ── LES CONTRÔLES ────────────────────────────────────────────────────
    if len(CONTROLES_PAR_CLE) != len(CONTROLES):
        fautes.append("deux contrôles portent la même clé")
    for c in CONTROLES:
        if not isinstance(c.get("delai_jours"), int) or c["delai_jours"] <= 0:
            fautes.append("le contrôle « %s » n'a pas de délai de mise en "
                          "place exploitable" % c["cle"])
        if not str(c.get("suppose") or "").strip():
            fautes.append("le contrôle « %s » ne dit pas ce que son délai "
                          "suppose — un délai sans hypothèse est une "
                          "promesse" % c["cle"])
        if not str(c.get("ce_qu_il_ne_fait_pas") or "").strip():
            fautes.append("le contrôle « %s » ne dit pas ce qu'il ne fait "
                          "PAS" % c["cle"])
        for p in c["prerequis"]:
            if p not in CONTROLES_PAR_CLE:
                fautes.append("le contrôle « %s » exige un prérequis inconnu "
                              ": %s" % (c["cle"], p))
            if p == c["cle"]:
                fautes.append("le contrôle « %s » est son propre prérequis"
                              % c["cle"])
        for m in c["maillons"]:
            if m not in chaine_autonomie._PAR_CLE:
                fautes.append("le contrôle « %s » cite un maillon inconnu de "
                              "la chaîne d'autonomie : %s" % (c["cle"], m))

    # ── LE GRAPHE DES PRÉREQUIS N'A PAS DE CYCLE ────────────────────────
    #
    # SANS CETTE VÉRIFICATION, la feuille de route rendrait un refus au
    # moment où un client s'en sert, plutôt qu'au chargement du module.
    r = feuille_de_route({}, depart="2026-01-01")
    if not r.get("ok"):
        fautes.append("la feuille de route ne se construit pas : %s"
                      % r.get("motif"))
    else:
        places = {c["cle"] for l in r["lots"] for c in l["controles"]}
        if places != set(CONTROLES_PAR_CLE):
            fautes.append("la feuille de route ne place pas tous les "
                          "contrôles : %s"
                          % sorted(set(CONTROLES_PAR_CLE) - places))

    # ── LES RISQUES ──────────────────────────────────────────────────────
    if len(RISQUES_PAR_CLE) != len(RISQUES):
        fautes.append("deux risques portent la même clé")
    menaces = {m["cle"] for m in chaine_autonomie.MENACES}
    for x in RISQUES:
        if x["famille"] not in FAMILLES_RISQUE:
            fautes.append("le risque « %s » est d'une famille inconnue"
                          % x["cle"])
        if x["maillon"] not in chaine_autonomie._PAR_CLE:
            fautes.append("le risque « %s » cite un maillon inconnu : %s"
                          % (x["cle"], x["maillon"]))
        if x["menace"] is not None and x["menace"] not in menaces:
            fautes.append("le risque « %s » cite une menace absente du "
                          "catalogue : %s" % (x["cle"], x["menace"]))
        if not str(x.get("pourquoi_ca_passe") or "").strip():
            fautes.append("le risque « %s » ne dit pas pourquoi il passe — "
                          "sans cela il ne se traite pas" % x["cle"])
        for c in x["controles"]:
            if c not in CONTROLES_PAR_CLE:
                fautes.append("le risque « %s » renvoie à un contrôle "
                              "inconnu : %s" % (x["cle"], c))
    for f in FAMILLES_RISQUE:
        if not any(x["famille"] == f for x in RISQUES):
            fautes.append("la famille de risque « %s » est vide" % f)

    # ── LES CAS D'USAGE ──────────────────────────────────────────────────
    for c in CAS_USAGE:
        for r_ in c["risques"]:
            if r_ not in RISQUES_PAR_CLE:
                fautes.append("le cas « %s » cite un risque inconnu : %s"
                              % (c["cle"], r_))
        for k in c["controles_requis"]:
            if k not in CONTROLES_PAR_CLE:
                fautes.append("le cas « %s » exige un contrôle inconnu : %s"
                              % (c["cle"], k))
        if not c["controles_requis"]:
            fautes.append("le cas « %s » n'exige aucun contrôle : il ne "
                          "pourra jamais entrer en dette" % c["cle"])
        if not str(c.get("signal_d_alerte") or "").strip():
            fautes.append("le cas « %s » ne dit pas à quoi on voit qu'il "
                          "dérape" % c["cle"])
    # LES DEUX QUE LA DEMANDE NOMME EXISTENT, ET SOUS CE NOM.
    for cle in ("vibe_coding", "agents_autonomes"):
        if cle not in CAS_PAR_CLE:
            fautes.append("le cas d'usage « %s » a disparu" % cle)

    # ── LES PATTERNS ─────────────────────────────────────────────────────
    for p in PATTERNS:
        if not str(p.get("l_anti_pattern") or "").strip():
            fautes.append("le pattern « %s » ne dit pas à quoi ressemble "
                          "l'anti-pattern — sans lui il ne challenge rien"
                          % p["cle"])
        for c in p["pour"]:
            if c not in CAS_PAR_CLE:
                fautes.append("le pattern « %s » vise un cas inconnu : %s"
                              % (p["cle"], c))
        for c in p["controles"]:
            if c not in CONTROLES_PAR_CLE:
                fautes.append("le pattern « %s » cite un contrôle inconnu : "
                              "%s" % (p["cle"], c))

    # ── LE CHALLENGE D'ARCHITECTURE ──────────────────────────────────────
    for a in ARCHITECTURE:
        if not str(a.get("mauvaise_reponse") or "").strip():
            fautes.append("la question d'architecture « %s » ne dit pas à "
                          "quoi ressemble une mauvaise réponse : elle se "
                          "remplit et ne challenge rien" % a["cle"])
        for r_ in a["risques"]:
            if r_ not in RISQUES_PAR_CLE:
                fautes.append("la question « %s » cite un risque inconnu : "
                              "%s" % (a["cle"], r_))

    # ── LES TROIS ISSUES DE L'ALERTE ─────────────────────────────────────
    if len(ISSUES) != 3:
        fautes.append("l'alerte ne porte pas ses trois issues : %d"
                      % len(ISSUES))
    if {i["cle"] for i in ISSUES} != {"reduire", "decaler", "accepter"}:
        fautes.append("les trois issues ne sont plus réduire, décaler, "
                      "accepter")
    for i in ISSUES:
        if not str(i.get("qui_tranche") or "").strip():
            fautes.append("l'issue « %s » ne dit pas qui tranche — et ce "
                          "n'est jamais la sécurité" % i["cle"])

    # ── LES TROIS DIRECTIONS, DONT CELLE QU'ON NE RÉDUIT PAS ─────────────
    if len(DIRECTIONS) != 3:
        fautes.append("les directions ne sont plus trois : %d"
                      % len(DIRECTIONS))
    aie = [d for d in DIRECTIONS if d["cle"] == "ai_enabled"]
    if not aie:
        fautes.append("la direction « menaces armées par l'IA » a disparu — "
                      "c'est la seule dont le périmètre ne se réduit pas en "
                      "renonçant à l'IA")
    elif "RIEN" not in aie[0]["le_perimetre_depend_de"]:
        fautes.append("la direction « ai_enabled » ne dit plus que son "
                      "périmètre ne dépend de rien qu'on contrôle")
    if not MENACES_ARMEES:
        fautes.append("aucune menace armée par l'IA n'est décrite")
    for m in MENACES_ARMEES:
        if not str(m.get("ce_qui_ne_marche_pas") or "").strip():
            fautes.append("la menace « %s » ne dit pas ce qui ne marche pas "
                          "contre elle" % m["cle"])
        if m["equipe"] not in EQUIPES_PAR_CLE:
            fautes.append("la menace « %s » nomme une équipe inconnue"
                          % m["cle"])

    # ── L'ARSENAL ET SA RÉSERVE ──────────────────────────────────────────
    for a in ARSENAL:
        if not str(a.get("ce_que_ca_expose") or "").strip():
            fautes.append("le cas d'arsenal « %s » ne dit pas ce qu'il "
                          "expose" % a["cle"])
        for r_ in a["risques"]:
            if r_ not in RISQUES_PAR_CLE:
                fautes.append("l'arsenal « %s » cite un risque inconnu : %s"
                              % (a["cle"], r_))
    if not ARSENAL_RESERVE.get("le_signe"):
        fautes.append("la réserve de l'arsenal ne dit plus à quoi on voit "
                      "que le SOC n'est pas à l'inventaire")
    if "soc_augmente" not in CAS_PAR_CLE:
        fautes.append("le SOC augmenté n'est plus un cas d'usage : "
                      "l'arsenal redeviendrait invisible à l'inventaire")
    for x in AI_FOR_CYBER:
        if not str(x.get("ce_qu_on_promet_a_tort") or "").strip():
            fautes.append("« %s » ne dit pas ce qu'on promet à tort" % x["cle"])

    # ── LES PHASES ───────────────────────────────────────────────────────
    rangs = sorted(p["rang"] for p in PHASES)
    if rangs != list(range(len(PHASES))):
        fautes.append("les rangs de phase ne sont pas 0..n : %s" % rangs)

    # ── LES SOURCES ──────────────────────────────────────────────────────
    for s in SOURCES:
        if not str(s.get("licence") or "").strip():
            fautes.append("la source « %s » ne dit pas sous quelle licence "
                          "elle est reprise" % s.get("court"))
        if not str(s.get("url") or "").strip():
            fautes.append("la source « %s » n'a pas d'adresse : une source "
                          "sans adresse est une intention" % s.get("court"))

    # ── LE CADRE BANCAIRE ────────────────────────────────────────────────
    if "4" not in (CADRE_BANCAIRE.get("nis2") or {}).get("article", ""):
        fautes.append("le cadre bancaire ne cite plus l'article 4 de NIS 2 — "
                      "c'est lui qui dit que DORA écarte les dispositions "
                      "correspondantes")
    if not (CADRE_BANCAIRE.get("dora") or {}).get("depuis"):
        fautes.append("le cadre bancaire ne dit plus depuis quand DORA "
                      "s'applique")

    if fautes:
        raise RuntimeError("contre_expertise_ia — table incohérente : "
                           + " ; ".join(fautes))
    return fautes


_FAUTES = _verifier()
