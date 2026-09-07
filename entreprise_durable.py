# -*- coding: utf-8 -*-
"""Les trente propositions pour des entreprises durables, appliquées aux centres
de données.

CE QUE CE MODULE PORTE. Les trente propositions du Cercle de Giverny (édition
2026), réparties en six thèmes : villes et logements, énergie et numérique,
santé mentale, infrastructures critiques, eau, parcours scientifiques. Chacune
est citée sous son intitulé d'origine, avec ce que le document en dit — et non
avec ce qu'on aimerait qu'elle dise.

LA DISTINCTION QUI FAIT TOUT LE TRAVAIL, ET SANS LAQUELLE CE MODULE SERAIT
FAUX. Ces trente propositions sont des RECOMMANDATIONS DE POLITIQUE PUBLIQUE.
Elles s'adressent au législateur, aux régulateurs, aux branches
professionnelles ; plusieurs d'entre elles — instaurer une tarification
incitative de l'eau, créer un indicateur national, réformer les cotisations
AT/MP — ne sont tout simplement pas des gestes qu'un maître d'ouvrage peut
poser. Les aligner en liste à cocher produirait une grille de conformité à un
texte qui n'en est pas une, et ferait signer au client des engagements qui ne
lui appartiennent pas.

Chaque proposition porte donc une PORTÉE, qui dit ce que ce projet-ci peut en
faire :

  · DÉCIDE    — le maître d'ouvrage peut agir seul, dans son périmètre. C'est
                un arbitrage de projet, et il se chiffre.
  · ANTICIPE  — c'est une politique publique qui, si elle advient, s'appliquera
                au projet. On ne la met pas en œuvre : on prépare la pièce
                qu'elle demandera, et on regarde ce qu'elle change au chiffrage.
  · CONTRIBUE — le projet ne décide de rien ici, il peut au mieux participer.
                Prétendre davantage serait une revendication sans objet.

Treize propositions relèvent de la décision, dix de l'anticipation, sept de la
contribution. Ce comptage n'est pas un résultat : c'est une lecture, faite ici
et assumée comme telle, qu'un lecteur peut contester proposition par
proposition — d'où le champ `pour_le_centre`, qui dit POURQUOI la portée est
celle-là.

CE QUE LA VERSION 2026-09-b AJOUTE, ET LE DÉFAUT QU'ELLE CORRIGE

Chaque proposition du document porte trois à cinq MESURES. Le champ `dit` les
compressait en une phrase, et une portée unique les couvrait toutes. Or à
l'intérieur d'une même proposition les mesures ne se ressemblent pas :
« instaurer une tarification incitative » est un acte de puissance publique,
« intégrer un stress test hydrique à l'évaluation du projet » est un geste que
le maître d'ouvrage pose seul, aujourd'hui.

CE QUE LA COMPRESSION COÛTAIT, VÉRIFIÉ SUR LE CODE. La proposition 25 est lue
CONTRIBUE — ce qui est juste pour l'ensemble : un centre de données ne
structure pas la recherche nationale sur l'eau. Mais deux de ses quatre mesures
sont la formation de ses propres exploitants aux risques hydriques, et cela il
le décide seul. Comme `hors_couverture()` ne regarde que les propositions
DÉCIDE ou ANTICIPE, ces deux mesures ne pouvaient apparaître dans AUCUN
livrable, quel que soit le projet. `mesures_masquees()` les rend.

Les mesures sont relevées pour les thèmes « eau », « énergie & numérique » et
« infrastructures critiques » — quinze propositions sur trente,
cinquante-huit mesures. `couverture_mesures()` le dit : les quinze autres ne
sont pas des propositions sans mesures, ce sont des propositions dont les
mesures ne sont pas dépouillées ici.

CE QUE LE GARDE-FOU A FAIT GAGNER, SUR LE THÈME DES INFRASTRUCTURES. La
proposition 20 est lue ANTICIPE, et sa justification tient à son chapeau : la
directive européenne sur la résilience des entités critiques s'appliquera au
projet. Or un chapeau n'est pas une mesure, et les quatre mesures relèvent
d'un collectif — un guide, des instances, un label. Le contrôle d'import a
donc obligé à désigner LAQUELLE porte l'anticipation : la première, parce
qu'un guide harmonisé traduisant les exigences en actions « auditables et
comparables » est, une fois écrit, le référentiel sur lequel le projet sera
examiné. La question ne se serait pas posée sans le contrôle.

CE QUE CE MODULE NE FAIT PAS. Il ne décerne aucune conformité : ces
propositions ne sont ni une norme, ni un référentiel certifiable, ni un texte
en vigueur. Il ne les récrit pas non plus : `titre` et `dit` restent au plus
près du document ; `pour_le_centre` est la transposition, et elle est de
CONSEILPREV, pas du Cercle de Giverny. Confondre les deux ferait dire à
l'auteur ce qu'il n'a pas écrit.
"""

VERSION = "2026-09-c"

# La source, citée une fois et lue partout. Le champ `nature` est là pour être
# RÉPÉTÉ dans le livrable : un lecteur qui trouve trente propositions numérotées
# dans un document d'étude les prendra pour une norme si rien ne l'en dissuade.
SOURCE = {
    "titre": "30 propositions pour des entreprises durables",
    "auteur": "Cercle de Giverny",
    "edition": "Édition 2026",
    "nature": "Contribution d'un think tank — recommandations adressées aux "
              "responsables publics et économiques. Ni norme, ni référentiel "
              "certifiable, ni texte en vigueur.",
}

THEMES = [
    {"cle": "villes", "nom": "Villes & logements",
     "question": "Comment adapter les villes et les logements aux chocs "
                 "climatiques ?"},
    {"cle": "energie_numerique", "nom": "Énergie & numérique",
     "question": "Comment bâtir une souveraineté énergétique et numérique "
                 "compétitive au service de la puissance européenne ?"},
    {"cle": "sante_mentale", "nom": "Santé mentale",
     "question": "Quel rôle pour l'entreprise dans une société sous tension ?"},
    {"cle": "infrastructures", "nom": "Infrastructures critiques",
     "question": "Comment sécuriser les infrastructures critiques face aux "
                 "risques systémiques ?"},
    {"cle": "eau", "nom": "Eau",
     "question": "Comment la gestion durable de l'eau participe-t-elle à la "
                 "souveraineté et à la transition écologique industrielle ?"},
    {"cle": "sciences", "nom": "Parcours scientifiques",
     "question": "Comment développer l'attractivité des parcours "
                 "scientifiques ?"},
]

