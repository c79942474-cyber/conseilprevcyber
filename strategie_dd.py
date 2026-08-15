# -*- coding: utf-8 -*-
"""La stratégie de développement durable d'un centre de données — le premier livrable.

CE QUE CE MODULE FAIT

Il applique aux centres de données la méthode des QUATRE PERSPECTIVES : raison
d'être, influence des parties prenantes, science et technologie, valeur
commerciale. Un questionnaire rempli par le client alimente les trois
perspectives qui lui appartiennent ; la quatrième — la science — n'est pas une
opinion et n'est donc pas demandée au client : elle est établie par le registre
d'enjeux et par le moteur de calcul.

De ces réponses, le module produit le document d'ouverture d'étude : ce que le
projet défend, ce que ses parties prenantes disent, ce que les données disent,
ce qui affecte ses résultats — puis la matérialité au croisement des quatre, et
le programme d'étude qui en découle.

LES DEUX TENSIONS SONT LE SUJET, PAS UN CHAPITRE

  · EXTÉRIEUR / INTÉRIEUR. Sans l'extérieur, on décide dans sa bulle. Avec le
    seul extérieur, on sur-réagit à la demande la plus bruyante. Le module
    compte les enjeux tirés du dehors sans adhésion interne, et ceux portés
    par la seule raison d'être — les deux sont des positions tenables, mais
    elles ne se pilotent pas de la même façon, et les confondre est ce qui
    produit les stratégies illisibles.

  · PERCEPTION / RÉALITÉ. Un enjeu que les données minorent mais que l'opinion
    tient pour central reste un enjeu : « tant que l'opinion le considère comme
    l'enjeu principal, c'est un problème qui doit être traité ». Et l'inverse,
    plus dangereux parce que silencieux : un enjeu que les données donnent pour
    structurant et que PERSONNE ne soulève ne disparaît pas — il arrive plus
    tard, sans avoir prévenu. Le module nomme les deux écarts au lieu de les
    moyenner : moyenner une divergence, c'est effacer l'information.

CE QUE CE MODULE REFUSE DE FAIRE

Il ne retient pas tout. Une stratégie qui retient vingt enjeux n'en retient
aucun : elle produit le tourbillon où chaque partie prenante tire l'entreprise
de son côté, et l'effet involontaire est la dispersion. Le document dit donc
aussi ce qui est ÉCARTÉ, et pourquoi — c'est la moitié difficile, et celle qui
prouve qu'un arbitrage a eu lieu.

Il ne comble pas les trous. Un enjeu non instruit n'est pas un enjeu mineur :
c'est un enjeu qu'on n'a pas regardé. Il figure comme tel, jamais avec un score
favorable par défaut.

Il ne décerne aucune conformité, aucune neutralité, aucun label : ces
qualifications se constatent sur dossier complet par un vérificateur accrédité.
"""

import datacenter as D

VERSION = "2026-08-a"


# ═══════════════════════════════════════════════════════════════════════════
#  1. LES QUATRE PERSPECTIVES, ET CE QU'ON DEMANDE À CHACUNE
#
#  Les questions clé et les outils sont ceux de la méthode, transposés aux
#  centres de données. `source` dit qui répond — et c'est structurant : la
#  perspective scientifique n'est PAS remplie par le client, sans quoi on
#  recueillerait une opinion en croyant recueillir une donnée.
# ═══════════════════════════════════════════════════════════════════════════

PERSPECTIVES = [
    {
        "cle": "raison_etre",
        "nom": "Raison d'être",
        "question": "Que défendons-nous ?",
        "source": "client",
        "objet": "Pourquoi ce centre de données existe, comment il veut "
                 "fonctionner, et quels impacts comptent au regard des valeurs "
                 "qu'il s'efforce de défendre.",
        "questions": [
            "Quelle est la raison d'être de ce centre de données — en d'autres "
            "termes, pourquoi le construisons-nous, au-delà de la capacité ?",
            "Quelles valeurs définissent notre manière de le concevoir, de le "
            "construire et de l'exploiter ?",
            "Quelle est notre vision : quel avenir souhaitons-nous pour "
            "l'entreprise, pour le secteur et pour le territoire d'accueil ?",
            "Quels engagements publics avons-nous déjà pris, et lesquels ce "
            "projet devra-t-il tenir ?",
        ],
        "outils": [
            "Facilitation du dialogue à travers l'organisation",
            "Analyse de la valeur client",
            "Exploration de l'histoire organisationnelle",
        ],
    },
    {
        "cle": "parties_prenantes",
        "nom": "Influence des parties prenantes",
        "question": "Qu'essaient-elles de nous dire ?",
        "source": "client",
        "objet": "Ce que disent — et ce que feront — les acteurs internes, les "
                 "interlocuteurs immédiats et l'écosystème plus large.",
        "questions": [
            "Quelles sont les préoccupations des intervenants internes "
            "(exploitants, équipes projet, partenaires) ?",
            "Quelles sont celles des interlocuteurs immédiats (clients "
            "hébergés, investisseurs, prêteurs, riverains, collectivité, "
            "gestionnaire de réseau, autorité de l'eau, services instructeurs) ?",
            "Quelles sont celles des autres parties prenantes (médias, ONG, "
            "associations de riverains, élus, concurrents, coalitions "
            "sectorielles) ?",
            "Comment recueillons-nous leurs avis, et comment pourrions-nous le "
            "faire de manière plus proactive ?",
        ],
        "outils": [
            "Tables rondes avec les clients et les parties prenantes",
            "Enquêtes entraînant l'établissement d'un classement ou une "
            "allocation de points",
            "Permanences et registre d'enquête publique",
            "Analyse de sentiments par IA sur la presse et les réseaux locaux",
        ],
        "garde": "Distinguer les préférences DÉCLARÉES des comportements "
                 "réels : un riverain qui déclare accepter le projet et qui "
                 "dépose un recours a dit deux choses différentes, et c'est la "
                 "seconde qui décale le calendrier.",
    },
    {
        "cle": "science",
        "nom": "Science et technologie",
        "question": "Que disent les données sur notre impact et notre futur ?",
        "source": "donnees",
        "objet": "Ce que l'état des connaissances et le calcul établissent, "
                 "indépendamment de ce que l'on souhaite et de ce qui se dit.",
        "questions": [
            "Existe-t-il des limites planétaires (seuils écologiques) que ce "
            "projet contribue à dépasser ?",
            "Générons-nous des impacts nets positifs, et sur quel périmètre ?",
            "Existe-t-il des besoins sociaux non satisfaits dans les "
            "communautés vitales pour le projet ?",
            "Comment les changements planétaires affecteront-ils le site sur "
            "sa durée de vie ?",
            "Quelles technologies émergentes affecteront nos impacts et nos "
            "profits ?",
        ],
        "outils": [
            "Analyse du cycle de vie",
            "Analyse des risques climatiques physiques",
            "Étude du salaire décent dans la chaîne d'approvisionnement",
            "Modélisation de la courbe d'apprentissage technologique",
            "Bilan énergie, eau et carbone du moteur de calcul",
        ],
        "garde": "Cette perspective n'est pas remplie par le client. Une "
                 "opinion recueillie dans cette colonne serait une opinion "
                 "présentée comme une donnée — exactement ce que la méthode "
                 "cherche à éviter.",
    },
    {
        "cle": "valeur",
        "nom": "Valeur commerciale",
        "question": "Qu'est-ce qui affecte nos résultats ?",
        "source": "client",
        "objet": "Les enjeux qui pèsent sur les coûts, les revenus, les "
                 "risques et la valeur intangible.",
        "questions": [
            "Comment les amendes, redevances, taxes, élimination des déchets, "
            "turnover et pertes affecteront-ils nos coûts ?",
            "Quand et dans quels domaines nos clients hébergés sont-ils prêts "
            "à supporter un coût supplémentaire pour de meilleures pratiques ?",
            "Quels risques courons-nous en matière de retard d'autorisation, "
            "de refus de raccordement, de réduction de revenus ou "
            "d'augmentation des coûts ?",
            "Quelle valeur intangible pouvons-nous créer grâce à notre "
            "leadership sur certains enjeux ?",
        ],
        "outils": [
            "Analyse coûts / bénéfices",
            "Analyse des risques",
            "Études de marché",
        ],
        "garde": "C'est la matérialité dite « unique » : apolitique, "
                 "financière, et pour cette raison la plus facile à faire "
                 "accepter. Elle ne voit que le court terme — s'en contenter "
                 "revient à ne jamais repérer ce qui se profile.",
    },
]

_PERSP = {p["cle"]: p for p in PERSPECTIVES}
CLES_CLIENT = [p["cle"] for p in PERSPECTIVES if p["source"] == "client"]


# ═══════════════════════════════════════════════════════════════════════════
#  2. L'ÉCHELLE
#
#  Quatre degrés et une absence. L'absence n'est PAS un zéro : « sans objet »
#  est une conclusion, « non instruit » est un trou, et les confondre ferait
#  disparaître du document tout ce qu'on n'a pas regardé.
# ═══════════════════════════════════════════════════════════════════════════

