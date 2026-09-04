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

CE QUE CE MODULE NE FAIT PAS. Il ne décerne aucune conformité : ces
propositions ne sont ni une norme, ni un référentiel certifiable, ni un texte
en vigueur. Il ne les récrit pas non plus : `titre` et `dit` restent au plus
près du document ; `pour_le_centre` est la transposition, et elle est de
CONSEILPREV, pas du Cercle de Giverny. Confondre les deux ferait dire à
l'auteur ce qu'il n'a pas écrit.
"""

VERSION = "2026-09-a"

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
            "propositions": [dict(p, enjeux=list(p["enjeux"]))
                             for p in PROPOSITIONS]}


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