PORTEES = {
    "decide": {
        "nom": "Le projet décide",
        "dit": "Le maître d'ouvrage peut agir seul, dans son périmètre. "
               "C'est un arbitrage de projet, et il se chiffre.",
    },
    "anticipe": {
        "nom": "Le projet anticipe",
        "dit": "Politique publique qui, si elle advient, s'appliquera au "
               "projet. On ne la met pas en œuvre : on prépare la pièce "
               "qu'elle demandera, et on regarde ce qu'elle change au "
               "chiffrage.",
    },
    "contribue": {
        "nom": "Le projet contribue",
        "dit": "Le projet ne décide de rien ici. Il peut participer ; "
               "prétendre davantage serait une revendication sans objet.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  LES TRENTE
#
#  `titre` et `dit` : le document. `pour_le_centre` : la transposition, qui
#  est de nous. `enjeux` : les clés du registre de `strategie_dd` que la
#  proposition touche — vérifiées là-bas, au chargement, pour que l'import ne
#  parte que dans un sens.
# ═══════════════════════════════════════════════════════════════════════════

PROPOSITIONS = [
    # ── Villes & logements ────────────────────────────────────────────────
    {"numero": 1, "cle": "habitabilite", "theme": "villes",
     "titre": "Instituer un plan d'habitabilité climatique dans chaque "
              "territoire.",
     "dit": "Faire passer les documents d'urbanisme d'une logique de "
            "constructibilité à une logique d'habitabilité : trajectoire à "
            "2050, et vérification explicite de la disponibilité en eau, de "
            "l'exposition aux aléas et de la capacité de rafraîchissement "
            "avant toute ouverture à l'urbanisation ou grand projet.",
     "portee": "anticipe",
     "pour_le_centre": "L'implantation se justifierait devant un document qui "
                       "demande la ressource en eau et l'exposition aux aléas "
                       "AVANT la constructibilité. Ce sont deux pièces à "
                       "produire au dossier d'urbanisme, pas des conclusions "
                       "de fin d'étude.",
     "enjeux": ["foncier", "conflit_usage_eau"]},

    {"numero": 2, "cle": "ville_eponge", "theme": "villes",
     "titre": "Faire de l'eau une infrastructure de résilience urbaine avec "
              "des « villes éponges ».",
     "dit": "Désimperméabilisation, infiltration à la source, stockage "
            "temporaire, sols vivants et végétalisation rafraîchissante ; "
            "gestion dynamique des réseaux arbitrant entre infiltration, "
            "stockage, réutilisation locale et évacuation.",
     "portee": "decide",
     "pour_le_centre": "Une parcelle de centre de données est massivement "
                       "imperméable — bâtiment, voiries lourdes, aires de "
                       "livraison. La part de surfaces perméables et "
                       "l'infiltration à la source se décident au plan-masse, "
                       "et ne se rattrapent jamais ensuite.",
     "enjeux": ["foncier", "conflit_usage_eau"]},

    {"numero": 3, "cle": "passeport_habitabilite", "theme": "villes",
     "titre": "Créer un passeport d'habitabilité climatique du logement et du "
              "quartier.",
     "dit": "Le diagnostic énergétique dit l'énergie, mais peu de la capacité "
            "à rester vivable en canicule, sécheresse ou pluie extrême. Le "
            "passeport mesurerait le confort d'été passif, la vulnérabilité "
            "aux aléas, l'accès à l'eau et à l'ombre, la part de surfaces "
            "perméables et la capacité de fonctionnement en mode dégradé.",
     "portee": "anticipe",
     "pour_le_centre": "« La capacité de fonctionnement en mode dégradé » est "
                       "exactement ce qu'un centre de données appelle son mode "
                       "secours. Le vocabulaire du passeport rejoint le sien : "
                       "les mêmes preuves serviront des deux côtés.",
     "enjeux": ["resilience", "secours", "foncier"]},

    {"numero": 4, "cle": "fiscalite_reemploi", "theme": "villes",
     "titre": "Orienter la fiscalité et l'assurance vers le réemploi, la "
              "sobriété matérielle et la robustesse climatique.",
     "dit": "Incitations ciblées pour le réemploi, la conservation du carbone "
            "incorporé et la désartificialisation ; bonus de constructibilité "
            "ou abattements locaux sur gain mesurable ; bonus-malus "
            "assurantiel lié à la robustesse climatique du bien.",
     "portee": "anticipe",
     "pour_le_centre": "Le carbone incorporé et le réemploi cesseraient d'être "
                       "des arguments de communication pour devenir des termes "
                       "de prime d'assurance et de fiscalité locale — "
                       "c'est-à-dire des lignes du compte d'exploitation.",
     "enjeux": ["carbone_incorpore", "materiaux", "fin_de_vie", "resilience"]},

    {"numero": 5, "cle": "contrat_adaptation", "theme": "villes",
     "titre": "Mettre en place des contrats territoriaux d'adaptation "
              "associant élus, opérateurs et citoyens.",
     "dit": "Contractualiser l'adaptation à l'échelle du territoire, entre "
            "collectivités, opérateurs et habitants, autour d'une vision "
            "commune.",
     "portee": "decide",
     "pour_le_centre": "C'est le cadre qui transforme le dialogue avec les "
                       "riverains — aujourd'hui un exercice d'acceptabilité "
                       "sans trace — en engagement écrit, daté et opposable "
                       "aux deux parties.",
     "enjeux": ["transparence", "bruit", "emploi_local", "conflit_usage_eau"]},

    # ── Énergie & numérique ───────────────────────────────────────────────
    {"numero": 6, "cle": "implantation_bas_carbone", "theme": "energie_numerique",
     "titre": "Conditionner l'implantation des infrastructures numériques à "
              "un approvisionnement énergétique bas carbone et à leur "
              "performance environnementale.",
     "dit": "Intégrer de manière contraignante la fourniture bas carbone dans "
            "la stratégie d'implantation des centres de données, en "
            "contrepartie de mesures facilitatrices (raccordement, "
            "autorisations) ; faciliter l'accès aux contrats de long terme "
            "(PPA) par des groupements d'achat ; créer les conditions "
            "d'offres « 24/7 », décarbonées heure par heure ; créer des "
            "certificats d'économie numérique ; étendre le mécanisme "
            "d'ajustement carbone aux frontières aux services numériques "
            "importés.",
     "portee": "decide",
     "pour_le_centre": "La proposition qui vise ce projet le plus "
                       "directement. Le « 24/7 heure par heure » n'est pas le "
                       "contrat annuel en volume qu'on signe aujourd'hui : il "
                       "change le chiffrage de la fourniture ET la façon de "
                       "déclarer le scope 2. La contrepartie annoncée — "
                       "raccordement et autorisations facilités — est "
                       "précisément ce qui décide du calendrier d'un projet.",
     "enjeux": ["carbone_electricite", "pue", "sobriete", "raccordement"]},

    {"numero": 7, "cle": "filieres_critiques", "theme": "energie_numerique",
     "titre": "Protéger les filières critiques et accélérer l'émergence de "
              "champions européens.",
     "dit": "Définir les filières critiques de la souveraineté numérique et "
            "énergétique, concentrer les financements publics sur un nombre "
            "limité d'acteurs stratégiques, instaurer un principe de "
            "préférence européenne.",
     "portee": "decide",
     "pour_le_centre": "La question atteint le projet par ses ACHATS : d'où "
                       "viennent les baies, l'onduleur, le groupe froid, "
                       "l'hyperviseur et l'outil de supervision — et quelle "
                       "dépendance chacun installe pour quinze ans.",
     "enjeux": ["chaine_humaine", "securite"]},

    {"numero": 8, "cle": "marche_donnees", "theme": "energie_numerique",
     "titre": "Construire un marché unique européen des données.",
     "dit": "Classification européenne harmonisée des données ; passeport "
            "européen de la donnée portant origine, qualité, conditions "
            "d'utilisation et restrictions juridiques ; standards ouverts, "
            "interopérabilité et portabilité ; accès effectif pour les PME et "
            "la recherche, conditionné aux financements publics.",
     "portee": "anticipe",
     "pour_le_centre": "Ce qu'un hébergeur promet en matière de réversibilité "
                       "et de portabilité cesserait d'être un argument "
                       "commercial pour devenir une condition d'accès aux "
                       "financements publics et aux marchés publics.",
     "enjeux": ["securite", "transparence"]},

    {"numero": 9, "cle": "stress_tests_croises", "theme": "energie_numerique",
     "titre": "Définir et lancer des stress tests des interdépendances entre "
              "les infrastructures numériques et énergétiques.",
     "dit": "Un cadre commun de stress tests croisés, des scénarios et des "
            "indicateurs de résilience définis avec les régulateurs ; des "
            "exercices réguliers inspirés du règlement DORA ; le partage "
            "sécurisé des enseignements et des solutions de continuité.",
     "portee": "decide",
     "pour_le_centre": "Le document le dit sans détour : la vulnérabilité "
                       "n'est pas dans le site ni dans le réseau pris "
                       "séparément, mais à leur croisement — c'est-à-dire là "
                       "où ni l'exploitant du centre ni le gestionnaire de "
                       "réseau ne teste, chacun sachant sécuriser sa propre "
                       "continuité.",
     "enjeux": ["resilience", "secours", "raccordement"]},

    {"numero": 10, "cle": "competences_ia", "theme": "energie_numerique",
     "titre": "Renforcer les compétences stratégiques face à l'IA.",
     "dit": "Identifier les compétences fondamentales dont la maîtrise "
            "humaine doit être maintenue malgré l'automatisation, pour "
            "garantir la capacité à superviser, contrôler et challenger les "
            "systèmes ; cartographier tâches et compétences dans les plans de "
            "formation ; capitaliser et transmettre les savoir-faire.",
     "portee": "decide",
     "pour_le_centre": "Un centre de données de plus en plus piloté par des "
                       "outils automatiques a besoin d'exploitants capables "
                       "de CONTREDIRE l'outil. C'est une compétence qui se "
                       "perd sans que rien ne le signale — jusqu'à la nuit où "
                       "elle manque.",
     "enjeux": ["emploi_local", "securite"]},

    # ── Santé mentale ─────────────────────────────────────────────────────
    {"numero": 11, "cle": "indicateur_sante_mentale", "theme": "sante_mentale",
     "titre": "Créer un indicateur national de suivi de la santé mentale au "
              "travail.",
     "dit": "Un indicateur national fondé sur les données agrégées de "
            "l'Assurance Maladie et des organismes de prévoyance, décliné par "
            "territoire et par filière ; un document unique d'évaluation des "
            "risques simplifié et rendu opérationnel ; un outil annuel "
            "harmonisé couplant les critères du rapport Gollac et l'indice "
            "WHO-5.",
     "portee": "anticipe",
     "pour_le_centre": "L'exploitation en trois-huit et l'astreinte figurent "
                       "parmi les organisations que ces critères mesurent — "
                       "intensité, exigences émotionnelles, insécurité de la "
                       "situation de travail. Le site serait mesuré sur ce "
                       "qu'il fait déjà.",
     "enjeux": ["chaine_humaine"]},

    {"numero": 12, "cle": "valoriser_engagees", "theme": "sante_mentale",
     "titre": "Valoriser et soutenir les entreprises engagées.",
     "dit": "Un label de reconnaissance ; une modulation bonus-malus des "
            "cotisations accidents du travail et maladies professionnelles "
            "sur la base de moyennes sectorielles ; un crédit d'impôt « santé "
            "mentale ».",
     "portee": "anticipe",
     "pour_le_centre": "Le sujet passerait du registre de l'engagement "
                       "volontaire à celui du coût du travail — donc d'un "
                       "chapitre de rapport annuel à une ligne de budget "
                       "d'exploitation.",
     "enjeux": ["chaine_humaine"]},

    {"numero": 13, "cle": "financement_solidaire", "theme": "sante_mentale",
     "titre": "Mobiliser des mécanismes de financement solidaires, notamment "
              "au bénéfice des TPE-PME.",
     "dit": "Généraliser le degré élevé de solidarité par les assureurs à "
            "l'ensemble des branches ; instaurer une péréquation "
            "inter-entreprises de sorte que les grandes structures outillent "
            "les TPE-PME de leur propre branche.",
     "portee": "contribue",
     "pour_le_centre": "Le mécanisme se décide en branche, pas sur le "
                       "projet. Mais un chantier de centre de données fait "
                       "travailler des entreprises qui n'ont aucun de ces "
                       "moyens : la question se pose au donneur d'ordre, même "
                       "s'il ne tient pas le levier.",
     "enjeux": ["chaine_humaine"]},

    {"numero": 14, "cle": "competence_sante_mentale", "theme": "sante_mentale",
     "titre": "Faire de la santé mentale une compétence clé à tous les "
              "niveaux.",
     "dit": "Un référentiel de compétences socles pour tous et un référentiel "
            "spécifique au management, exigé à la prise de fonction ; un "
            "système de mentorat ou de binôme entre pairs pour rompre "
            "l'isolement du manager, souvent seul face aux exigences de "
            "performance et aux situations humaines complexes.",
     "portee": "decide",
     "pour_le_centre": "L'exploitation d'un site critique met des "
                       "responsables seuls, la nuit, face à des décisions de "
                       "continuité qui engagent le client et le territoire. "
                       "L'isolement du manager que décrit la proposition y a "
                       "une forme très concrète.",
     "enjeux": ["chaine_humaine", "securite"]},

    {"numero": 15, "cle": "situations_exterieures", "theme": "sante_mentale",
     "titre": "Développer des politiques d'accompagnement qui prennent en "
              "compte les situations extérieures à l'environnement "
              "professionnel.",
     "dit": "Des dispositifs pour l'aidance, la parentalité, le deuil, les "
            "violences conjugales ; un cadre permettant d'adapter "
            "temporairement l'organisation du travail ; le recensement et "
            "l'accessibilité des droits et ressources existants.",
     "portee": "decide",
     "pour_le_centre": "Sur un site en astreinte, la souplesse temporaire "
                       "d'organisation est précisément ce qu'il est le plus "
                       "difficile d'accorder. Elle se décide donc au "
                       "DIMENSIONNEMENT DES ÉQUIPES, des années avant le cas "
                       "particulier qui la demandera.",
     "enjeux": ["chaine_humaine"]},

    # ── Infrastructures critiques ─────────────────────────────────────────
    {"numero": 16, "cle": "plateforme_interdependances", "theme": "infrastructures",
     "titre": "Développer et promouvoir une plateforme permettant de mieux "
              "appréhender les interdépendances des infrastructures.",
     "dit": "Cartographier les interdépendances et les effets de cascade "
            "affectant les services essentiels, en mobilisant les outils "
            "existants, pour alimenter une modélisation en graphes ; un "
            "référentiel commun de vocabulaire ; une gouvernance du partage "
            "sécurisé des données.",
     "portee": "contribue",
     "pour_le_centre": "Le site dépend de l'électricité, de l'eau, des "
                       "télécommunications et des routes ; et plusieurs "
                       "services essentiels dépendent de lui. Aujourd'hui, la "
                       "carte n'existe dans aucun des deux sens — le projet "
                       "peut fournir sa moitié.",
     "enjeux": ["resilience", "secours"]},

    {"numero": 17, "cle": "exercices_territoriaux", "theme": "infrastructures",
     "titre": "Renforcer et étendre les exercices territoriaux multicrises et "
              "inter-opérateurs à fréquence régulière.",
     "dit": "Des exercices régionaux multirisques réguliers fondés sur la "
            "cartographie propre à chaque territoire ; la cohérence avec les "
            "plans communaux et intercommunaux de sauvegarde ; une "
            "bibliothèque nationale de scénarios inspirés de crises réelles ; "
            "l'association de la population.",
     "portee": "decide",
     "pour_le_centre": "L'exercice interne annuel ne dit rien de ce qui se "
                       "passe quand la panne est TERRITORIALE et que le "
                       "gestionnaire de réseau, la collectivité et le site "
                       "décident en même temps, chacun avec sa procédure.",
     "enjeux": ["resilience", "secours", "transparence"]},

    {"numero": 18, "cle": "fonction_resilience", "theme": "infrastructures",
     "titre": "Ancrer la composante résilience dans la gestion des risques "
              "des organisations.",
     "dit": "Généraliser la fonction de directeur de la résilience au sein "
            "des entités critiques et l'intégrer à la gouvernance "
            "stratégique ; lui confier la cartographie des interdépendances "
            "de l'organisation avec son écosystème, puis la coordination des "
            "actions associées.",
     "portee": "decide",
     "pour_le_centre": "La résilience cesserait d'être une annexe du plan de "
                       "continuité pour devenir une fonction NOMMÉE, avec un "
                       "titulaire, un rattachement et un budget. C'est la "
                       "différence entre un document et une responsabilité.",
     "enjeux": ["resilience", "transparence"]},

    {"numero": 19, "cle": "financement_resilience", "theme": "infrastructures",
     "titre": "Développer et mobiliser des mécanismes de financement pour "
              "mettre en œuvre la résilience.",
     "dit": "Construire une taxonomie de la résilience à l'image des critères "
            "ESG pour prioriser les financements ; imposer aux gestionnaires "
            "d'infrastructures critiques d'allouer une part de leurs fonds "
            "propres au renforcement de leur résilience ; doter des fonds "
            "dédiés à la prévention.",
     "portee": "anticipe",
     "pour_le_centre": "La dépense de résilience, aujourd'hui arbitrée en "
                       "dernier parce qu'elle ne produit rien de visible, "
                       "deviendrait une allocation à justifier devant le "
                       "financeur. C'est un renversement de la charge de la "
                       "preuve.",
     "enjeux": ["resilience", "secours"]},

    {"numero": 20, "cle": "professionnalisation_resilience", "theme": "infrastructures",
     "titre": "Accompagner la professionnalisation des acteurs de la "
              "résilience des infrastructures critiques.",
     "dit": "La directive européenne sur la résilience des entités critiques "
            "renforce les exigences applicables ; il s'agit d'un guide "
            "opérationnel harmonisé traduisant ces exigences en actions "
            "concrètes, auditables et comparables, de l'implication des "
            "acteurs de l'audit et de la certification, et d'un label "
            "professionnel d'experts en résilience.",
     "portee": "anticipe",
     "pour_le_centre": "C'est le texte qui rend la résilience AUDITABLE, donc "
                       "opposable. Un centre de données qui relève des "
                       "entités critiques sera examiné sur pièces, pas sur "
                       "déclaration.",
     "enjeux": ["resilience", "securite"]},

    # ── Eau ───────────────────────────────────────────────────────────────
    {"numero": 21, "cle": "ecosystemes_infrastructure", "theme": "eau",
     "titre": "Reconnaître les écosystèmes comme infrastructures de gestion "
              "de l'eau.",
     "dit": "Inscrire les fonctions de régulation hydrique des sols et des "
            "écosystèmes dans les documents de planification ; cartographier "
            "les écosystèmes dont dépendent les chaînes d'approvisionnement ; "
            "élargir les plans de transition bas carbone à des plans "
            "« transition nature » intégrant les dépendances aux milieux.",
     "portee": "decide",
     "pour_le_centre": "Le plan « transition nature » élargit l'exercice "
                       "carbone à la dépendance aux milieux. C'est un livrable "
                       "de plus, pas un chapitre du premier : les dépendances "
                       "ne se déduisent pas d'un bilan d'émissions.",
     "enjeux": ["conflit_usage_eau", "foncier"]},

    {"numero": 22, "cle": "contexte_hydrologique", "theme": "eau",
     "titre": "Évaluer les projets industriels au regard de leur contexte "
              "hydrologique territorial.",
     "dit": "Une empreinte hydrique évaluée localement, à l'échelle du bassin "
            "versant et sur tout le cycle de vie du projet — y compris lors "
            "de la cessation d'activité ; un stress test hydrique fondé sur "
            "les projections climatiques de référence ; la participation aux "
            "instances de gouvernance de l'eau conditionnée à cette analyse.",
     "portee": "decide",
     "pour_le_centre": "C'est l'arbitrage que ce document pose déjà entre "
                       "l'eau du site et l'eau prélevée en amont. La "
                       "proposition y ajoute deux choses qui manquent presque "
                       "toujours : la DATE DE FIN — le cycle de vie va "
                       "jusqu'à la cessation — et une trajectoire climatique "
                       "de référence, au lieu de l'hydrologie d'hier.",
     "enjeux": ["eau_site", "eau_amont", "conflit_usage_eau"]},

    {"numero": 23, "cle": "planifier_prelevements", "theme": "eau",
     "titre": "Planifier les prélèvements et renforcer la gestion collective "
              "à l'échelle des bassins versants.",
     "dit": "Fixer des objectifs quantifiés de prélèvement PAR FILIÈRE, à "
            "l'échelle des bassins et sous-bassins, pour éclairer les schémas "
            "d'aménagement et de gestion des eaux ; développer des projets "
            "d'intérêt commun entre usagers.",
     "portee": "anticipe",
     "pour_le_centre": "Un objectif par filière signifie qu'un volume sera un "
                       "jour attribué au numérique dans un bassin donné — "
                       "indépendamment de ce projet-ci, et sans doute avant "
                       "qu'il ne soit mis en service.",
     "enjeux": ["eau_site", "conflit_usage_eau"]},

    {"numero": 24, "cle": "tarification_eau", "theme": "eau",
     "titre": "Adapter la tarification de l'eau à la disponibilité de la "
              "ressource.",
     "dit": "Une tarification incitative associant un prix plancher reflétant "
            "le coût réel du service à une part variable modulée selon la "
            "pression sur la ressource, avec plafonnement ; des recettes "
            "affectées à la préservation des écosystèmes du bassin.",
     "portee": "anticipe",
     "pour_le_centre": "Le coût de l'eau, aujourd'hui négligeable dans le "
                       "compte d'exploitation, deviendrait une variable liée "
                       "au bassin ET à la saison. Un refroidissement "
                       "évaporatif ne se chiffre alors plus au tarif "
                       "d'aujourd'hui — et c'est la pointe d'août qui coûte.",
     "enjeux": ["eau_site", "conflit_usage_eau"]},

    {"numero": 25, "cle": "competences_eau", "theme": "eau",
     "titre": "Structurer les compétences et la recherche au service de "
              "l'innovation.",
     "dit": "Formation continue des élus et des collaborateurs ; parcours "
            "incluant des visites de terrain pour les métiers exposés aux "
            "risques hydriques ; chaires partenariales et centres de "
            "recherche mutualisés, notamment sur les polluants émergents qui "
            "freinent la réutilisation de l'eau.",
     "portee": "contribue",
     "pour_le_centre": "La réutilisation d'eau sur site bute sur le "
                       "traitement, pas sur la volonté. La proposition nomme "
                       "l'obstacle réel — les micropolluants — là où les "
                       "engagements de réutilisation restent en général muets "
                       "sur la raison pour laquelle ils ne sont pas tenus.",
     "enjeux": ["eau_site"]},

    # ── Parcours scientifiques ────────────────────────────────────────────
    {"numero": 26, "cle": "experimentation_ecole", "theme": "sciences",
     "titre": "Faire de l'expérimentation le socle de l'enseignement "
              "scientifique dès l'école primaire.",
     "dit": "Un temps régulier d'expérimentation de la maternelle au CM2 sous "
            "le signe du droit à l'erreur ; des fêtes de la science dans les "
            "établissements ; la mobilisation des acteurs de la recherche "
            "dans les projets scolaires.",
     "portee": "contribue",
     "pour_le_centre": "Hors du périmètre d'un projet. Elle l'atteint par le "
                       "vivier dans lequel l'exploitant recrutera dans dix "
                       "ans — l'économie française devant former, selon le "
                       "document, près de cent mille ingénieurs et "
                       "techniciens nets par an d'ici 2035.",
     "enjeux": ["emploi_local"]},

    {"numero": 27, "cle": "ambassadrices", "theme": "sciences",
     "titre": "Créer un réseau national de femmes scientifiques "
              "ambassadrices.",
     "dit": "Un réseau associant universités, organismes de recherche et "
            "entreprises pour identifier, former et accompagner des "
            "intervenantes ; des interventions de modèles féminins en "
            "établissement scolaire, dont la proximité d'âge facilite "
            "l'identification.",
     "portee": "contribue",
     "pour_le_centre": "Les métiers d'exploitation d'un centre de données "
                       "comptent parmi les moins mixtes de la filière. "
                       "L'entreprise peut fournir des intervenantes ; elle ne "
                       "décide pas du réseau.",
     "enjeux": ["emploi_local"]},

    {"numero": 28, "cle": "recherche_entreprise", "theme": "sciences",
     "titre": "Faire de la coopération entre recherche et entreprise un "
              "moteur d'innovation.",
     "dit": "Simplifier et renforcer les conventions industrielles de "
            "formation par la recherche ; instaurer un guichet unique entre "
            "organismes de recherche et entreprises ; codévelopper des "
            "laboratoires communs.",
     "portee": "decide",
     "pour_le_centre": "Une thèse en convention industrielle est le moyen le "
                       "plus accessible de faire traiter par la recherche une "
                       "question que le projet ne sait pas trancher : "
                       "récupération de chaleur à basse température, "
                       "refroidissement sans eau, prolongation de la durée de "
                       "vie des serveurs.",
     "enjeux": ["chaleur_fatale", "fin_de_vie", "emploi_local"]},

    {"numero": 29, "cle": "culture_scientifique", "theme": "sciences",
     "titre": "Structurer une stratégie nationale de culture scientifique.",
     "dit": "Une certification nationale de culture scientifique ouverte à "
            "tous, structurée par niveaux de maîtrise ; des parcours de "
            "formation accessibles, en modules numériques et ressources "
            "libres.",
     "portee": "contribue",
     "pour_le_centre": "Hors périmètre du projet. À retenir pour la formation "
                       "continue des équipes d'exploitation, où l'esprit "
                       "critique face à un outil automatique est une "
                       "compétence de sûreté (voir la proposition 10).",
     "enjeux": ["emploi_local"]},

    {"numero": 30, "cle": "information_scientifique", "theme": "sciences",
     "titre": "Garantir l'accès à une information scientifique de qualité.",
     "dit": "Une plateforme nationale de réponses scientifiques sourcées ; un "
            "label indépendant pour les médias et créateurs de contenus "
            "scientifiques ; un dispositif public de réponse rapide aux "
            "fausses informations en ligne.",
     "portee": "contribue",
     "pour_le_centre": "Un projet de centre de données affronte, en "
                       "concertation, des affirmations chiffrées fausses DANS "
                       "LES DEUX SENS — celles qui l'accablent comme celles "
                       "qui le flattent. La qualité de l'information publique "
                       "décide du terrain sur lequel le débat se tient.",
     "enjeux": ["transparence", "bruit"]},
]

_THEME = {t["cle"]: t for t in THEMES}
_PAR_CLE = {p["cle"]: p for p in PROPOSITIONS}


# ═══════════════════════════════════════════════════════════════════════════
#  CONTRÔLES AU CHARGEMENT — un référentiel incohérent doit refuser de se
#  charger, pas rendre un livrable faux.
# ═══════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════
#  LES MESURES — CE QUE CHAQUE PROPOSITION DEMANDE VRAIMENT
#
#  LE DÉFAUT QUE CE BLOC CORRIGE, ET SA CONSÉQUENCE MESURÉE. Chaque
#  proposition du document porte trois à cinq MESURES. Le champ `dit` les
#  compressait en une phrase, et une portée unique les couvrait toutes. Or à
#  l'intérieur d'une même proposition les mesures ne se ressemblent pas :
#  « instaurer une tarification incitative » est un acte de puissance publique,
#  « intégrer un stress test hydrique à l'évaluation du projet » est un geste
#  que le maître d'ouvrage pose seul, aujourd'hui.
#
#  CE QUE LA COMPRESSION COÛTAIT, VÉRIFIÉ SUR LE CODE. La proposition 25
#  — « Structurer les compétences et la recherche au service de l'innovation »
#  — est lue CONTRIBUE, ce qui est juste pour l'ensemble : un centre de données
#  ne structure pas la recherche nationale. Mais deux de ses quatre mesures
#  sont la formation des collaborateurs et des métiers exposés aux risques
#  hydriques — c'est-à-dire, pour un exploitant, ses propres équipes. Et comme
#  `hors_couverture()` ne regarde que les propositions DÉCIDE ou ANTICIPE, ces
#  deux mesures-là ne pouvaient apparaître dans AUCUN livrable, quel que soit
#  le projet. La moitié utile de la confrontation en laissait tomber une part,
#  sans que rien ne le signale.
#
#  LA PORTÉE D'UNE MESURE RÉPOND À LA MÊME QUESTION QUE CELLE D'UNE
#  PROPOSITION : que peut ce projet-ci en faire, seul, dans son périmètre ?
#  Elle est donc comparable, et `_verifier()` exige que la portée annoncée par
#  la proposition figure parmi celles de ses mesures — une proposition lue
#  DÉCIDE dont aucune mesure ne se décide serait une promesse sans objet.
#
#  CE QUI N'EST RELEVÉ QUE POUR TROIS THÈMES. Les mesures ne sont saisies que
#  pour « eau », « énergie & numérique » et « infrastructures critiques » —
#  ceux versés au dossier. Les quinze autres propositions gardent leur résumé,
#  et `couverture_mesures()` le dit : quinze propositions sans mesures
#  détaillées ne sont pas quinze propositions sans mesures.
#
#  LE TEXTE DES MESURES EST CELUI DU DOCUMENT, à la ponctuation près. La
#  portée, elle, est la lecture de CONSEILPREV — comme `pour_le_centre`. Les
#  confondre ferait dire à l'auteur ce qu'il n'a pas écrit.
# ═══════════════════════════════════════════════════════════════════════════

#: Le rang d'une portée, pour comparer une mesure à sa proposition. DÉCIDE est
#: le rang le plus haut : c'est la portée qui engage le plus le projet.
RANG_PORTEE = {"contribue": 0, "anticipe": 1, "decide": 2}

MESURES = {
    # ── ÉNERGIE & NUMÉRIQUE ────────────────────────────────────────────────
    "implantation_bas_carbone": {
        "chapeau":
            "Le train de mesures sur la souveraineté technologique européenne "
            "porté par la Commission européenne constitue une avancée "
            "importante en faveur d'une planification plus cohérente des "
            "infrastructures numériques et énergétiques. Il convient de le "
            "compléter par des critères opérationnels qui orientent le "
            "développement de ces infrastructures vers les usages les plus "
            "sobres et essentiels, tout en assurant au préalable le "
            "développement de capacités suffisantes de production d'énergie, "
            "notamment à l'échelle européenne.",
        "mesures": [
            {"texte": "Intégrer de manière contraignante la fourniture "
                      "d'électrons et de molécules bas carbone dans la "
                      "stratégie d'implantation des infrastructures numériques "
                      "(data centers), en contrepartie de la mise en place de "
                      "mesures facilitatrices pour leur installation "
                      "(raccordement, autorisations, etc.).",
             "portee": "decide",
             "termes": []},
            {"texte": "Faciliter l'accès aux contrats long terme (PPA/BPA) "
                      "pour tous les acteurs via des groupements d'achats et "
                      "des mécanismes de garantie, afin de mutualiser et "
                      "d'améliorer la compétitivité des offres.",
             "portee": "decide",
             "termes": ["ppa_bpa"]},
            {"texte": "Créer les conditions pour des offres « 24/7 » "
                      "(fourniture en ruban décarbonée heure par heure), "
                      "garantissant que chaque électron ou molécule consommé "
                      "par l'infrastructure est structurellement bas carbone, "
                      "en veillant à ce que le GHG Protocol prenne les bonnes "
                      "dispositions pour cela.",
             "portee": "contribue",
             "termes": ["ghg_protocol"]},
            {"texte": "Créer des certificats d'économie numérique, inspirés "
                      "des certificats d'économie d'énergie, permettant de "
                      "valoriser les réductions mesurables de consommation "
                      "énergétique et d'empreinte carbone des services "
                      "numériques, et d'intégrer le signal-prix carbone au "
                      "développement de l'économie numérique.",
             "portee": "anticipe",
             "termes": []},
            {"texte": "Étendre le MACF aux infrastructures et services "
                      "numériques importés lorsque leur empreinte carbone "
                      "n'est pas soumise à des exigences équivalentes à celles "
                      "applicables dans l'Union européenne.",
             "portee": "anticipe",
             "termes": ["macf"]},
        ],
    },
    "filieres_critiques": {
        "chapeau":
            "Face à l'intensification de la concurrence technologique "
            "mondiale, l'Europe doit se doter d'une stratégie offensive de "
            "souveraineté numérique. L'objectif n'est pas de reproduire les "
            "modèles dominants existants, mais de bâtir des avantages "
            "compétitifs européens fondés sur la confiance, la maîtrise "
            "technologique et la réponse aux besoins structurants du "
            "continent.",
        "mesures": [
            {"texte": "Définir précisément, aux échelles nationale et "
                      "européenne, les filières critiques de notre "
                      "souveraineté numérique et énergétique.",
             "portee": "anticipe", "termes": []},
            {"texte": "Concentrer les financements publics nationaux et "
                      "européens sur un nombre limité d'acteurs et de projets "
                      "stratégiques, sur le modèle des PIIEC, afin de faire "
                      "émerger des champions européens capables d'atteindre "
                      "une taille compétitive, plutôt que de disperser les "
                      "soutiens sur une multitude d'initiatives.",
             "portee": "contribue", "termes": ["piiec"]},
            {"texte": "Instaurer un principe de « préférence européenne » dans "
                      "le choix des solutions numériques, en exigeant qu'un "
                      "recours à une solution extra-européenne fasse l'objet "
                      "d'une justification formelle lorsqu'une alternative "
                      "européenne répond aux besoins exprimés.",
             "portee": "decide", "termes": []},
            {"texte": "Conditionner les procédures accélérées de raccordement "
                      "des data centers à des critères de souveraineté "
                      "industrielle européenne, en privilégiant les projets "
                      "reposant sur des technologies, équipements et services "
                      "développés au sein de l'Union européenne.",
             "portee": "anticipe", "termes": []},
        ],
    },
    "marche_donnees": {
        "chapeau":
            "Les données sont devenues une ressource stratégique pour "
            "l'innovation, la compétitivité et le développement de "
            "l'intelligence artificielle. Pour valoriser pleinement ce "
            "potentiel, l'Europe doit dépasser la fragmentation actuelle en "
            "créant un marché unique des données fondé sur des règles "
            "harmonisées, des standards communs, des infrastructures de "
            "confiance et un accès élargi aux jeux de données stratégiques.",
        "mesures": [
            {"texte": "Établir une classification européenne harmonisée en "
                      "distinguant notamment les données ouvertes, "
                      "personnelles, confidentielles, industrielles, "
                      "sensibles, critiques et stratégiques, afin d'adapter "
                      "leurs conditions de circulation, de stockage, de "
                      "traitement et d'accès.",
             "portee": "anticipe", "termes": []},
            {"texte": "Créer un passeport européen de la donnée avec, pour "
                      "chaque jeu de données : origine, niveau de qualité, "
                      "conditions d'utilisation, restrictions juridiques, "
                      "historique de transformation, traitements auxquels il "
                      "peut être soumis.",
             "portee": "anticipe", "termes": []},
            {"texte": "Accélérer l'interconnexion des écosystèmes sectoriels, "
                      "le déploiement de standards ouverts et le développement "
                      "d'intermédiaires de confiance garantissant "
                      "l'interopérabilité et la portabilité des données.",
             "portee": "contribue", "termes": []},
            {"texte": "Adosser le développement du marché européen des données "
                      "au PIIEC IA en orientant une partie des financements "
                      "vers la collecte, la qualification, l'anonymisation et "
                      "la mutualisation de jeux de données européens destinés "
                      "à l'entraînement et à l'évaluation des modèles "
                      "d'intelligence artificielle.",
             "portee": "contribue", "termes": ["piiec_ia"]},
            {"texte": "Garantir un accès effectif aux données pour les PME, "
                      "start-ups, laboratoires de recherche et acteurs "
                      "publics, en conditionnant les financements publics, les "
                      "aides à l'innovation et les marchés publics à des "
                      "engagements d'interopérabilité, de portabilité et de "
                      "réutilisation des données produites grâce à des fonds "
                      "publics.",
             "portee": "anticipe", "termes": []},
        ],
    },
    "stress_tests_croises": {
        "chapeau":
            "La résilience des infrastructures, définie comme la capacité à "
            "maintenir la continuité des fonctions critiques malgré des "
            "perturbations, constitue un enjeu majeur de souveraineté qui "
            "nécessite de mieux identifier les vulnérabilités systémiques. Ces "
            "stress tests croisés permettront de préserver la continuité des "
            "services et activités essentiels.",
        "mesures": [
            {"texte": "Définir un cadre commun de stress tests des "
                      "interdépendances entre infrastructures numériques et "
                      "énergétiques, de scénarios à évaluer et d'indicateurs "
                      "de résilience pertinents, à travers un groupe de "
                      "travail associant les acteurs de l'énergie, du "
                      "numérique, des infrastructures critiques et les "
                      "régulateurs concernés.",
             "portee": "contribue", "termes": []},
            {"texte": "Réaliser régulièrement ces stress tests, en s'inspirant "
                      "des cadres de résilience existants tels que DORA, afin "
                      "d'identifier les vulnérabilités systémiques et de "
                      "renforcer la continuité des services essentiels.",
             "portee": "decide", "termes": ["dora"]},
            {"texte": "Partager, dans un cadre sécurisé et adapté aux enjeux "
                      "de confidentialité, les enseignements de ces exercices "
                      "ainsi que les solutions de continuité d'activité et "
                      "d'atténuation identifiées, accélérant ainsi la "
                      "diffusion des bonnes pratiques et le renforcement de la "
                      "résilience collective.",
             "portee": "contribue", "termes": []},
        ],
    },
    "competences_ia": {
        "chapeau":
            "L'intelligence artificielle transforme profondément les métiers "
            "et les compétences. Pour qu'elle reste un outil au service de "
            "l'humain plutôt qu'une finalité, il est essentiel de renforcer "
            "les savoirs fondamentaux et les savoir-faire professionnels qui "
            "permettent d'en comprendre le fonctionnement, d'en maîtriser les "
            "usages et d'en challenger les résultats.",
        "mesures": [
            {"texte": "Identifier, dans les secteurs stratégiques, les "
                      "compétences fondamentales dont la maîtrise humaine doit "
                      "être maintenue malgré l'automatisation croissante des "
                      "tâches, afin de garantir la capacité à superviser, "
                      "contrôler et challenger les systèmes d'IA.",
             "portee": "decide", "termes": []},
            {"texte": "Intégrer le mapping des tâches et des compétences dans "
                      "la révision des plans de formation (démarches "
                      "GEPP/GPEC) pour identifier précisément les compétences "
                      "amenées à évoluer, les savoir-faire à préserver et les "
                      "nouveaux besoins de formation.",
             "portee": "decide", "termes": ["gepp_gpec"]},
            {"texte": "Développer, au sein des entreprises et des filières "
                      "stratégiques, des dispositifs de capitalisation et de "
                      "transmission des savoir-faire afin de préserver les "
                      "expertises métiers.",
             "portee": "decide", "termes": []},
            {"texte": "Intégrer dans les cursus de formation initiale et "
                      "continue l'apprentissage du fonctionnement de l'IA, de "
                      "ses biais, de ses limites et des méthodes permettant "
                      "d'exercer un regard critique sur ses résultats.",
             "portee": "contribue", "termes": []},
        ],
    },

    # ── INFRASTRUCTURES CRITIQUES ──────────────────────────────────────────
    # UNE DIFFICULTÉ PROPRE À CE THÈME, ET LE GARDE-FOU L'A POSÉE. La
    # proposition 20 est lue ANTICIPE, et sa justification tient au chapeau :
    # la directive européenne sur la résilience des entités critiques
    # s'appliquera au projet. Or un chapeau n'est pas une mesure, et les quatre
    # mesures relèvent d'un collectif — un guide, des instances, un label.
    # `_verifier()` a donc demandé LAQUELLE porte l'anticipation. C'est la
    # première : un guide harmonisé traduisant les exigences en actions
    # AUDITABLES et comparables est, une fois écrit, le référentiel sur lequel
    # le projet sera examiné. La question n'aurait pas été posée sans le
    # contrôle ; c'est exactement ce pour quoi il existe.
    "plateforme_interdependances": {
        "chapeau":
            "Si des outils d'analyse et de cartographie existent déjà, ils "
            "restent souvent méconnus et principalement centrés sur les "
            "risques territoriaux plutôt que sur les interdépendances. Les "
            "travaux menés, notamment par la Banque mondiale, soulignent "
            "l'importance de mieux comprendre les relations entre "
            "infrastructures et les conséquences de leur défaillance. "
            "L'élaboration d'une plateforme dédiée doit permettre de traduire "
            "ces connaissances en un outil opérationnel d'aide à la décision "
            "et de renforcer notre robustesse à l'échelle territoriale comme "
            "systémique.",
        "mesures": [
            {"texte": "Cartographier les interdépendances entre "
                      "infrastructures ainsi que les effets de cascade "
                      "susceptibles d'affecter les services essentiels, en "
                      "mobilisant les données, outils de cartographie et "
                      "démarches de diagnostic existants (tels que Géorisques "
                      "et TACCT), afin d'alimenter une modélisation en graphes "
                      "permettant de visualiser les liaisons et de fournir une "
                      "aide à la décision.",
             # La finalité — « afin d'alimenter une modélisation en graphes » —
             # rattache l'acte à un modèle partagé que le projet ne construit
             # pas. Il peut relever ses propres dépendances et les verser :
             # c'est une participation, pas une décision de projet.
             "portee": "contribue", "termes": ["tacct"]},
            {"texte": "Prendre en compte les risques émergents, en s'appuyant "
                      "notamment sur les travaux scientifiques tels que ceux "
                      "du laboratoire de la Caisse centrale de réassurance "
                      "(CCR).",
             # LA SEULE DES QUATRE SANS OBJET PARTAGÉ. Intégrer les risques
             # émergents à sa propre analyse, à partir de travaux publiés, ne
             # demande ni plateforme ni accord : cela se fait aujourd'hui.
             "portee": "decide", "termes": []},
            {"texte": "Définir un cadre de gouvernance assurant l'évolution "
                      "continue de la plateforme et le partage sécurisé des "
                      "données, avec des modalités d'accès adaptées à leur "
                      "degré de sensibilité.",
             "portee": "contribue", "termes": []},
            {"texte": "Élaborer un référentiel commun définissant un "
                      "vocabulaire et une méthodologie partagés pour "
                      "caractériser et analyser les interdépendances selon des "
                      "critères communs à l'ensemble des acteurs concernés.",
             "portee": "contribue", "termes": []},
        ],
    },
    "exercices_territoriaux": {
        "chapeau":
            "La préparation aux crises systémiques repose sur la capacité des "
            "acteurs d'un territoire à tester ensemble leur réaction face à "
            "des risques de différentes natures susceptibles de se combiner. "
            "La réalisation régulière d'exercices multirisques et "
            "multipartites doit permettre de mieux préparer la réponse "
            "collective et de renforcer la culture du risque.",
        "mesures": [
            {"texte": "Imposer à l'échelle régionale des exercices réguliers "
                      "multirisques, fondés sur la cartographie des risques "
                      "propre à chaque territoire et associant l'ensemble des "
                      "parties prenantes concernées.",
             "portee": "anticipe", "termes": []},
            {"texte": "Renforcer la coordination entre les différents échelons "
                      "territoriaux lors des exercices, en assurant la "
                      "cohérence entre les dispositifs communaux et "
                      "départementaux et les PICS.",
             "portee": "contribue", "termes": ["pics"]},
            {"texte": "Capitaliser sur les initiatives existantes — Journée "
                      "nationale de la résilience, exercices ministériels ou "
                      "exercices cyber de l'ANSSI — afin de structurer et de "
                      "mettre en cohérence les démarches menées sur le "
                      "territoire.",
             # Ces rendez-vous existent et sont ouverts : y inscrire son site
             # ne demande l'accord de personne. C'est la mesure que le projet
             # peut poser dès cette année, et elle porte la portée de la
             # proposition.
             "portee": "decide", "termes": []},
            {"texte": "Mettre à disposition des collectivités et des "
                      "opérateurs une bibliothèque nationale de scénarios "
                      "d'exercices, inspirée de crises réelles et enrichie par "
                      "les retours d'expérience.",
             "portee": "contribue", "termes": []},
            {"texte": "Associer la population aux exercices territoriaux et "
                      "développer des outils pédagogiques de simulation, à "
                      "l'instar du programme Stop Disasters Game développé par "
                      "l'UNDRR, afin de renforcer la préparation des citoyens "
                      "aux situations de crise.",
             "portee": "contribue", "termes": ["undrr"]},
        ],
    },
    "fonction_resilience": {
        "chapeau":
            "Face à la multiplication des risques systémiques, la résilience "
            "ne doit pas se limiter à la gestion de crise. Portée au plus haut "
            "niveau des organisations et fondée sur la coopération "
            "public-privé, elle doit constituer une fonction reconnue, "
            "structurée et présente chez l'ensemble des acteurs du système.",
        "mesures": [
            {"texte": "Généraliser la fonction de Chief Resilience Officer "
                      "(CRO) au sein des entités critiques et l'intégrer à la "
                      "gouvernance stratégique, en définissant clairement les "
                      "responsabilités de chacun, les processus associés et "
                      "les instances de pilotage.",
             "portee": "decide", "termes": []},
            {"texte": "Confier à cette fonction la mission de cartographier "
                      "les interdépendances de son organisation avec son "
                      "écosystème, puis de coordonner les actions de "
                      "résilience associées.",
             "portee": "decide", "termes": []},
            {"texte": "Structurer des communautés permettant à ces "
                      "ambassadeurs de la résilience de se rencontrer "
                      "régulièrement pour partager leurs retours d'expérience "
                      "et coordonner des actions de résilience à l'échelle du "
                      "système.",
             "portee": "contribue", "termes": []},
        ],
    },
    "financement_resilience": {
        "chapeau":
            "Face à l'intensification des risques climatiques, cyber, "
            "sanitaires, géopolitiques et sociétaux, les investissements de "
            "résilience restent insuffisants alors qu'ils conditionnent la "
            "continuité des services essentiels. Il est nécessaire de "
            "mobiliser des mécanismes financiers dédiés pour soutenir la "
            "prévention, l'adaptation et le renforcement des infrastructures "
            "critiques.",
        "mesures": [
            {"texte": "Construire une taxonomie de la résilience à l'image des "
                      "critères ESG pour prioriser les financements.",
             "portee": "anticipe", "termes": []},
            {"texte": "Imposer aux entreprises amenées à gérer des "
                      "infrastructures critiques d'allouer une part de leurs "
                      "fonds propres au renforcement de leur résilience, en "
                      "s'inspirant de la logique de Bâle III.",
             "portee": "anticipe", "termes": ["bale_iii"]},
            {"texte": "Doter financièrement des fonds dédiés à la prévention "
                      "et à la résilience des infrastructures critiques, en "
                      "s'inspirant du Fonds Barnier ainsi que de dispositifs "
                      "internationaux tels que le programme BRIC aux "
                      "États-Unis ou le Plan national pour la reprise et la "
                      "résilience du Luxembourg.",
             "portee": "contribue", "termes": ["bric"]},
        ],
    },
    "professionnalisation_resilience": {
        "chapeau":
            "La directive européenne sur la Résilience des entités critiques "
            "(REC) renforce les exigences applicables aux infrastructures "
            "critiques. Au-delà de la conformité, elle constitue une "
            "opportunité de transformation pour les organisations, à condition "
            "de s'appuyer sur l'expertise des instances professionnelles, de "
            "transposer les référentiels en accord avec la réalité du terrain "
            "et de développer les compétences sur l'ensemble de la chaîne de "
            "valeur.",
        "mesures": [
            {"texte": "Développer et mettre à jour un guide opérationnel "
                      "harmonisé, intégrant les principaux référentiels "
                      "nationaux et internationaux, permettant de traduire les "
                      "exigences réglementaires en actions concrètes, "
                      "auditables et comparables, à l'image du Vade-mecum des "
                      "démarches de reconnaissance de la résilience.",
             # « AUDITABLES ET COMPARABLES » : une fois ce guide écrit, c'est
             # sur lui que le projet sera examiné. C'est la seule des quatre
             # mesures qui s'impose à lui — et donc celle qui porte
             # l'anticipation que la proposition annonce.
             "portee": "anticipe", "termes": ["vade_mecum"]},
            {"texte": "Impliquer les acteurs de référence de l'audit et de la "
                      "certification pour accompagner la transposition "
                      "opérationnelle des directives européennes au niveau "
                      "national et sectoriel.",
             "portee": "contribue", "termes": []},
            {"texte": "Développer une action collective autour des instances "
                      "professionnelles pivots, afin d'harmoniser les "
                      "pratiques et d'impacter l'ensemble des acteurs des "
                      "systèmes critiques, y compris leur chaîne de valeur.",
             "portee": "contribue", "termes": []},
            {"texte": "Créer un label professionnel d'experts en résilience "
                      "pour valoriser les compétences des auditeurs face aux "
                      "risques majeurs, garantissant la qualité de l'exécution "
                      "tout en mutualisant les coûts de formation.",
             "portee": "contribue", "termes": []},
        ],
    },

    # ── EAU ────────────────────────────────────────────────────────────────
    "ecosystemes_infrastructure": {
        "chapeau":
            "L'eau ne peut être dissociée des moteurs naturels que sont les "
            "sols, les forêts, les zones humides et, plus largement, les "
            "écosystèmes, qui assurent les fonctions essentielles de stockage, "
            "de filtration et de régulation. Préserver ces milieux, c'est "
            "sécuriser les ressources dont dépendent directement les activités "
            "économiques. Leur restauration doit donc être pleinement intégrée "
            "aux politiques publiques et aux stratégies industrielles.",
        "mesures": [
            {"texte": "Faire de la gestion équilibrée et durable de l'eau un "
                      "principe structurant de l'aménagement du territoire, en "
                      "inscrivant les fonctions de régulation hydrique des "
                      "sols et des écosystèmes dans les documents de "
                      "planification et les décisions d'aménagement.",
             "portee": "anticipe", "termes": []},
            {"texte": "Identifier et cartographier les écosystèmes dont "
                      "dépendent les chaînes d'approvisionnement industrielles "
                      "afin d'intégrer ces dépendances dans les décisions "
                      "d'investissement et la gestion des risques.",
             "portee": "decide", "termes": []},
            {"texte": "Élargir les plans de transition bas carbone à des plans "
                      "« transition nature », intégrant les dépendances des "
                      "entreprises aux écosystèmes (eau verte, sols, forêts, "
                      "zones humides) et leur contribution à leur "
                      "préservation.",
             "portee": "decide", "termes": []},
            {"texte": "Déployer des politiques de préservation et de "
                      "restauration des sols afin de conforter leur capacité "
                      "de rétention et d'infiltration de l'eau, notamment par "
                      "l'évolution des pratiques agricoles et des politiques "
                      "d'urbanisme.",
             "portee": "contribue", "termes": []},
        ],
    },
    "contexte_hydrologique": {
        "chapeau":
            "L'évaluation de l'empreinte hydrique des projets industriels sur "
            "l'ensemble de leur cycle de vie permet d'anticiper les effets de "
            "l'évolution de la ressource sur leurs activités. Elle constitue "
            "un outil de préparation à l'adaptation et doit, à ce titre, être "
            "intégrée aux plans d'adaptation des entreprises. Cette évaluation "
            "doit être construite au niveau local, afin de tenir compte de la "
            "disponibilité de la ressource, des autres usages du bassin "
            "versant et des risques propres à chaque territoire.",
        "mesures": [
            {"texte": "Définir un cadre commun d'accès aux données sur la "
                      "disponibilité présente et future de la ressource, pour "
                      "permettre aux industriels d'évaluer l'impact de leurs "
                      "projets à l'échelle de chaque bassin versant.",
             "portee": "anticipe", "termes": []},
            {"texte": "Conditionner la participation aux instances de "
                      "gouvernance des usages de l'eau à la réalisation d'une "
                      "analyse contextualisée de l'empreinte hydrique, des "
                      "usages et des risques, à l'échelle du bassin versant et "
                      "sur l'ensemble du cycle de vie des projets industriels, "
                      "y compris lors de la cessation d'activité.",
             "portee": "anticipe", "termes": []},
            {"texte": "Intégrer dans l'évaluation des projets industriels un "
                      "stress test hydrique fondé sur les projections "
                      "climatiques et hydrologiques de référence, cohérentes "
                      "avec la TRACC, afin d'anticiper les risques liés à "
                      "l'eau et de traduire la valeur de la ressource dans le "
                      "pilotage de l'activité économique.",
             "portee": "decide", "termes": ["tracc"]},
        ],
    },
    "planifier_prelevements": {
        "chapeau":
            "L'évolution de la disponibilité de la ressource impose d'adapter "
            "les prélèvements aux capacités de chaque bassin versant et de "
            "renforcer la coordination entre les usagers. Une gestion "
            "collective doit permettre de planifier les usages et d'organiser "
            "les actions nécessaires à la préservation de la ressource.",
        "mesures": [
            {"texte": "Fixer des objectifs quantifiés de prélèvement par "
                      "filière, à l'échelle des bassins et sous-bassins "
                      "versants, adaptés à la pression exercée sur la "
                      "ressource afin d'éclairer les décisions prises dans le "
                      "cadre des SAGE.",
             "portee": "anticipe", "termes": ["sage"]},
            {"texte": "Développer des projets d'intérêt commun associant les "
                      "usagers concernés pour définir les actions à mener sur "
                      "l'eau et les sols, ainsi que les modalités de "
                      "contribution et de compensation nécessaires à leur mise "
                      "en œuvre.",
             "portee": "contribue", "termes": []},
            {"texte": "Prendre systématiquement en compte les enjeux du cycle "
                      "hydrologique global dans les stratégies de "
                      "développement économique local, en mobilisant les "
                      "collectivités territoriales et les réseaux consulaires "
                      "aux côtés des partenaires financiers publics et privés.",
             "portee": "contribue", "termes": []},
        ],
    },
    "tarification_eau": {
        "chapeau":
            "Les mécanismes de tarification doivent mieux refléter la pression "
            "exercée sur la ressource et inciter les acteurs économiques à "
            "réduire leurs prélèvements. Leur évolution doit également "
            "favoriser les investissements qui améliorent l'efficacité "
            "hydrique et contribuer au financement de la préservation des "
            "écosystèmes à l'échelle des bassins versants.",
        "mesures": [
            {"texte": "Instaurer une tarification incitative associant un prix "
                      "plancher reflétant le coût réel du service à une part "
                      "variable modulée selon la pression exercée sur la "
                      "ressource, tout en prévoyant un mécanisme de "
                      "plafonnement afin de préserver les activités "
                      "économiques.",
             "portee": "anticipe", "termes": []},
            {"texte": "Affecter les recettes issues de la modulation tarifaire "
                      "au financement d'actions de préservation et de "
                      "restauration des écosystèmes à l'échelle des bassins "
                      "versants, sous l'égide d'une gouvernance locale "
                      "associant collectivités, industriels, agriculteurs et "
                      "autres usagers de la ressource.",
             "portee": "anticipe", "termes": []},
            {"texte": "Moduler à la baisse la part variable du tarif pour les "
                      "usagers dont les investissements dans le recyclage, la "
                      "réutilisation ou la récupération de l'eau permettent "
                      "une réduction durable et mesurable des prélèvements.",
             "portee": "anticipe", "termes": []},
            {"texte": "Rendre visibles sur les factures des acteurs "
                      "économiques les différentes composantes du coût de "
                      "l'eau afin de matérialiser sa valeur réelle et de "
                      "renforcer le signal-prix.",
             "portee": "anticipe", "termes": []},
        ],
    },
    "competences_eau": {
        "chapeau":
            "Le manque de compétences spécialisées et la diffusion "
            "insuffisante des connaissances freinent le déploiement de "
            "solutions adaptées aux enjeux de l'eau. La formation des acteurs "
            "et le rapprochement entre recherche et entreprises doivent "
            "accélérer leur développement et leur mise en œuvre.",
        "mesures": [
            {"texte": "Déployer des programmes de formation continue destinés "
                      "aux élus et aux collaborateurs des entreprises afin "
                      "d'ancrer une culture partagée de l'eau.",
             "portee": "decide", "termes": []},
            {"texte": "Développer des parcours de formation incluant des "
                      "visites de terrain pour les métiers exposés aux risques "
                      "hydriques, des concepteurs urbains aux exploitants "
                      "agricoles, pour mieux appréhender le fonctionnement du "
                      "cycle hydrologique et les enjeux économiques liés à "
                      "l'eau.",
             "portee": "decide", "termes": []},
            {"texte": "Créer des chaires académiques partenariales et des "
                      "incubateurs dédiés à l'innovation dans le domaine de "
                      "l'eau afin d'accélérer le transfert de connaissances.",
             "portee": "contribue", "termes": []},
            {"texte": "Développer des centres de R&D mutualisés afin de "
                      "concentrer les moyens consacrés à l'innovation, "
                      "notamment sur le traitement des polluants émergents "
                      "comme les PFAS et les micropolluants qui freinent la "
                      "réutilisation de l'eau.",
             "portee": "contribue", "termes": ["pfas"]},
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  LE GLOSSAIRE — LES SIGLES QUE LES MESURES EMPLOIENT
#
#  Ce sont les notes de bas de page du document, reprises telles quelles. Elles
#  ne sont pas décoratives : une mesure qui demande un « stress test hydrique
#  cohérent avec la TRACC » est inapplicable pour qui ne sait pas ce qu'est la
#  TRACC, et un livrable qui cite le sigle sans le définir fait porter au
#  lecteur le travail que l'auteur avait déjà fait.
#
#  QUELLE MESURE CITE QUEL TERME EST CALCULÉ, jamais recopié : `termes` est
#  déclaré sur la mesure, et `_verifier()` refuse un terme du glossaire que
#  plus aucune mesure n'emploie — comme un terme employé qui n'existe pas.
# ═══════════════════════════════════════════════════════════════════════════

GLOSSAIRE = {
    "tracc": {
        "sigle": "TRACC",
        "developpe": "Trajectoire de réchauffement de référence pour "
                     "l'adaptation au changement climatique",
        "definition": "Cadre élaboré par la France pour guider l'adaptation "
                      "aux effets du changement climatique.",
    },
    "sage": {
        "sigle": "SAGE",
        "developpe": "Schéma d'aménagement et de gestion des eaux",
        "definition": "Outil de planification locale, élaboré collectivement à "
                      "l'échelle d'un bassin versant ou d'une nappe "
                      "souterraine, qui fixe les objectifs et les règles de "
                      "gestion équilibrée et durable de la ressource en eau.",
    },
    "pfas": {
        "sigle": "PFAS",
        "developpe": "Composés per- et polyfluoroalkylés",
        "definition": "Famille de plusieurs milliers de composés chimiques "
                      "persistants utilisés dans de nombreux produits et "
                      "procédés industriels.",
    },
    "ppa_bpa": {
        "sigle": "PPA / BPA",
        "developpe": "Power Purchase Agreement / Biomethane Purchase Agreement",
        "definition": "Contrats d'approvisionnement énergétique de long terme "
                      "permettant à un consommateur d'acheter directement de "
                      "l'électricité ou du biométhane à un producteur, afin de "
                      "sécuriser les volumes, les prix et la visibilité des "
                      "investissements.",
    },
    "ghg_protocol": {
        "sigle": "GHG Protocol",
        "developpe": "Greenhouse Gas Protocol",
        "definition": "Principal référentiel international de comptabilisation "
                      "et de reporting des émissions de gaz à effet de serre "
                      "utilisé par les entreprises et les organisations.",
    },
    "macf": {
        "sigle": "MACF",
        "developpe": "Mécanisme d'ajustement carbone aux frontières",
        "definition": "Mécanisme européen visant à prendre en compte le coût "
                      "du carbone des produits importés afin de prévenir les "
                      "fuites de carbone et de préserver l'équité "
                      "concurrentielle.",
    },
    "piiec": {
        "sigle": "PIIEC",
        "developpe": "Projet important d'intérêt européen commun",
        "definition": "Dispositif européen permettant aux États membres de "
                      "soutenir conjointement, y compris par des aides "
                      "publiques, des projets stratégiques transnationaux "
                      "contribuant aux objectifs de l'Union européenne.",
    },
    "piiec_ia": {
        "sigle": "PIIEC IA",
        "developpe": "Projet important d'intérêt européen commun — "
                     "intelligence artificielle",
        "definition": "Projet de coopération européenne visant à soutenir des "
                      "investissements stratégiques dans l'intelligence "
                      "artificielle, sur le modèle du PIIEC.",
    },
    "dora": {
        "sigle": "DORA",
        "developpe": "Digital Operational Resilience Act",
        "definition": "Règlement européen sur la résilience opérationnelle "
                      "numérique, applicable au secteur financier de l'Union "
                      "européenne depuis janvier 2025.",
    },
    "tacct": {
        "sigle": "TACCT",
        "developpe": "Trajectoires d'adaptation au changement climatique des "
                     "territoires",
        "definition": "Démarche développée par l'Ademe pour accompagner les "
                      "collectivités dans l'évaluation de leur vulnérabilité "
                      "au changement climatique et la définition de stratégies "
                      "d'adaptation.",
    },
    "pics": {
        "sigle": "PICS",
        "developpe": "Plan intercommunal de sauvegarde",
        "definition": "Document organisant la préparation et la coordination "
                      "des communes d'un même territoire face aux situations "
                      "de crise.",
    },
    "undrr": {
        "sigle": "UNDRR",
        "developpe": "United Nations Office for Disaster Risk Reduction",
        "definition": "Agence des Nations unies chargée de coordonner les "
                      "actions internationales de réduction des risques de "
                      "catastrophe et de renforcer la résilience des "
                      "territoires.",
    },
    "bale_iii": {
        "sigle": "Bâle III",
        "developpe": "Accord international de Bâle III",
        "definition": "Nom de l'accord international conclu en 2010 qui a pour "
                      "objectif de renforcer la solidité du secteur bancaire, "
                      "afin de tirer les leçons de la crise financière de 2008.",
    },
    "bric": {
        "sigle": "BRIC",
        "developpe": "Building Resilient Infrastructure and Communities",
        "definition": "Programme de financement visant à renforcer la "
                      "résilience des infrastructures et des territoires face "
                      "aux risques naturels et aux effets du changement "
                      "climatique.",
    },
    "vade_mecum": {
        "sigle": "Vade-mecum",
        "developpe": "Vade-mecum des démarches de reconnaissance de la "
                     "résilience",
        "definition": "Menée par Résilience France (HCFRN) et l'association "
                      "Résiliances, cette étude vise à l'établissement d'un "
                      "panorama des démarches de reconnaissance de la "
                      "résilience et à la définition d'un vade-mecum pour "
                      "chaque type de démarche identifiée.",
    },
    "gepp_gpec": {
        "sigle": "GEPP / GPEC",
        "developpe": "Gestion des emplois et des parcours professionnels / "
                     "Gestion prévisionnelle des emplois et des compétences",
        "definition": "Dispositifs d'anticipation des évolutions des métiers "
                      "et des compétences au sein des organisations.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  LES REPÈRES CHIFFRÉS — ET CE QU'ILS N'ÉTABLISSENT PAS
#
#  Trois chiffres encadrés dans le document. Chacun porte SA source, qui n'est
#  pas toujours le document lui-même, et une LECTURE qui dit ce qu'il ne prouve
#  pas. Sans elle, ces trois-là se citent de travers avec une facilité
#  remarquable : « l'industrie consomme 80 % de l'eau » est faux d'un ordre de
#  grandeur, et « 88 % du territoire en tension en 2050 » n'est pas une
#  prévision mais un scénario tendanciel, sur une année sèche.
#
#  AUCUN DE CES CHIFFRES N'EST RECALCULÉ ICI. Ils sont cités, avec leur
#  périmètre et leur date ; un chiffre repris sans son périmètre est un chiffre
#  faux qui a l'air juste.
# ═══════════════════════════════════════════════════════════════════════════

REPERES = [
    {
        "cle": "eau_usages_economiques_2022",
        "theme": "eau",
        "chiffre": "2,1 milliards de m³",
        "enonce": "En 2022, 2,1 milliards de mètres cubes d'eau douce ont été "
                  "utilisés pour l'industrie, les collectivités, les services "
                  "publics et d'autres activités économiques — soit moins de "
                  "10 % du total. L'industrie représente à elle seule 80 % de "
                  "ces usages.",
        "source": "Encadré du document — aucune source externe n'y est citée.",
        "date": "2022",
        "lecture": "LES 80 % SONT UNE PART DE CES 2,1 MILLIARDS, PAS DE L'EAU "
                   "PRÉLEVÉE EN FRANCE. Lire « l'industrie consomme 80 % de "
                   "l'eau » est faux d'un ordre de grandeur : ces usages "
                   "économiques pèsent eux-mêmes moins de 10 % du total. Le "
                   "chiffre sert à situer un ordre de grandeur, pas à fonder "
                   "une répartition.",
    },
    {
        "cle": "tension_hydrique_2050",
        "theme": "eau",
        "chiffre": "88 % du territoire hexagonal",
        "enonce": "À l'horizon 2050, pour une année marquée par un "
                  "printemps-été sec, dans le scénario tendanciel — sans "
                  "inflexion notable de la situation actuelle —, 88 % du "
                  "territoire hexagonal seraient en situation de tension "
                  "hydrique modérée ou sévère en été.",
        "source": "« L'eau en 2050 : graves tensions sur les écosystèmes et "
                  "les usages », note d'analyse du Haut-commissariat à la "
                  "stratégie.",
        "date": "horizon 2050",
        "lecture": "CE N'EST PAS UNE PRÉVISION, C'EST UN SCÉNARIO — celui qui "
                   "prolonge la situation actuelle sans inflexion — ET IL "
                   "PORTE SUR UNE ANNÉE SÈCHE, pas sur une année moyenne. Les "
                   "deux conditions font partie du chiffre : les omettre "
                   "transforme une hypothèse de travail en fatalité annoncée.",
    },
    {
        "cle": "pertes_infrastructures_europe",
        "theme": "infrastructures",
        "chiffre": "66 milliards de dollars pour la France",
        "enonce": "Les pertes cumulées liées aux dommages causés aux "
                  "infrastructures par les aléas climatiques en Europe sont "
                  "estimées à environ 340 milliards de dollars au cours des "
                  "dix prochaines années, dans les conditions climatiques "
                  "actuelles. Parmi les pays européens, la France apparaît "
                  "comme le pays le plus exposé, avec 66 milliards de dollars "
                  "de pertes d'infrastructures, principalement dues aux "
                  "dommages causés aux réseaux de transport et au secteur de "
                  "l'énergie.",
        "source": "« The 2 Trillion Dollars Question, A Review of Short-Term "
                  "Climate Risks for Global Infrastructures », étude Callendar "
                  "— start-up française spécialisée dans l'évaluation des "
                  "risques climatiques, juin 2025.",
        "date": "juin 2025",
        "lecture": "DEUX BORNES CHANGENT CE QUE CE CHIFFRE DIT. Il est calculé "
                   "DANS LES CONDITIONS CLIMATIQUES ACTUELLES : il ne chiffre "
                   "pas le réchauffement à venir, il chiffre l'exposition "
                   "d'aujourd'hui sur dix ans. Et les 66 milliards sont "
                   "dominés par les RÉSEAUX DE TRANSPORT ET L'ÉNERGIE — un "
                   "exploitant de centre de données qui le lirait comme son "
                   "exposition propre se tromperait de périmètre. Ce qui le "
                   "concerne dans ce chiffre, c'est que ses deux dépendances "
                   "les plus critiques sont précisément les postes les plus "
                   "touchés.",
    },
    {
        "cle": "investissement_infrastructures_fr",
        "theme": "infrastructures",
        "chiffre": "76 milliards de dollars investis en 2024",
        "enonce": "Avec 76 milliards de dollars investis en 2024, la France "
                  "représente 12 % du marché européen des infrastructures et "
                  "se positionne comme le 3e marché du continent derrière "
                  "l'Allemagne et le Royaume-Uni. D'ici 2050, les "
                  "investissements annuels devraient atteindre 99 milliards de "
                  "dollars, soit une progression de 30 %, mais inférieure à la "
                  "dynamique européenne (+45 %). La France entre ainsi dans "
                  "une phase de modernisation stratégique, davantage que dans "
                  "une logique d'expansion massive.",
        "source": "« 151 000 milliards de dollars : le monde entre dans le "
                  "plus grand cycle d'investissements en infrastructures de "
                  "son histoire », communiqué de presse PwC, juillet 2026.",
        "date": "juillet 2026",
        "lecture": "LA SOURCE EST UN COMMUNIQUÉ DE PRESSE, pas une étude "
                   "publiée : les hypothèses de la projection à 2050 n'y sont "
                   "pas exposées, et le « +30 % » est une trajectoire "
                   "attendue, non un engagement. La phrase « modernisation "
                   "stratégique davantage qu'expansion massive » est "
                   "l'interprétation de l'auteur, pas une grandeur mesurée — "
                   "la citer comme un fait ferait passer une opinion de marché "
                   "pour un constat.",
    },
    {
        "cle": "consommation_dc_france",
        "theme": "energie_numerique",
        "chiffre": "2,2 % de la consommation annuelle française",
        "enonce": "Les data centers représentent à eux seuls 2,2 % de la "
                  "consommation annuelle française, soit l'équivalent de "
                  "l'électricité consommée par 9 à 10 agglomérations de plus "
                  "de 100 000 habitants pendant un an.",
        "source": "« Consommation électrique des data centers : 5 scénarios "
                  "pour demain », Ademe, janvier 2026.",
        "date": "janvier 2026",
        "lecture": "IL S'AGIT D'ÉLECTRICITÉ, ET DU PARC ENTIER À CETTE DATE. "
                   "La comparaison aux agglomérations est une équivalence "
                   "d'ordre de grandeur destinée à rendre le chiffre lisible, "
                   "pas une substitution : personne n'arbitre entre un centre "
                   "de données et une ville. La source elle-même présente cinq "
                   "scénarios — citer le seul chiffre d'aujourd'hui sans dire "
                   "qu'il en existe cinq trajectoires appauvrit ce qu'elle dit.",
    },
]

def _verifier():
    if len(PROPOSITIONS) != 30:
        raise ValueError("le référentiel annonce trente propositions et en "
                         "porte %d" % len(PROPOSITIONS))
    vues, numeros = set(), []
    for p in PROPOSITIONS:
        if p["cle"] in vues:
            raise ValueError("clé de proposition dupliquée : %r" % p["cle"])
        vues.add(p["cle"])
        numeros.append(p["numero"])
        if p["theme"] not in _THEME:
            raise ValueError("proposition %d : thème inconnu %r"
                             % (p["numero"], p["theme"]))
        if p["portee"] not in PORTEES:
            raise ValueError("proposition %d : portée inconnue %r"
                             % (p["numero"], p["portee"]))
        for champ in ("titre", "dit", "pour_le_centre"):
            if len(str(p.get(champ) or "").strip()) < 40:
                raise ValueError("proposition %d : « %s » vide ou trop court "
                                 "pour être une justification"
                                 % (p["numero"], champ))
        if not p["enjeux"]:
            raise ValueError("proposition %d : aucun enjeu touché — une "
                             "proposition qui ne touche rien n'a pas sa place "
                             "dans un livrable d'étude" % p["numero"])
    if sorted(numeros) != list(range(1, 31)):
        raise ValueError("la numérotation n'est pas 1..30 : %s" % sorted(numeros))
    # Chaque thème porte cinq propositions — c'est la structure du document,
    # et un thème qui en perdrait une passerait sinon inaperçu.
    for t in THEMES:
        n = len([p for p in PROPOSITIONS if p["theme"] == t["cle"]])
        if n != 5:
            raise ValueError("le thème « %s » porte %d propositions au lieu "
                             "de cinq" % (t["nom"], n))

    # ── LES MESURES ────────────────────────────────────────────────────────
    connues = {p["cle"] for p in PROPOSITIONS}
    cites = set()
    for cle, bloc in MESURES.items():
        if cle not in connues:
            raise ValueError("MESURES : « %s » ne désigne aucune proposition"
                             % cle)
        if len(str(bloc.get("chapeau") or "").strip()) < 80:
            raise ValueError("mesures de « %s » : chapeau absent ou trop "
                             "court pour être celui du document" % cle)
        if len(bloc["mesures"]) < 3:
            raise ValueError("mesures de « %s » : %d mesure(s) — le document "
                             "en porte trois à cinq par proposition"
                             % (cle, len(bloc["mesures"])))
        for m in bloc["mesures"]:
            if m["portee"] not in PORTEES:
                raise ValueError("mesure de « %s » : portée inconnue %r"
                                 % (cle, m["portee"]))
            if len(m["texte"].strip()) < 60:
                raise ValueError("mesure de « %s » : texte trop court pour "
                                 "être celui du document" % cle)
            for t in m["termes"]:
                if t not in GLOSSAIRE:
                    raise ValueError("mesure de « %s » : terme « %s » absent "
                                     "du glossaire" % (cle, t))
                cites.add(t)
        # LA PORTÉE DE LA PROPOSITION FIGURE PARMI CELLES DE SES MESURES. Une
        # proposition lue DÉCIDE dont aucune mesure ne se décide serait une
        # promesse sans objet ; l'inverse — une mesure plus engageante que sa
        # proposition — est permis et c'est précisément ce que
        # `mesures_masquees()` va chercher.
        prop = [p for p in PROPOSITIONS if p["cle"] == cle][0]
        if prop["portee"] not in {m["portee"] for m in bloc["mesures"]}:
            raise ValueError(
                "proposition %d : lue « %s », alors qu'aucune de ses mesures "
                "ne l'est (%s)" % (prop["numero"], prop["portee"],
                                   sorted({m["portee"] for m in bloc["mesures"]})))
    orphelins = sorted(set(GLOSSAIRE) - cites)
    if orphelins:
        raise ValueError("termes du glossaire que plus aucune mesure "
                         "n'emploie : %s" % orphelins)

    # ── LES REPÈRES ────────────────────────────────────────────────────────
    vus = set()
    for r in REPERES:
        if r["cle"] in vus:
            raise ValueError("repère dupliqué : %r" % r["cle"])
        vus.add(r["cle"])
        if r["theme"] not in _THEME:
            raise ValueError("repère %s : thème inconnu %r" % (r["cle"], r["theme"]))
        for champ in ("chiffre", "enonce", "source", "date", "lecture"):
            if not str(r.get(champ) or "").strip():
                raise ValueError("repère %s : « %s » vide — un chiffre sans "
                                 "source ni lecture se cite de travers"
                                 % (r["cle"], champ))


_verifier()   # refuse au chargement, pas à l'affichage


# ═══════════════════════════════════════════════════════════════════════════
#  LECTURES
# ═══════════════════════════════════════════════════════════════════════════

def referentiel():
    """Tout ce dont une interface a besoin. Une seule définition côté serveur :
    une liste recopiée dans le HTML finit toujours par diverger du moteur."""
    return {"version": VERSION, "source": dict(SOURCE),
            "themes": [dict(t) for t in THEMES],
            "portees": {k: dict(v) for k, v in PORTEES.items()},
            # CHAQUE PROPOSITION PORTE SES MESURES ET LEURS PORTÉES. Les
            # servir à part obligerait l'écran à les rapprocher lui-même, et
            # c'est exactement le rapprochement qui a manqué jusqu'ici.
            "propositions": [dict(p, enjeux=list(p["enjeux"]),
                                  chapeau=chapeau_de(p["cle"]),
                                  mesures=mesures_de(p["cle"]),
                                  portees_mesures=portees_des_mesures(p["cle"]))
                             for p in PROPOSITIONS],
            "couverture_mesures": couverture_mesures(),
            "mesures_masquees": mesures_masquees(),
            "glossaire": {k: dict(v) for k, v in GLOSSAIRE.items()},
            "reperes": [dict(r) for r in REPERES]}


def par_enjeu(cles_enjeux):
    """Les propositions qui touchent au moins un des enjeux donnés, dans
    l'ordre du document.

    L'ORDRE COMPTE : le numéro est la seule référence stable vers le document
    d'origine. Trier par pertinence supposée ferait perdre au lecteur le moyen
    de retrouver la proposition dans le texte qu'elle cite."""
    voulus = set(cles_enjeux or ())
    return [p for p in PROPOSITIONS if voulus.intersection(p["enjeux"])]


def hors_couverture(cles_enjeux):
    """Les propositions que le projet DÉCIDE ou ANTICIPE, et qu'aucun des
    enjeux donnés ne couvre.

    C'EST LA MOITIÉ UTILE, et la raison d'être de cette fonction. Lister ce
    qu'une stratégie couvre déjà rassure ; lister ce qu'elle laisse dehors est
    ce qui la fait avancer. Les propositions de portée « contribue » n'y
    figurent pas : les compter comme des trous reprocherait au projet de ne
    pas décider ce qu'il ne décide pas."""
    voulus = set(cles_enjeux or ())
    return [p for p in PROPOSITIONS
            if p["portee"] in ("decide", "anticipe")
            and not voulus.intersection(p["enjeux"])]


def enjeux_cites():
    """Toutes les clés d'enjeux citées par le référentiel — pour que
    `strategie_dd` vérifie, au chargement, qu'aucune n'est inconnue."""
    return sorted({c for p in PROPOSITIONS for c in p["enjeux"]})


def sante():
    par_theme = {}
    par_portee = {}
    for p in PROPOSITIONS:
        par_theme[p["theme"]] = par_theme.get(p["theme"], 0) + 1
        par_portee[p["portee"]] = par_portee.get(p["portee"], 0) + 1
    return {"version": VERSION, "propositions": len(PROPOSITIONS),
            "themes": par_theme, "portees": par_portee,
            "enjeux_cites": len(enjeux_cites()), "problemes": []}


def mesures_de(cle_proposition):
    """Les mesures d'une proposition, termes du glossaire résolus.

    Rend une liste VIDE pour les vingt propositions dont les mesures ne sont
    pas relevées — et `couverture_mesures()` dit lesquelles. Une liste vide qui
    se lirait « cette proposition n'a pas de mesures » serait fausse : elle
    n'en a pas ICI."""
    bloc = MESURES.get(cle_proposition)
    if not bloc:
        return []
    return [dict(m, termes=[dict(GLOSSAIRE[t], cle=t) for t in m["termes"]])
            for m in bloc["mesures"]]


def chapeau_de(cle_proposition):
    bloc = MESURES.get(cle_proposition)
    return bloc["chapeau"] if bloc else None


def couverture_mesures():
    """Combien de propositions portent leurs mesures détaillées, et lesquelles.

    ELLE EST RENDUE AVEC LES MESURES, ET JAMAIS APRÈS. Dix propositions sur
    trente les portent : afficher les mesures sans dire cela laisserait croire
    que les vingt autres n'en ont pas, alors qu'elles n'ont pas été relevées.
    C'est la même règle qu'ailleurs — une couverture tue se lit comme une
    absence."""
    avec = [p["cle"] for p in PROPOSITIONS if p["cle"] in MESURES]
    return {
        "total": len(PROPOSITIONS),
        "avec_mesures": len(avec),
        "sans_mesures": len(PROPOSITIONS) - len(avec),
        "themes_releves": sorted({p["theme"] for p in PROPOSITIONS
                                  if p["cle"] in MESURES}),
        "mesures": sum(len(b["mesures"]) for b in MESURES.values()),
        "pourquoi": "Les mesures ne sont relevées que pour les thèmes versés "
                    "au dossier. Les autres propositions gardent le résumé du "
                    "document ; elles ne sont pas dépourvues de mesures, "
                    "elles ne sont pas dépouillées ici.",
    }


def mesures_masquees():
    """Les mesures que la portée de leur proposition rend invisibles.

    LE DÉFAUT QUE CETTE FONCTION EXPOSE, ET QUI A MOTIVÉ TOUT LE BLOC. La
    portée d'une proposition est une lecture d'ENSEMBLE, et elle est juste à ce
    titre : un centre de données ne structure pas la recherche nationale sur
    l'eau, donc la proposition 25 est bien « contribue ». Mais deux de ses
    quatre mesures sont la formation de ses propres exploitants aux risques
    hydriques — cela, il le décide seul.

    Or `hors_couverture()` ne regarde que les propositions DÉCIDE ou ANTICIPE.
    Ces deux mesures-là ne pouvaient donc apparaître dans AUCUN livrable, quel
    que soit le projet : la moitié utile de la confrontation en laissait tomber
    une part, et rien ne le signalait.

    Une mesure est masquée quand sa portée engage PLUS que celle de sa
    proposition — c'est-à-dire quand le résumé a perdu du travail actionnable
    en route.
    """
    masquees = []
    for p in PROPOSITIONS:
        bloc = MESURES.get(p["cle"])
        if not bloc:
            continue
        rang_p = RANG_PORTEE[p["portee"]]
        for i, m in enumerate(bloc["mesures"]):
            if RANG_PORTEE[m["portee"]] > rang_p:
                masquees.append({
                    "numero": p["numero"], "cle": p["cle"], "titre": p["titre"],
                    "theme": p["theme"], "rang": i + 1,
                    "texte": m["texte"], "portee": m["portee"],
                    "portee_proposition": p["portee"],
                    "enjeux": list(p["enjeux"]),
                })
    return masquees


def portees_des_mesures(cle_proposition):
    """Les portées présentes parmi les mesures, de la plus engageante à la
    moins — pour que l'écran puisse dire qu'une proposition en mélange
    plusieurs, au lieu de n'afficher que celle du résumé."""
    bloc = MESURES.get(cle_proposition)
    if not bloc:
        return []
    vues = {m["portee"] for m in bloc["mesures"]}
    return sorted(vues, key=lambda x: -RANG_PORTEE[x])


def glossaire_cite(cles_propositions):
    """Les seuls termes employés par les propositions données.

    Servir les dix termes à chaque fois noierait les deux qui comptent. Un
    glossaire complet est un glossaire qu'on ne lit pas."""
    voulus = set(cles_propositions or ())
    cites = []
    for cle in voulus:
        for m in MESURES.get(cle, {}).get("mesures", []):
            cites.extend(m["termes"])
    return [dict(GLOSSAIRE[t], cle=t) for t in sorted(set(cites))]


def reperes_des_themes(cles_themes):
    """Les repères chiffrés des thèmes donnés, avec leur source et leur lecture."""
    voulus = set(cles_themes or ())
    return [dict(r) for r in REPERES if r["theme"] in voulus]