DEGRES = {
    0: {"cle": "sans_objet", "nom": "Sans objet",
        "dit": "L'enjeu ne concerne pas ce projet. Doit être justifié : une "
               "exclusion non motivée est le premier point que relève un "
               "vérificateur."},
    1: {"cle": "secondaire", "nom": "Secondaire",
        "dit": "Présent, sans peser sur les décisions de conception."},
    2: {"cle": "significatif", "nom": "Significatif",
        "dit": "Pèse sur une décision au moins, et mérite d'être instruit."},
    3: {"cle": "structurant", "nom": "Structurant",
        "dit": "Commande une décision de conception ou conditionne le projet."},
}

NON_INSTRUIT = {
    "nom": "Non instruit",
    "dit": "Personne n'a regardé. Ce n'est pas un enjeu mineur : c'est un "
           "enjeu sans réponse, et il figure comme tel jusqu'à ce qu'il en "
           "reçoive une.",
}


# ═══════════════════════════════════════════════════════════════════════════
#  3. LE CONTEXTE DU SITE
#
#  Ces réponses ne notent aucun enjeu : elles MODULENT ce que la science en
#  dit. Le même centre de données ne pose pas le même problème d'eau en
#  Scandinavie et en Espagne, et prétendre le contraire produirait un document
#  interchangeable — c'est-à-dire sans valeur.
# ═══════════════════════════════════════════════════════════════════════════

CONTEXTE = [
    {"cle": "stress_hydrique", "nom": "Stress hydrique du bassin d'implantation",
     "options": [("faible", "Faible"), ("modere", "Modéré"),
                 ("eleve", "Élevé"), ("tres_eleve", "Très élevé")],
     "pourquoi": "Commande l'arbitrage eau / énergie du refroidissement, et "
                 "l'acceptabilité locale du prélèvement."},
    {"cle": "tension_reseau", "nom": "Tension sur le réseau électrique local",
     "options": [("faible", "Capacité disponible"),
                 ("modere", "Capacité contrainte"),
                 ("eleve", "File d'attente de raccordement"),
                 ("tres_eleve", "Moratoire ou refus de raccordement")],
     "pourquoi": "C'est le premier facteur qui arrête un projet de centre de "
                 "données, avant tout arbitrage environnemental."},
    {"cle": "voisinage", "nom": "Proximité des habitations",
     "options": [("faible", "Zone industrielle isolée"),
                 ("modere", "Zone d'activité, habitat à distance"),
                 ("eleve", "Habitat proche"),
                 ("tres_eleve", "Habitat contigu")],
     "pourquoi": "Le bruit et l'emprise se jugent au voisinage, pas en "
                 "moyenne nationale."},
    {"cle": "aleas_climatiques", "nom": "Exposition du site aux aléas climatiques",
     "options": [("faible", "Faible"), ("modere", "Modérée"),
                 ("eleve", "Élevée"), ("tres_eleve", "Très élevée")],
     "pourquoi": "Un site s'exploite trente ans : c'est le climat de 2050 qui "
                 "le dimensionne, pas celui d'aujourd'hui."},
    {"cle": "reseau_chaleur", "nom": "Preneur de chaleur mobilisable",
     "options": [("aucun", "Aucun identifié"),
                 ("etude", "Piste à l'étude"),
                 ("proche", "Réseau ou preneur à proximité"),
                 ("engage", "Preneur engagé")],
     "pourquoi": "La valorisation de chaleur ne dépend pas de nous seuls : "
                 "sans preneur, c'est une intention."},
    {"cle": "maturite_rse", "nom": "Maturité de l'organisation sur le sujet",
     "options": [("aucune", "Premier projet"),
                 ("debut", "Démarche engagée, sans inventaire vérifié"),
                 ("etablie", "Inventaire vérifié, cible publiée"),
                 ("avancee", "Trajectoire validée par un tiers")],
     "pourquoi": "Détermine ce que le projet peut porter : une cible publiée "
                 "sans inventaire est une intention, et le document doit le "
                 "dire plutôt que de l'accompagner."},
]

_CONTEXTE = {c["cle"]: c for c in CONTEXTE}
_RANG_CTX = {"faible": 0, "modere": 1, "eleve": 2, "tres_eleve": 3,
             "aucun": 0, "etude": 1, "proche": 2, "engage": 3,
             "aucune": 0, "debut": 1, "etablie": 2, "avancee": 3}


# ═══════════════════════════════════════════════════════════════════════════
#  4. LE REGISTRE DES ENJEUX — propres aux centres de données
#
#  `science` porte ce que les données établissent EN GÉNÉRAL, avec le niveau
#  qui en découle et l'outil qui l'affinera dans l'étude. `module_site` dit
#  quelle réponse de contexte relève ou abaisse ce niveau. `seul` dit si
#  l'enjeu peut être traité par l'entreprise seule — s'il ne le peut pas, la
#  réponse n'est pas un investissement, c'est une coalition.
# ═══════════════════════════════════════════════════════════════════════════

ENJEUX = [
    # ── Énergie ───────────────────────────────────────────────────────────
    {"cle": "pue", "nom": "Efficacité énergétique de l'installation",
     "famille": "energie",
     "science": 3,
     "dit": "L'énergie non informatique est le premier poste sur lequel la "
            "conception agit directement. Le PUE se dégrade à charge "
            "partielle : les auxiliaires consomment presque autant à vide.",
     "outil": "Bilan énergie du moteur de calcul, puis mesure sur douze mois "
              "au sens d'ISO/IEC 30134-2",
     "moteur": "pue", "seul": True,
     "piege": "Annoncer un PUE de conception comme un indicateur. Une plage de "
              "conception décrit une famille d'équipements, pas la machine "
              "installée."},
    {"cle": "raccordement", "nom": "Raccordement et congestion du réseau électrique",
     "famille": "energie",
     "science": 2, "module_site": ("tension_reseau", 1),
     "dit": "La capacité de raccordement est une ressource partagée avec le "
            "territoire. Là où elle manque, elle décide du projet avant tout "
            "arbitrage environnemental.",
     "outil": "Étude de raccordement du gestionnaire de réseau ; analyse des "
              "files d'attente",
     "moteur": None, "seul": False,
     "piege": "Traiter le raccordement comme une formalité de calendrier. "
              "C'est le premier motif d'abandon d'un projet de centre de "
              "données, et il se joue des années à l'avance."},
    {"cle": "carbone_electricite", "nom": "Contenu carbone de l'électricité (scope 2)",
     "famille": "carbone",
     "science": 3,
     "dit": "Pour un même kWh consommé, l'intensité carbone varie d'un facteur "
            "voisin de cinq d'un pays européen à l'autre. C'est le premier "
            "déterminant de l'empreinte d'exploitation.",
     "outil": "Bilan carbone du moteur ; facteur du gestionnaire de réseau ; "
              "double déclaration du scope 2",
     "moteur": "carbone", "seul": False,
     "piege": "Publier le seul chiffre market-based et annoncer « zéro "
              "émission électrique ». La double déclaration n'est pas une "
              "option de présentation."},
    {"cle": "sobriete", "nom": "Sobriété : la puissance qu'on n'installe pas",
     "famille": "energie",
     "science": 3,
     "dit": "Toute l'empreinte est proportionnelle à la puissance "
            "informatique installée. C'est le seul levier qui agit à la fois "
            "sur l'énergie, l'eau, le carbone d'exploitation et une bonne part "
            "du carbone incorporé.",
     "outil": "Dimensionnement sur la charge utile ; courbe de charge ; étude "
              "de consolidation",
     "moteur": "energie", "seul": True,
     "piege": "Dimensionner sur le pic annoncé par l'exploitant. Un plateau "
              "conçu pour une charge qui n'arrive pas fait tourner des "
              "auxiliaires à vide pendant toute la vie de l'installation."},

    # ── Eau ───────────────────────────────────────────────────────────────
    {"cle": "eau_site", "nom": "Consommation d'eau sur site",
     "famille": "eau",
     "science": 2, "module_site": ("stress_hydrique", 1),
     "dit": "Le refroidissement évaporatif améliore le rendement énergétique "
            "et consomme de l'eau qui ne retourne ni à la nappe ni au réseau. "
            "L'arbitrage se décide au regard du bassin, pas d'un classement "
            "général.",
     "outil": "Bilan eau du moteur ; WUE au sens d'ISO/IEC 30134-9",
     "moteur": "eau_site", "seul": True,
     "piege": "Publier un WUE en baisse sans le PUE de la même année : les "
              "deux se déplacent en sens contraire."},
    {"cle": "eau_amont", "nom": "Eau prélevée en amont par la production électrique",
     "famille": "eau",
     "science": 2,
     "dit": "Supprimer l'eau du site en augmentant l'électricité déplace le "
            "prélèvement en amont. Sur certains mix, l'arbitrage s'inverse.",
     "outil": "WUE source ; facteur eau du fournisseur d'électricité",
     "moteur": "eau_source", "seul": False,
     "piege": "Annoncer un site « sans eau » en ne comptant que le site. Le "
              "prélèvement n'a pas disparu : il a changé de bassin, et souvent "
              "de territoire — sans que personne, sur place, ne puisse le "
              "constater."},
    {"cle": "conflit_usage_eau", "nom": "Conflit d'usage de l'eau avec le territoire",
     "famille": "eau",
     "science": 1, "module_site": ("stress_hydrique", 2),
     "dit": "En bassin tendu, le prélèvement entre en concurrence avec "
            "l'agriculture et l'eau potable. La question cesse d'être "
            "technique et devient politique.",
     "outil": "Concertation avec l'autorité de l'eau ; scénarios de "
              "restriction estivale",
     "moteur": None, "seul": False,
     "piege": "Répondre par le volume moyen annuel à une inquiétude qui porte "
              "sur la pointe d'août."},

    # ── Carbone et matières ───────────────────────────────────────────────
    {"cle": "carbone_incorpore", "nom": "Carbone incorporé des équipements et du bâtiment",
     "famille": "carbone",
     "science": 3,
     "dit": "Sur un site bien implanté et alimenté en électricité peu carbonée, "
            "le carbone incorporé devient le premier poste. Il se décide à la "
            "conception et ne se rattrape jamais en exploitation.",
     "outil": "Analyse du cycle de vie ; déclarations environnementales "
              "produit des équipements retenus",
     "moteur": None, "seul": True,
     "piege": "Le remettre à plus tard parce qu'aucune partie prenante ne le "
              "demande. Il est fixé le jour de la commande."},
    {"cle": "frigorigenes", "nom": "Fluides frigorigènes et fuites",
     "famille": "carbone",
     "science": 2,
     "dit": "Émissions directes à très fort pouvoir de réchauffement, "
            "sensibles aux fuites et encadrées par la réglementation sur les "
            "gaz fluorés.",
     "outil": "Inventaire scope 1 ; taux de fuite mesuré ; choix de fluides à "
              "faible potentiel",
     "moteur": None, "seul": True,
     "piege": "Compter la charge installée et non les fuites annuelles. La "
              "première est une donnée d'inventaire matériel ; la seconde est "
              "la seule qui produise des émissions, et elle se mesure."},
    {"cle": "chaleur_fatale", "nom": "Valorisation de la chaleur fatale",
     "famille": "energie",
     "science": 2, "module_site": ("reseau_chaleur", 1),
     "dit": "La chaleur livrée remplace une production ailleurs. Le règlement "
            "européen de déclaration en fait un indicateur à publier.",
     "outil": "ERF au sens d'ISO/IEC 30134-6 ; convention d'allocation avec le "
              "preneur",
     "moteur": "chaleur", "seul": False,
     "piege": "S'attribuer le gain sans convention d'allocation : la même "
              "tonne est alors comptée deux fois."},
    {"cle": "fin_de_vie", "nom": "Fin de vie des équipements et réemploi",
     "famille": "matieres",
     "science": 2,
     "dit": "Le renouvellement accéléré des serveurs — souvent présenté comme "
            "un gain d'efficacité — se paie précisément ici, en matières et en "
            "carbone incorporé du remplaçant.",
     "outil": "Filière DEEE ; taux de réemploi ; contrat de reprise",
     "moteur": None, "seul": False,
     "piege": "Compter le don de matériel comme du réemploi sans en suivre la "
              "destination réelle."},
    {"cle": "materiaux", "nom": "Matériaux de construction et circularité",
     "famille": "matieres",
     "science": 2,
     "dit": "Béton et acier portent l'essentiel du carbone incorporé du "
            "bâtiment, décidé au stade de l'avant-projet.",
     "outil": "Analyse du cycle de vie du bâti ; déclarations "
              "environnementales des lots",
     "moteur": None, "seul": True,
     "piege": "Arbitrer les matériaux après le permis, quand la trame et les "
              "descentes de charge sont figées."},

    # ── Territoire ────────────────────────────────────────────────────────
    {"cle": "bruit", "nom": "Bruit et voisinage",
     "famille": "territoire",
     "science": 1, "module_site": ("voisinage", 2),
     "dit": "Impact environnemental modeste à l'échelle globale, mais c'est "
            "l'enjeu qui se vit quotidiennement pour les riverains — et celui "
            "qui alimente le plus de recours.",
     "outil": "Étude acoustique réglementaire ; mesures en limite de "
              "propriété ; essais de groupes",
     "moteur": None, "seul": True,
     "piege": "Répondre par la conformité réglementaire à une gêne réelle. La "
              "conformité protège juridiquement, elle ne fait pas dormir."},
    {"cle": "foncier", "nom": "Emprise foncière, artificialisation et biodiversité",
     "famille": "territoire",
     "science": 2,
     "dit": "L'artificialisation et la fragmentation des milieux relèvent de "
            "limites planétaires distinctes du climat, et ne se compensent pas "
            "par des gains énergétiques.",
     "outil": "Étude d'impact ; séquence éviter-réduire-compenser ; "
              "inventaires faune-flore",
     "moteur": None, "seul": True,
     "piege": "Traiter la biodiversité comme une variable d'ajustement du "
              "bilan carbone. Ce sont deux limites différentes."},
    {"cle": "secours", "nom": "Groupes de secours : carburant, air, essais",
     "famille": "territoire",
     "science": 1, "module_site": ("voisinage", 1),
     "dit": "Émissions directes faibles en énergie annuelle, mais concentrées "
            "dans le temps et dans l'espace : qualité de l'air locale et bruit "
            "des essais périodiques.",
     "outil": "Inventaire scope 1 ; plan d'essais ; carburants de "
              "substitution",
     "moteur": None, "seul": True,
     "piege": "Programmer les essais sur le seul critère de la maintenance, "
              "sans regarder le calendrier du voisinage."},
    {"cle": "emploi_local", "nom": "Emploi local et retombées économiques",
     "famille": "social",
     "science": 1,
     "dit": "Un centre de données mobilise beaucoup de capital et peu d'emploi "
            "permanent. L'écart entre l'attente du territoire et la réalité de "
            "l'exploitation est une source de tension durable.",
     "outil": "Étude de retombées ; engagements d'insertion ; formation locale",
     "moteur": None, "seul": False,
     "piege": "Communiquer sur les emplois de chantier en laissant croire "
              "qu'ils sont permanents. La déception se paie au projet suivant."},

    # ── Social et chaîne d'approvisionnement ──────────────────────────────
    {"cle": "chaine_humaine", "nom": "Droits humains dans la chaîne d'approvisionnement",
     "famille": "social",
     "science": 2,
     "dit": "Minerais et électronique concentrent des risques documentés de "
            "travail forcé et de conditions de travail indignes, très en amont "
            "et peu visibles depuis le site.",
     "outil": "Cartographie des fournisseurs ; étude du salaire décent ; "
              "devoir de vigilance",
     "moteur": None, "seul": False,
     "piege": "S'arrêter au rang 1. Les abus se situent aux rangs que le "
              "contrat ne nomme pas."},
    {"cle": "securite", "nom": "Sécurité des personnes, chantier et exploitation",
     "famille": "social",
     "science": 2,
     "dit": "Risque électrique de forte puissance, travaux en hauteur, "
            "coactivité de chantier : les accidents graves du secteur se "
            "concentrent sur ces trois causes.",
     "outil": "Analyse des risques ; plan de prévention ; retour d'expérience",
     "moteur": None, "seul": True,
     "piege": "Traiter la sécurité comme un chapitre réglementaire séparé de "
              "la conception, alors qu'elle se joue dans les choix "
              "d'implantation et d'accès."},

    # ── Gouvernance ───────────────────────────────────────────────────────
    {"cle": "resilience", "nom": "Résilience du site aux aléas climatiques",
     "famille": "gouvernance",
     "science": 2, "module_site": ("aleas_climatiques", 1),
     "dit": "Un site s'exploite plusieurs décennies. Vagues de chaleur, "
            "sécheresse et inondation dimensionnent les utilités à l'horizon "
            "de sa vie, pas à celui d'aujourd'hui.",
     "outil": "Analyse des risques climatiques physiques ; scénarios à 2050",
     "moteur": None, "seul": True,
     "piege": "Dimensionner le refroidissement sur les températures "
              "historiques. La série passée n'est plus la série à venir."},
    {"cle": "transparence", "nom": "Transparence, déclaration et données publiées",
     "famille": "gouvernance",
     "science": 2,
     "dit": "La déclaration européenne rend publiques une partie des données "
            "d'exploitation, et rend les installations comparables entre "
            "elles. Ce qui est publié devient un objet de débat public.",
     "outil": "Indicateurs ISO/IEC 30134 ; déclaration européenne ; "
              "vérification par un tiers",
     "moteur": None, "seul": True,
     "piege": "Découvrir l'obligation de déclarer après avoir conçu le plan de "
              "comptage. Les points de mesure se posent à la conception."},
]

_ENJEU = {e["cle"]: e for e in ENJEUX}

FAMILLES = {
    "energie": "Énergie",
    "eau": "Eau",
    "carbone": "Carbone",
    "matieres": "Matières et circularité",
    "territoire": "Territoire et voisinage",
    "social": "Social et chaîne d'approvisionnement",
    "gouvernance": "Gouvernance et résilience",
}


# ═══════════════════════════════════════════════════════════════════════════
#  5. CONTRÔLES D'INTÉGRITÉ — au chargement, pas à l'exécution
# ═══════════════════════════════════════════════════════════════════════════

# Les questions ouvertes des perspectives remplies par le client — et, pour
# chacune, des PISTES DE RÉPONSE.
#
# CE QUE LES PISTES SONT, ET NE SONT PAS. Sept cases vides arrêtaient net la
# plupart des lecteurs : « pourquoi construisons-nous ce centre ? » est une
# vraie question de direction, et personne ne la rédige de zéro dans un
# formulaire. Chaque question offre donc de quatre à huit réponses RÉALISTES,
# relevées sur ce que les projets européens répondent effectivement — la
# souveraineté, la reprise de coûts, la valorisation d'un site, l'ancrage.
#
# LA LIGNE : une piste choisie est INSÉRÉE dans la case, où elle devient le
# texte du client — modifiable, complétable, effaçable. Le livrable ne retient
# que le texte final ; aucune trace de « quelle piste » n'est conservée, parce
# qu'une réponse de direction n'est pas un choix dans un menu. Et là où le
# terrain le permet, la liste porte une piste INCONFORTABLE (« rien de
# formalisé », « nos clients arbitrent au prix », « aucun engagement public ») :
# un menu qui n'offrirait que des réponses flatteuses ne recueillerait pas une
# stratégie, il ferait passer un test de conformité.
OUVERTES = [
    {"cle": "raison_etre_texte", "perspective": "raison_etre",
     "libelle": "Pourquoi construisons-nous ce centre de données, "
                "au-delà de la capacité ?",
     "pistes": [
         "Garder en Europe les données et les modèles de nos clients, sous "
         "droit européen.",
         "Rapprocher le calcul de nos sites industriels, pour la latence et "
         "la continuité d'exploitation.",
         "Reprendre la main sur des coûts d'hébergement devenus imprévisibles "
         "chez les grands fournisseurs.",
         "Porter la croissance de nos services d'IA sans dépendre des files "
         "d'attente des hyperscalers.",
         "Valoriser un site industriel existant — foncier, raccordement — "
         "plutôt que d'artificialiser ailleurs.",
         "Doter le territoire d'une infrastructure numérique qui y fixe des "
         "emplois qualifiés.",
     ]},
    {"cle": "valeurs_texte", "perspective": "raison_etre",
     "libelle": "Quelles valeurs définissent notre manière de le "
                "concevoir, de le construire et de l'exploiter ?",
     "pistes": [
         "Sobriété d'abord : chaque kilowatt et chaque litre évités valent "
         "mieux qu'une compensation.",
         "Transparence : nos indicateurs — PUE, WUE, CUE — seront publiés et "
         "auditables.",
         "Ancrage local : entreprises du territoire, chaleur réutilisée, "
         "dialogue avec les riverains.",
         "Sécurité sans compromis : la disponibilité ne se négocie pas contre "
         "le calendrier.",
         "Réversibilité : concevoir démontable et réemployable, du bâtiment "
         "aux baies.",
         "Exemplarité sociale : conditions de chantier et d'exploitation "
         "au-dessus des obligations.",
     ]},
    {"cle": "vision_texte", "perspective": "raison_etre",
     "libelle": "Quel avenir souhaitons-nous pour l'entreprise, le "
                "secteur et le territoire d'accueil ?",
     "pistes": [
         "Devenir la référence régionale de l'hébergement sobre pour les "
         "charges d'IA.",
         "Un parc qui croît sans accroître ses prélèvements d'eau ni sa "
         "pointe sur le réseau.",
         "Faire du site une brique du système énergétique local : chaleur "
         "fournie, flexibilité offerte au réseau.",
         "Fixer sur le territoire un écosystème — intégration, formation, "
         "maintenance — qui survive au chantier.",
         "Démontrer qu'un centre de données peut être un voisin accepté, pas "
         "seulement toléré.",
     ]},
    {"cle": "engagements_texte", "perspective": "raison_etre",
     "libelle": "Quels engagements publics avons-nous déjà pris, que "
                "ce projet devra tenir ?",
     "pistes": [
         "Une neutralité carbone annoncée à échéance publique — dont le "
         "périmètre reste à préciser ici.",
         "L'adhésion au Climate Neutral Data Centre Pact, avec ses jalons.",
         "Un contrat d'électricité renouvelable signé ou en négociation, sur "
         "une part définie de la consommation.",
         "Un engagement de réutilisation de chaleur pris auprès de la "
         "collectivité.",
         "Des objectifs publiés dans notre rapport annuel, que ce projet "
         "devra chiffrer.",
         "Aucun engagement public à ce jour — ce dossier est l'occasion d'en "
         "formuler.",
     ]},
    {"cle": "ecoute_texte", "perspective": "parties_prenantes",
     "libelle": "Comment recueillons-nous aujourd'hui les avis des "
                "parties prenantes, et comment pourrions-nous le faire "
                "de manière plus proactive ?",
     "pistes": [
         "Réunions publiques et registre pendant l'instruction ; rien "
         "d'installé au-delà.",
         "Un comité de suivi riverains-collectivité-exploitant, réuni à "
         "échéance fixe.",
         "Des enquêtes régulières auprès des clients hébergés sur leurs "
         "attentes environnementales.",
         "Un canal de signalement permanent — bruit, chantier, lumière — avec "
         "engagement de réponse.",
         "Un dialogue structuré avec le gestionnaire de réseau et l'agence de "
         "l'eau, en amont des dossiers.",
         "Rien de formalisé aujourd'hui : l'écoute passe par les commerciaux, "
         "et peu remonte.",
     ]},
    {"cle": "clients_payer_texte", "perspective": "valeur",
     "libelle": "Sur quels sujets nos clients hébergés sont-ils prêts "
                "à supporter un coût supplémentaire ?",
     "pistes": [
         "Une électricité renouvelable garantie heure par heure, "
         "contractualisée.",
         "Des indicateurs vérifiés par un tiers, réutilisables dans leur "
         "propre reporting.",
         "La localisation souveraine des données et des modèles, avec "
         "engagement contractuel.",
         "Des niveaux de disponibilité supérieurs, adossés à des pénalités "
         "réelles.",
         "La chaleur fatale valorisée, qu'ils peuvent citer dans leur bilan.",
         "Presque rien : nos clients arbitrent au prix — une contrainte à "
         "assumer dans ce dossier.",
     ]},
    {"cle": "intangible_texte", "perspective": "valeur",
     "libelle": "Quelle valeur intangible pouvons-nous créer par notre "
                "leadership sur certains enjeux ?",
     "pistes": [
         "La crédibilité d'exploitant sobre, qui pèse dans les appels "
         "d'offres publics.",
         "L'acceptabilité locale : un site accepté se développe, un site "
         "contesté s'arrête.",
         "L'attractivité employeur sur des métiers en tension — énergie, "
         "froid, exploitation.",
         "Une prime de confiance des financeurs, sensibles aux risques ESG "
         "documentés.",
         "Un capital de bonne foi qui protège le jour où un incident "
         "survient.",
     ]},
]


def _verifier():
    fautes = []
    cles = [e["cle"] for e in ENJEUX]
    if len(set(cles)) != len(cles):
        fautes.append("clé d'enjeu dupliquée")

    for e in ENJEUX:
        if e["famille"] not in FAMILLES:
            fautes.append("enjeu %s : famille inconnue %s" % (e["cle"], e["famille"]))
        if e["science"] not in DEGRES:
            fautes.append("enjeu %s : niveau scientifique hors échelle" % e["cle"])
        # Un enjeu sans piège est un enjeu qu'on n'a pas travaillé : le piège
        # est ce qui distingue un registre d'une liste de mots.
        for champ in ("dit", "outil", "piege"):
            if len((e.get(champ) or "").strip()) < 40:
                fautes.append("enjeu %s : %s trop court pour être utile"
                              % (e["cle"], champ))
        m = e.get("module_site")
        if m:
            if m[0] not in _CONTEXTE:
                fautes.append("enjeu %s : contexte inconnu %s" % (e["cle"], m[0]))
            if not isinstance(m[1], int) or m[1] < 1:
                fautes.append("enjeu %s : modulation nulle ou négative" % e["cle"])
        if e.get("moteur") and e["moteur"] not in _GRANDEURS:
            fautes.append("enjeu %s : grandeur moteur inconnue %s"
                          % (e["cle"], e["moteur"]))

    # Chaque option de contexte doit être classable : une option absente du
    # barème rendrait la modulation silencieusement nulle, et l'enjeu qu'elle
    # devait relever resterait au niveau générique sans que rien ne le dise.
    for c in CONTEXTE:
        for cle, _ in c["options"]:
            if cle not in _RANG_CTX:
                fautes.append("contexte %s : option non classée %s" % (c["cle"], cle))

    # Un contexte que personne ne module ne sert à rien : il ferait poser une
    # question dont la réponse ne change aucune conclusion.
    utilises = {e["module_site"][0] for e in ENJEUX if e.get("module_site")}
    inutiles = [c["cle"] for c in CONTEXTE
                if c["cle"] not in utilises and c["cle"] != "maturite_rse"]
    if inutiles:
        fautes.append("contexte sans effet sur aucun enjeu : %s"
                      % ", ".join(inutiles))

    for p in PERSPECTIVES:
        if p["source"] not in ("client", "donnees"):
            fautes.append("perspective %s : source inconnue" % p["cle"])
        if not p["questions"] or not p["outils"]:
            fautes.append("perspective %s : questions ou outils manquants" % p["cle"])

    # LA règle de la méthode : la perspective scientifique n'est pas remplie
    # par le client. Si elle le devenait, on recueillerait une opinion en
    # croyant recueillir une donnée, et les écarts perception/réalité —
    # l'apport central de la méthode — deviendraient indétectables.
    if _PERSP["science"]["source"] != "donnees":
        fautes.append("la perspective scientifique ne peut pas être remplie "
                      "par le client")

    # LES PISTES DE RÉPONSE : de quatre à huit par question, uniques, et
    # jamais sur la perspective scientifique — elle n'est pas remplie par le
    # client, elle n'a donc rien à lui souffler.
    for o in OUVERTES:
        p = o.get("pistes") or []
        if not (4 <= len(p) <= 8):
            fautes.append("question %s : %d piste(s), attendu 4 à 8"
                          % (o["cle"], len(p)))
        if len(set(p)) != len(p):
            fautes.append("question %s : piste en double" % o["cle"])
        for x in p:
            if not (20 <= len(x) <= 140):
                fautes.append("question %s : piste hors gabarit (%d car.)"
                              % (o["cle"], len(x)))
        if o["perspective"] == "science":
            fautes.append("question %s : la perspective scientifique ne "
                          "reçoit pas de pistes" % o["cle"])
    cles_o = [o["cle"] for o in OUVERTES]
    if len(set(cles_o)) != len(cles_o):
        fautes.append("clé de question ouverte dupliquée")
    return fautes


# Les grandeurs du moteur mobilisables comme preuve chiffrée, et où les lire.
_GRANDEURS = {
    "pue": ("energie", "pue"),
    "energie": ("energie", "energie_totale_MWh"),
    "eau_site": ("eau", "wue_site"),
    "eau_source": ("eau", "wue_source"),
    "carbone": ("carbone", "empreinte_totale_t"),
    "chaleur": ("chaleur", "erf"),
}

_FAUTES = _verifier()
if _FAUTES:
    raise RuntimeError("strategie_dd — référentiel incohérent : "
                       + " ; ".join(_FAUTES))


# ═══════════════════════════════════════════════════════════════════════════
#  6. LE QUESTIONNAIRE
# ═══════════════════════════════════════════════════════════════════════════

GROUPES_PP = [
    ("interne", "Équipes internes et partenaires du projet"),
    ("clients", "Clients hébergés, actuels et potentiels"),
    ("financeurs", "Investisseurs, prêteurs, assureurs"),
    ("riverains", "Riverains et associations locales"),
    ("collectivite", "Collectivité, élus, services instructeurs"),
    ("regulateur", "Régulateurs, gestionnaire de réseau, autorité de l'eau"),
    ("ong", "ONG, militants, presse"),
    ("secteur", "Coalitions sectorielles, concurrents, normalisateurs"),
]

_GROUPES = dict(GROUPES_PP)


def questionnaire():
    """Ce qu'on demande au client, et rien de plus.

    Trois perspectives sur quatre. La quatrième est établie par les données —
    la demander reviendrait à recueillir une opinion et à l'afficher ensuite
    comme une mesure.
    """
    return {
        "version": VERSION,
        "perspectives": [
            {k: p[k] for k in ("cle", "nom", "question", "source", "objet",
                               "questions", "outils")}
            | ({"garde": p["garde"]} if p.get("garde") else {})
            for p in PERSPECTIVES
        ],
        "ouvertes": OUVERTES,
        "contexte": CONTEXTE,
        "groupes_parties_prenantes": GROUPES_PP,
        "degres": DEGRES,
        "non_instruit": NON_INSTRUIT,
        # Les enjeux à noter, avec ce que la science en dit DÉJÀ : le client
        # note en connaissance de cause, ce qui vaut mieux qu'un formulaire
        # aveugle suivi d'une surprise à la restitution.
        "enjeux": [{
            "cle": e["cle"], "nom": e["nom"],
            "famille": e["famille"], "famille_nom": FAMILLES[e["famille"]],
            "science_dit": e["dit"],
            "outil": e["outil"],
            "piege": e["piege"],
            "a_noter": CLES_CLIENT,
        } for e in ENJEUX],
        "avertissement":
            "Ce questionnaire sert à ouvrir une étude, non à la remplacer. Il "
            "recueille des positions ; l'étude établira des mesures. Aucune "
            "conformité, aucune neutralité et aucun label ne se décernent ici.",
    }


# ═══════════════════════════════════════════════════════════════════════════
#  7. LA NOTATION
# ═══════════════════════════════════════════════════════════════════════════

def _note_client(reponses, cle_enjeu, perspective):
    """La note du client, ou None. Jamais de valeur par défaut : une absence
    de réponse ne peut pas devenir un « secondaire » silencieux."""
    bloc = (reponses.get("notes") or {}).get(cle_enjeu) or {}
    v = bloc.get(perspective)
    if v in (None, "", "nsp"):
        return None
    try:
        n = int(v)
    except (TypeError, ValueError):
        return None
    return n if n in DEGRES else None


def _note_science(enjeu, contexte):
    """Ce que les données disent, modulé par le site.

    Le niveau générique du registre est relevé quand le contexte l'exige. Il
    n'est jamais ABAISSÉ par le contexte : un bassin peu tendu ne rend pas
    l'eau sans objet, il la rend moins contraignante — et c'est l'étude qui le
    chiffrera, pas ce formulaire.
    """
    base = enjeu["science"]
    m = enjeu.get("module_site")
    motif = None
    if m:
        cle, poids = m
        rang = _RANG_CTX.get((contexte or {}).get(cle), None)
        if rang is None:
            return base, ("contexte « %s » non renseigné : le niveau reste "
                          "générique, alors que ce site pourrait le relever"
                          % _CONTEXTE[cle]["nom"])
        if rang >= 2:
            releve = min(3, base + poids * (rang - 1))
            if releve > base:
                lib = dict(_CONTEXTE[cle]["options"]).get(
                    contexte.get(cle), contexte.get(cle))
                motif = ("relevé de %d à %d : %s — %s"
                         % (base, releve, _CONTEXTE[cle]["nom"].lower(), lib))
                base = releve
    return base, motif


def _valeur_moteur(enjeu, etude):
    """La grandeur du moteur qui chiffre cet enjeu, si le profil la permet."""
    if not etude or not enjeu.get("moteur"):
        return None
    sec, champ = _GRANDEURS[enjeu["moteur"]]
    v = (etude.get(sec) or {}).get(champ)
    if not v:
        return None
    return {"nom": v["nom"], "valeur": v["valeur"], "unite": v["unite"],
            "incertitude": v.get("incertitude", "")}


def _groupes_cites(reponses, cle_enjeu):
    bloc = (reponses.get("notes") or {}).get(cle_enjeu) or {}
    g = bloc.get("groupes") or []
    return [{"cle": x, "nom": _GROUPES[x]} for x in g if x in _GROUPES]


# ── Le classement, et c'est le cœur de la méthode ──────────────────────────

VERDICTS = {
    "croisement": {
        "nom": "Au croisement des quatre perspectives",
        "dit": "Les quatre perspectives convergent. C'est ici qu'un "
               "investissement, une innovation ou une coalition produit le "
               "plus d'effet, et c'est ici que la stratégie se joue.",
    },
    "perception": {
        "nom": "Retenu par la perception",
        "dit": "Les données minorent cet enjeu, les parties prenantes le "
               "tiennent pour central. Il doit être traité : tant que "
               "l'opinion le considère comme l'enjeu principal, c'est un "
               "problème à traiter — quelle que soit l'analyse factuelle.",
    },
    "donnees": {
        "nom": "Retenu par les données",
        "dit": "Les données le donnent pour structurant et personne ne le "
               "soulève. C'est le cas le plus dangereux, parce qu'il est "
               "silencieux : il n'arrivera pas par une plainte, il arrivera "
               "par un fait.",
    },
    "raison_etre": {
        "nom": "Retenu par la raison d'être",
        "dit": "Ni les parties prenantes ni le compte de résultat ne "
               "l'imposent : l'entreprise le porte parce qu'il correspond à ce "
               "qu'elle défend. C'est une position de tête, et elle s'assume "
               "comme telle.",
    },
    "surveiller": {
        "nom": "À surveiller",
        "dit": "Significatif sur une seule perspective, sans convergence. Ne "
               "commande pas la conception aujourd'hui ; se réexamine au jalon "
               "suivant.",
    },
    "ecarte": {
        "nom": "Écarté",
        "dit": "Aucune perspective ne le porte. Il est écarté explicitement, "
               "et le motif est écrit — une exclusion non motivée est le "
               "premier point que relève un vérificateur.",
    },
    "non_instruit": {
        "nom": "Non instruit",
        "dit": "Une perspective au moins est restée sans réponse. Ce n'est ni "
               "retenu ni écarté : c'est en attente, et le document le porte "
               "comme un travail à faire.",
    },
}

# L'ordre de lecture. Les enjeux non instruits ne sont pas relégués en fin de
# document : un trou placé après les conclusions ne se lit pas.
ORDRE_VERDICTS = ["croisement", "donnees", "perception", "raison_etre",
                  "non_instruit", "surveiller", "ecarte"]


def _verdict(notes):
    """Le classement d'un enjeu, à partir de ses quatre notes.

    Les divergences ne sont pas moyennées. Une moyenne entre « les données
    disent 3 » et « personne n'en parle : 0 » donne un tiède 1,5 qui efface
    exactement l'information qu'il fallait porter.
    """
    if any(notes.get(k) is None for k in ("raison_etre", "parties_prenantes",
                                          "valeur")):
        return "non_instruit"
    re_, pp, sc, va = (notes["raison_etre"], notes["parties_prenantes"],
                       notes["science"], notes["valeur"])
    forts = sum(1 for n in (re_, pp, sc, va) if n >= 2)
    if sc >= 2 and forts >= 3:
        return "croisement"
    # Les données ET les parties prenantes au maximum : c'est une convergence
    # en substance, même si l'organisation ne l'a pas encore faite sienne. Le
    # manque d'adhésion interne est réel et il est nommé dans la tension
    # extérieur/intérieur — ce n'est pas une raison de ranger l'enjeu au plus
    # bas du document.
    if sc >= 3 and pp >= 3:
        return "croisement"
    if pp >= 3 and sc <= 1:
        return "perception"
    if sc >= 3 and pp <= 1:
        return "donnees"
    if re_ >= 3 and pp <= 1 and va <= 1:
        return "raison_etre"
    if forts >= 1:
        return "surveiller"
    return "ecarte"


MODES = {
    "investir": {
        "nom": "Investir",
        "dit": "L'enjeu est mesurable, les leviers existent et relèvent de "
               "nous. La réponse est une décision d'allocation.",
    },
    "innover": {
        "nom": "Innover",
        "dit": "L'enjeu est établi mais les solutions disponibles ne le "
               "referment pas. La réponse est un travail de conception, pas un "
               "achat.",
    },
    "coalition": {
        "nom": "Construire une coalition",
        "dit": "L'enjeu déborde le périmètre de l'entreprise : réseau, bassin, "
               "filière, chaîne d'approvisionnement. Le traiter seul revient à "
               "en porter le coût sans en obtenir l'effet.",
    },
}


def _mode(enjeu, notes, verdict):
    """Investir, innover, ou construire une coalition — la question qui suit
    immédiatement « cet enjeu est retenu »."""
    if verdict in ("ecarte", "non_instruit", "surveiller"):
        return None
    if not enjeu.get("seul", True):
        return "coalition"
    if notes["science"] >= 2 and (notes.get("valeur") or 0) >= 2:
        return "investir"
    return "innover"


# ═══════════════════════════════════════════════════════════════════════════
#  8. LES DEUX TENSIONS
# ═══════════════════════════════════════════════════════════════════════════

def _tensions(lignes):
    """Nommées pour CE projet, avec les enjeux qui les portent.

    Écrites en général — « il faut équilibrer l'intérieur et l'extérieur » —
    elles ne servent à rien. Ce qui sert, c'est de dire lesquels des vingt
    enjeux tirent de quel côté.
    """
    tire_dehors, porte_seul, ecart_p, ecart_d = [], [], [], []
    for l in lignes:
        n = l["notes"]
        if l["verdict"] == "non_instruit":
            continue
        if (n["parties_prenantes"] >= 2 or n["valeur"] >= 2) and n["raison_etre"] <= 1:
            tire_dehors.append(l)
        if n["raison_etre"] >= 3 and n["parties_prenantes"] <= 1 and n["valeur"] <= 1:
            porte_seul.append(l)
        if n["parties_prenantes"] - n["science"] >= 2:
            ecart_p.append(l)
        if n["science"] - n["parties_prenantes"] >= 2:
            ecart_d.append(l)

    def _n(ls):
        return [{"cle": x["cle"], "nom": x["nom"]} for x in ls]

    return [
        {
            "cle": "exterieur_interieur",
            "nom": "Extérieur / intérieur",
            "dit": "Sans l'extérieur, on décide dans sa bulle. Avec le seul "
                   "extérieur, on sur-réagit à la demande la plus bruyante. "
                   "Les deux positions sont tenables ; elles ne se pilotent "
                   "pas de la même façon.",
            "tire_du_dehors": _n(tire_dehors),
            "porte_de_l_interieur": _n(porte_seul),
            "lecture": _lecture_ext_int(tire_dehors, porte_seul),
        },
        {
            "cle": "perception_realite",
            "nom": "Perception / réalité",
            "dit": "Les données et l'opinion ne classent pas les enjeux dans "
                   "le même ordre. Moyenner les deux efface précisément "
                   "l'information qu'il fallait porter.",
            "opinion_devant_les_donnees": _n(ecart_p),
            "donnees_devant_l_opinion": _n(ecart_d),
            "lecture": _lecture_perception(ecart_p, ecart_d),
        },
    ]


def _lecture_ext_int(dehors, dedans):
    if not dehors and not dedans:
        return ("Aucun écart marqué : ce que le projet défend, ce que ses "
                "parties prenantes demandent et ce qui pèse sur ses résultats "
                "désignent les mêmes enjeux. C'est confortable, et cela mérite "
                "d'être vérifié : une convergence parfaite vient parfois d'un "
                "questionnaire rempli par une seule personne.")
    bouts = []
    if dehors:
        bouts.append("%d enjeu%s vous %s tirés du dehors sans adhésion interne "
                     "déclarée (%s). Ils se traiteront, mais sans conviction "
                     "ils se traiteront au minimum exigé — et cela se voit."
                     % (len(dehors), "x" if len(dehors) > 1 else "",
                        "sont" if len(dehors) > 1 else "est",
                        ", ".join(x["nom"] for x in dehors)))
    if dedans:
        bouts.append("%d enjeu%s que vous portez seuls (%s) : personne ne vous "
                     "les demande et ils ne pèsent pas encore sur vos "
                     "résultats. C'est une position de tête ; elle demande "
                     "d'être expliquée, sans quoi elle passera pour une "
                     "dépense sans objet."
                     % (len(dedans), "x" if len(dedans) > 1 else "",
                        ", ".join(x["nom"] for x in dedans)))
    return " ".join(bouts)


def _lecture_perception(devant_op, devant_don):
    if not devant_op and not devant_don:
        return ("Les données et l'opinion classent ces enjeux dans le même "
                "ordre. C'est rare : vérifiez que les parties prenantes ont "
                "réellement été consultées, et pas seulement supposées.")
    bouts = []
    if devant_op:
        bouts.append("Sur %s, l'opinion est très en avance sur ce que les "
                     "données établissent. Ce n'est pas une raison de "
                     "l'écarter : tant que l'opinion le tient pour l'enjeu "
                     "principal, c'est un problème qui doit être traité. La "
                     "réponse peut être une conception différente, une mesure "
                     "publiée, ou les deux — jamais un démenti."
                     % ", ".join(x["nom"] for x in devant_op))
    if devant_don:
        bouts.append("Sur %s, les données sont très en avance sur l'opinion. "
                     "C'est le cas le plus dangereux, parce qu'il est "
                     "silencieux : rien ne viendra vous le rappeler avant que "
                     "le fait ne se produise, et il sera alors trop tard pour "
                     "le traiter à la conception."
                     % ", ".join(x["nom"] for x in devant_don))
    return " ".join(bouts)


# ═══════════════════════════════════════════════════════════════════════════
#  9. LA STRATÉGIE
# ═══════════════════════════════════════════════════════════════════════════

# Au-delà de ce nombre d'enjeux retenus, on le dit. Ce n'est pas un plafond
# imposé — c'est le seuil au-delà duquel l'expérience montre que la stratégie
# cesse d'être un arbitrage pour devenir une liste, et que chaque partie
# prenante tire l'entreprise de son côté.
SEUIL_DISPERSION = 8


def strategie(reponses, profil=None):
    """Le livrable, calculé depuis les réponses du questionnaire.

    `reponses` porte : identite, contexte, ouvertes, notes.
    `profil` est le profil technique du moteur, facultatif : renseigné, il
    chiffre ce qui peut l'être dès l'ouverture de l'étude.
    """
    reponses = dict(reponses or {})
    contexte = reponses.get("contexte") or {}
    etude = None
    if profil and profil.get("puissance_it_kw"):
        try:
            etude = D.etude(profil)
        except Exception:
            etude = None

    lignes = []
    for e in ENJEUX:
        sc, motif = _note_science(e, contexte)
        notes = {"science": sc}
        for k in CLES_CLIENT:
            notes[k] = _note_client(reponses, e["cle"], k)
        v = _verdict(notes)
        lignes.append({
            "cle": e["cle"], "nom": e["nom"],
            "famille": e["famille"], "famille_nom": FAMILLES[e["famille"]],
            "dit": e["dit"], "outil": e["outil"], "piege": e["piege"],
            "seul": e.get("seul", True),
            "notes": notes,
            "science_motif": motif,
            "chiffre": _valeur_moteur(e, etude),
            "groupes": _groupes_cites(reponses, e["cle"]),
            "verdict": v, "verdict_nom": VERDICTS[v]["nom"],
            "mode": _mode(e, notes, v),
            "manquantes": [_PERSP[k]["nom"] for k in CLES_CLIENT
                           if notes[k] is None],
        })

    par_verdict = {v: [l for l in lignes if l["verdict"] == v]
                   for v in VERDICTS}
    retenus = [l for l in lignes
               if l["verdict"] in ("croisement", "perception", "donnees",
                                   "raison_etre")]

    contexte_lu = []
    for c in CONTEXTE:
        val = contexte.get(c["cle"])
        contexte_lu.append({
            "cle": c["cle"], "nom": c["nom"], "pourquoi": c["pourquoi"],
            "valeur": val,
            "libelle": dict(c["options"]).get(val) if val else None,
            "renseigne": bool(val),
        })

    return {
        "version": VERSION,
        "version_moteur": D.VERSION,
        "identite": {
            "projet": str((reponses.get("identite") or {}).get("projet") or "")[:160],
            "organisation": str((reponses.get("identite") or {}).get("organisation") or "")[:160],
            "site": str((reponses.get("identite") or {}).get("site") or "")[:160],
        },
        "ouvertes": {k: str(v)[:4000] for k, v in
                     (reponses.get("ouvertes") or {}).items() if v},
        "contexte": contexte_lu,
        "profil_chiffre": bool(etude),
        "lignes": lignes,
        "par_verdict": par_verdict,
        "ordre_verdicts": ORDRE_VERDICTS,
        "verdicts": VERDICTS,
        "modes": MODES,
        "retenus": retenus,
        "tensions": _tensions(lignes),
        "programme": _programme(retenus, par_verdict["non_instruit"]),
        "alertes": _alertes(lignes, retenus, par_verdict, contexte_lu, reponses),
        "perspectives": [{k: p[k] for k in ("cle", "nom", "question", "objet",
                                            "source", "outils")}
                         for p in PERSPECTIVES],
        "avertissement":
            "Ce document ouvre une étude ; il ne la remplace pas. Les positions "
            "recueillies ici seront confrontées à des mesures, et certaines ne "
            "survivront pas. Il ne décerne aucune conformité, aucune "
            "neutralité et aucun label : ces qualifications se constatent sur "
            "dossier complet par un vérificateur accrédité.",
    }


def _programme(retenus, non_instruits):
    """Ce que l'étude devra produire, enjeu par enjeu. C'est le lien entre le
    document d'ouverture et le travail d'ingénierie qui suit — sans lui, le
    livrable reste une déclaration."""
    travaux = []
    for l in retenus:
        travaux.append({"cle": l["cle"], "nom": l["nom"], "outil": l["outil"],
                        "motif": l["verdict_nom"],
                        "mode": l["mode"],
                        "mode_nom": MODES[l["mode"]]["nom"] if l["mode"] else None})
    for l in non_instruits:
        travaux.append({"cle": l["cle"], "nom": l["nom"],
                        "outil": "Instruire les perspectives manquantes : "
                                 + ", ".join(l["manquantes"]),
                        "motif": "Non instruit", "mode": None,
                        "mode_nom": None})
    return travaux


def _alertes(lignes, retenus, par_verdict, contexte_lu, reponses):
    """Ce qui doit être dit au lecteur avant qu'il ne se félicite du résultat."""
    a = []
    n_ni = len(par_verdict["non_instruit"])
    if n_ni:
        a.append({
            "gravite": "haute",
            "titre": "%d enjeu%s non instruit%s" % (n_ni, "x" if n_ni > 1 else "",
                                                    "s" if n_ni > 1 else ""),
            "dit": "Ils ne sont ni retenus ni écartés. Un enjeu sans réponse "
                   "n'est pas un enjeu mineur : c'est un enjeu qu'on n'a pas "
                   "regardé, et il reste au document jusqu'à ce qu'il en "
                   "reçoive une.",
        })
    if len(retenus) > SEUIL_DISPERSION:
        a.append({
            "gravite": "haute",
            "titre": "%d enjeux retenus : risque de dispersion" % len(retenus),
            "dit": "Au-delà de huit, une stratégie cesse d'être un arbitrage "
                   "pour devenir une liste. Chaque partie prenante tire alors "
                   "le projet de son côté, et l'effet involontaire est la "
                   "dispersion. Reprenez les notes : sur quels enjeux "
                   "acceptez-vous de ne PAS être en tête ?",
        })
    if not retenus:
        a.append({
            "gravite": "haute",
            "titre": "Aucun enjeu retenu",
            "dit": "Aucun enjeu n'atteint le seuil de convergence. Soit le "
                   "questionnaire a été rempli trop prudemment, soit le projet "
                   "n'a pas encore de stratégie — dans les deux cas, le "
                   "document ne peut pas conclure à votre place.",
        })
    mis_de_cote = par_verdict["ecarte"] + par_verdict["surveiller"]
    if lignes and not mis_de_cote:
        a.append({
            "gravite": "moyenne",
            "titre": "Aucun enjeu écarté ni mis en surveillance",
            "dit": "Une stratégie qui ne met rien de côté n'a pas encore "
                   "arbitré. Savoir dire sur quels sujets on ne se focalisera "
                   "pas est la moitié difficile de l'exercice, et c'est elle "
                   "qui rend le reste crédible.",
        })
    manquants = [c["nom"] for c in contexte_lu if not c["renseigne"]]
    if manquants:
        a.append({
            "gravite": "moyenne",
            "titre": "Contexte de site incomplet",
            "dit": "Non renseigné : %s. Les enjeux qui en dépendent restent au "
                   "niveau générique — donc probablement sous-évalués pour ce "
                   "site précis." % ", ".join(manquants),
        })
    vides = [o["cle"] for o in questionnaire()["ouvertes"]
             if not (reponses.get("ouvertes") or {}).get(o["cle"])]
    if len(vides) >= 4:
        a.append({
            "gravite": "moyenne",
            "titre": "La raison d'être n'est pas formulée",
            "dit": "La plupart des questions ouvertes sont restées vides. Les "
                   "notes chiffrées se calculent quand même, mais un document "
                   "de stratégie qui ne dit pas ce que l'entreprise défend "
                   "n'est qu'un tableau de priorités.",
        })
    return a


# ═══════════════════════════════════════════════════════════════════════════
#  10. LE LIVRABLE RÉDIGÉ
# ═══════════════════════════════════════════════════════════════════════════

def markdown(s):
    """Le document, prêt à exporter. L'ordre des chapitres est celui de la
    méthode : on dit ce qu'on défend, ce qu'on entend, ce qu'on mesure et ce
    qu'on gagne AVANT de conclure. Placer la conclusion en tête ferait lire les
    quatre perspectives comme sa justification."""
    ident = s["identite"]
    L = []
    A = L.append

    titre = ident["projet"] or "Centre de données"
    A("# Stratégie de développement durable — %s" % titre)
    if ident["organisation"]:
        A("")
        A("**Organisation :** %s" % ident["organisation"])
    if ident["site"]:
        A("**Site :** %s" % ident["site"])
    A("")
    A("*Document d'ouverture d'étude — méthode des quatre perspectives.*")
    A("")
    A("## Ce que ce document est, et ce qu'il n'est pas")
    A("")
    A(s["avertissement"])
    A("")
    A("La méthode croise quatre perspectives : ce que le projet **défend**, ce "
      "que ses **parties prenantes** disent, ce que les **données** "
      "établissent, et ce qui affecte ses **résultats**. Trois d'entre elles "
      "ont été renseignées par vos réponses. La quatrième — la science — ne "
      "vous a pas été demandée : la recueillir comme une opinion aurait rendu "
      "indétectables les écarts entre perception et réalité, qui sont "
      "précisément l'apport de la méthode.")

    # 1. Raison d'être
    A("")
    A("## 1. Ce que nous défendons")
    A("")
    ouv = s["ouvertes"]
    dit = False
    for cle, intitule in [
            ("raison_etre_texte", "Pourquoi ce centre de données existe"),
            ("valeurs_texte", "Les valeurs qui définissent notre manière de faire"),
            ("vision_texte", "La vision"),
            ("engagements_texte", "Les engagements déjà pris")]:
        if ouv.get(cle):
            A("**%s.** %s" % (intitule, ouv[cle]))
            A("")
            dit = True
    if not dit:
        A("*Non formulé. Les priorités qui suivent restent valables, mais elles "
          "ne sont rattachées à aucune intention déclarée — et une stratégie "
          "sans intention se renégocie à chaque arbitrage.*")
        A("")

    # 2. Parties prenantes
    A("## 2. Ce que les parties prenantes nous disent")
    A("")
    if ouv.get("ecoute_texte"):
        A("**Nos modes d'écoute.** %s" % ouv["ecoute_texte"])
        A("")
    cites = [l for l in s["lignes"] if l["groupes"]]
    if cites:
        A("Les enjeux portés, et par qui :")
        A("")
        for l in cites:
            A("- **%s** — %s" % (l["nom"],
                                 ", ".join(g["nom"] for g in l["groupes"])))
        A("")
    else:
        A("*Aucun porteur n'a été nommé enjeu par enjeu. Une préoccupation sans "
          "porteur identifié ne se traite pas : on ne sait ni à qui répondre, "
          "ni ce qui compterait comme réponse.*")
        A("")

    # 3. Science
    A("## 3. Ce que les données disent")
    A("")
    A("Les niveaux ci-dessous viennent du registre d'enjeux et du contexte de "
      "site que vous avez décrit. Ils ne sont pas des mesures : ils disent où "
      "les mesures devront être faites.")
    A("")
    for c in s["contexte"]:
        A("- **%s :** %s" % (c["nom"], c["libelle"] or "*non renseigné*"))
    A("")
    releves = [l for l in s["lignes"] if l["science_motif"]]
    if releves:
        A("Ce que ce site change par rapport au cas générique :")
        A("")
        for l in releves:
            A("- **%s** — %s" % (l["nom"], l["science_motif"]))
        A("")
    if s["profil_chiffre"]:
        chiffres = [l for l in s["lignes"] if l["chiffre"]]
        if chiffres:
            A("Ce que le moteur chiffre dès aujourd'hui, sous réserve des "
              "incertitudes portées :")
            A("")
            for l in chiffres:
                c = l["chiffre"]
                # Le nombre passe par le formateur du MOTEUR : une virgule
                # oubliée dans un livrable le fait passer pour une traduction
                # automatique, et c'est ce qu'un évaluateur voit avant le fond.
                A("- **%s** — %s : %s %s%s"
                  % (l["nom"], c["nom"], D.fr(c["valeur"]), c["unite"],
                     (" · " + c["incertitude"]) if c["incertitude"] else ""))
            A("")

    # 4. Valeur commerciale
    A("## 4. Ce qui affecte nos résultats")
    A("")
    if ouv.get("clients_payer_texte"):
        A("**Ce que nos clients sont prêts à payer.** %s"
          % ouv["clients_payer_texte"])
        A("")
    if ouv.get("intangible_texte"):
        A("**La valeur intangible visée.** %s" % ouv["intangible_texte"])
        A("")
    forts = [l for l in s["lignes"] if (l["notes"]["valeur"] or 0) >= 2]
    if forts:
        A("Enjeux à effet significatif ou structurant sur les résultats : %s."
          % ", ".join(l["nom"] for l in forts))
        A("")

    # 5. Tensions
    A("## 5. Les deux tensions, nommées pour ce projet")
    A("")
    for t in s["tensions"]:
        A("### %s" % t["nom"])
        A("")
        A(t["dit"])
        A("")
        A(t["lecture"])
        A("")

    # 6. Matérialité
    A("## 6. La matérialité au croisement des quatre perspectives")
    A("")
    if not s["retenus"]:
        A("*Aucun enjeu ne réunit les conditions de convergence. Voir les "
          "alertes en fin de document.*")
        A("")
    for v in s["ordre_verdicts"]:
        if v in ("ecarte", "surveiller", "non_instruit"):
            continue
        groupe = s["par_verdict"].get(v) or []
        if not groupe:
            continue
        A("### %s" % s["verdicts"][v]["nom"])
        A("")
        A("*%s*" % s["verdicts"][v]["dit"])
        A("")
        for l in groupe:
            mode = (" — **%s.** %s" % (s["modes"][l["mode"]]["nom"],
                                       s["modes"][l["mode"]]["dit"])
                    if l["mode"] else "")
            A("**%s** (%s)%s" % (l["nom"], l["famille_nom"], mode))
            A("")
            A("%s" % l["dit"])
            A("")
            A("*Le piège :* %s" % l["piege"])
            A("")
            A("*Outil de l'étude :* %s" % l["outil"])
            A("")

    # 7. Écarté et surveillé
    A("## 7. Ce que nous écartons, et ce que nous surveillons")
    A("")
    ecartes = s["par_verdict"].get("ecarte") or []
    if ecartes:
        A("**Écartés.** Aucune des quatre perspectives ne les porte. Cet "
          "arbitrage est explicite : il pourra être rouvert, mais il ne se "
          "sera pas fait par omission.")
        A("")
        for l in ecartes:
            A("- **%s** (%s) — %s" % (l["nom"], l["famille_nom"], l["dit"]))
        A("")
    else:
        A("*Aucun enjeu écarté. Une stratégie qui n'écarte rien n'a pas encore "
          "arbitré.*")
        A("")
    surv = s["par_verdict"].get("surveiller") or []
    if surv:
        A("**À surveiller.** Significatifs sur une seule perspective, sans "
          "convergence. Ils se réexaminent au jalon suivant : %s."
          % ", ".join(l["nom"] for l in surv))
        A("")

    # 8. Non instruit
    ni = s["par_verdict"].get("non_instruit") or []
    A("## 8. Ce qui n'a pas été instruit")
    A("")
    if ni:
        A("Ces enjeux ne sont ni retenus ni écartés : personne ne les a "
          "regardés. Ils figurent ici, et non en annexe, parce qu'un trou "
          "placé après les conclusions ne se lit pas.")
        A("")
        for l in ni:
            A("- **%s** — perspectives manquantes : %s"
              % (l["nom"], ", ".join(l["manquantes"])))
        A("")
    else:
        A("Toutes les perspectives ont été renseignées pour tous les enjeux du "
          "registre.")
        A("")

    # 9. Programme d'étude
    A("## 9. Le programme d'étude qui en découle")
    A("")
    A("Chaque enjeu retenu appelle un outil, et chaque outil appelle une "
      "production datée. C'est ce qui distingue une stratégie d'une "
      "déclaration d'intention.")
    A("")
    for t in s["programme"]:
        A("- **%s** — %s%s · *%s*"
          % (t["nom"], t["outil"],
             (" · " + t["mode_nom"]) if t["mode_nom"] else "", t["motif"]))
    A("")

    # 10. Alertes
    if s["alertes"]:
        A("## 10. Ce qu'il faut lire avant de se féliciter du résultat")
        A("")
        for al in s["alertes"]:
            A("**%s.** %s" % (al["titre"], al["dit"]))
            A("")

    A("---")
    A("")
    A("*Méthode des quatre perspectives, appliquée aux centres de données. "
      "Référentiel strategie_dd v%s ; moteur de calcul v%s. Les niveaux "
      "scientifiques sont établis par le registre et le contexte de site "
      "déclaré ; ils seront remplacés par les mesures de l'étude.*"
      % (s["version"], s["version_moteur"]))
    return "\n".join(L)


def sante():
    par_famille = {}
    for e in ENJEUX:
        par_famille[e["famille"]] = par_famille.get(e["famille"], 0) + 1
    return {"module": "strategie_dd", "version": VERSION,
            "perspectives": len(PERSPECTIVES),
            "remplies_par_le_client": len(CLES_CLIENT),
            "enjeux": len(ENJEUX), "par_famille": par_famille,
            "enjeux_hors_perimetre_seul": sum(1 for e in ENJEUX
                                              if not e.get("seul", True)),
            "enjeux_chiffres_par_le_moteur": sum(1 for e in ENJEUX
                                                 if e.get("moteur")),
            "contexte": len(CONTEXTE),
            "problemes": _verifier()}
