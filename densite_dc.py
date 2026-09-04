# -*- coding: utf-8 -*-
"""Ce que la densité par baie impose au bâtiment, et ce qu'elle interdit.

CE QUE CE MODULE EST. Le croisement de deux sujets que les dossiers traitent
séparément : la DENSITÉ (combien de kilowatts dans une baie) et la STRUCTURE
(ce que le plancher, la trame et les réservations peuvent porter). Il calcule,
pour une densité donnée : quelles familles de diffusion restent possibles,
quelle charge la baie applique au plancher et si celui-ci la tient, quelle
section il faut à l'eau et à l'air pour évacuer la même chaleur, et quelle
réserve de charge il faut spécifier avant que les poutrelles ne soient
fabriquées.

POURQUOI IL EXISTE. On est passé de baies à 1–2 kW à 130, 150 voire 300 kW
selon les architectures d'accélérateurs poussées par les fabricants. Le réflexe
est de traiter cela comme une question de froid — et c'est faux à deux titres.

  · D'abord parce que le froid n'est plus la contrainte qui mord en premier.
    Au-delà d'une centaine de kilowatts par baie, la boucle d'eau se
    dimensionne sans difficulté ; c'est le PLANCHER qui cède, très en amont.
    Une baie d'accélérateurs pèse près d'une tonne et demie sur moins d'un
    mètre carré d'emprise nue, quand une salle informatique courante est
    dimensionnée pour 7,2 kPa. Le calcul de ce module le montre au lieu de
    l'affirmer.

  · Ensuite parce que la conséquence n'est pas un choix d'équipement mais un
    choix de bâtiment. Passer de l'air à l'eau sur un site existant n'est pas
    un remplacement de machines : c'est une reprise de dalle, un réseau
    hydraulique jusqu'à la baie, et des réservations qui n'ont pas été
    prévues. C'est ce qui complique la rénovation de beaucoup de sites et
    reporte la pression sur la construction neuve.

CE QU'IL N'EST PAS. Ni une note de calcul de structure, ni un avis de
conception. Les plafonds de densité par famille sont des PLAGES DE CONCEPTION
du cabinet, déclarées comme telles, pas des valeurs normatives ; les capacités
de plancher sont des ordres de grandeur d'usage, pas le résultat d'un relevé
sur un bâtiment. Aucun de ces chiffres ne remplace un diagnostic de structure
par un bureau d'études, et le module le dit dans ses propres réserves.

CE QU'IL NE DEVINE PAS. La masse d'une baie n'est pas corrélée à sa puissance
par une loi : elle dépend du matériel. Si elle n'est pas déclarée, le verdict
de plancher sort « indéterminé » en NOMMANT ce qui manque, au lieu d'un chiffre
calculé sur une masse supposée. Sur ce sujet une valeur par défaut deviendrait
la réponse.

LE LIEN AVEC LES MODULES VOISINS. `technique_dc` décrit comment la chaleur
QUITTE LE SITE (groupe froid, tour, adiabatique) ; ce module décrit comment
elle QUITTE LA PUCE et traverse la salle. La distinction n'est pas scolaire :
une tour évaporative n'a pas de plafond de densité — elle refroidit ce qu'on
lui apporte —, et lui en prêter un ferait chercher une limite là où elle n'est
pas. Chaque famille de diffusion dit donc si son plafond lui appartient ou s'il
est porté par autre chose.
"""

VERSION = "2026-09-a"


# ═══════════════════════════════════════════════════════════════════════════
#  1. LES CONSTANTES DÉCLARÉES — chacune avec sa nature et sa réserve
# ═══════════════════════════════════════════════════════════════════════════
# AUCUNE N'EST NEUTRE, ET C'EST POURQUOI ELLES SONT ICI PLUTÔT QUE DANS LE
# CALCUL. Une vitesse d'air de 7 m/s au lieu de 10 change la section d'une
# gaine de moitié ; un écart de température d'eau de 10 K au lieu de 6 change
# le débit du même rapport. Écrites au fil du code, ces valeurs se seraient
# contredites d'une fonction à l'autre sans que rien ne le signale. Écrites
# ici, elles sortent AVEC le résultat : le lecteur voit sur quoi il repose.

CONSTANTES = {
    "emprise_baie_m2": {
        "nom": "Emprise au sol par baie, allées comprises",
        "valeur": 1.85, "unite": "m²",
        "nature": "hypothese_geometrique",
        "source": "Baie 600 × 1200 mm, pas de 0,60 m en rangée, profondeur "
                  "utile 2,25 m (baie + demi-allée froide 0,60 m + demi-allée "
                  "chaude 0,45 m), soit 1,35 m² ; majoration d'environ 35 % "
                  "pour les dégagements de bout de rangée, les armoires de "
                  "distribution et les poteaux.",
        "reserve": "Une salle réellement dessinée s'écarte de cette valeur. "
                   "Elle sert à convertir des kW par baie en kW par mètre "
                   "carré ; elle n'établit pas un plan de salle.",
    },
    "emprise_baie_nue_m2": {
        "nom": "Emprise nue de la baie, hors allées",
        "valeur": 0.72, "unite": "m²",
        "nature": "geometrie",
        "source": "600 mm × 1200 mm, dimensions d'encombrement courantes d'une "
                  "baie 42 U.",
        "reserve": "ELLE NE SERT PAS À COMPARER À LA CAPACITÉ EN kPa, et "
                   "c'est une correction : la charge d'exploitation d'un "
                   "plancher est une charge RÉPARTIE, moyennée sur la surface "
                   "d'influence de l'élément porteur — allées comprises, "
                   "puisque les baies ne pavent pas le sol. Rapportée à "
                   "l'emprise nue, la même masse donne une PRESSION locale, "
                   "utile pour la dalle de faux-plancher et les vérifications "
                   "ponctuelles ; la confondre avec la charge répartie ferait "
                   "sortir un refus sur des salles qui fonctionnent.",
    },
    "pieds_par_baie": {
        "nom": "Points d'appui d'une baie",
        "valeur": 4, "unite": "—",
        "nature": "geometrie",
        "source": "Quatre pieds réglables ou quatre roulettes, disposition "
                  "courante des baies 19 pouces.",
        "reserve": "La charge ne se répartit pas également entre les quatre "
                   "si la baie est chargée en haut ou si le sol n'est pas "
                   "plan. Le calcul par point est un ordre de grandeur, pas "
                   "une descente de charge.",
    },
    "g": {
        "nom": "Accélération de la pesanteur",
        "valeur": 9.80665, "unite": "m/s²",
        "nature": "physique",
        "source": "Valeur normale conventionnelle.",
        "reserve": None,
    },
    "cp_eau": {
        "nom": "Chaleur massique de l'eau",
        "valeur": 4.18, "unite": "kJ/(kg·K)",
        "nature": "physique",
        "source": "Eau liquide autour de 20–40 °C.",
        "reserve": "Une eau glycolée descend vers 3,6 kJ/(kg·K) et demande "
                   "donc plus de débit à écart égal.",
    },
    "rho_eau": {
        "nom": "Masse volumique de l'eau",
        "valeur": 1000.0, "unite": "kg/m³",
        "nature": "physique",
        "source": "Eau douce liquide aux températures d'une boucle de "
                  "refroidissement, où elle varie de moins de un pour cent "
                  "entre 20 et 60 °C.",
        "reserve": "Un mélange eau-glycol est plus dense d'environ 5 % à 30 % "
                   "de glycol — l'écart joue sur le débit masse, pas sur la "
                   "section, qui se calcule sur le débit volume.",
    },
    "cp_air": {
        "nom": "Chaleur massique de l'air",
        "valeur": 1.006, "unite": "kJ/(kg·K)",
        "nature": "physique", "source": "Air sec aux conditions de salle.",
        "reserve": None,
    },
    "rho_air": {
        "nom": "Masse volumique de l'air",
        "valeur": 1.2, "unite": "kg/m³",
        "nature": "physique",
        "source": "Air à environ 20 °C sous pression atmosphérique.",
        "reserve": "L'air de reprise est plus chaud et donc plus léger : à "
                   "35 °C la masse volumique tombe vers 1,14 kg/m³, ce qui "
                   "AUGMENTE encore le volume à déplacer.",
    },
    "delta_t_eau": {
        "nom": "Écart de température retenu côté eau",
        "valeur": 10.0, "unite": "K",
        "nature": "plage_de_conception",
        "source": "Écart courant d'une boucle de plaques froides (par exemple "
                  "40/50 °C). Élargir l'écart réduit le débit à puissance "
                  "égale.",
        "reserve": "C'est un choix de projet, pas une donnée. Il se négocie "
                   "avec le constructeur du serveur, qui impose une "
                   "température d'entrée maximale.",
    },
    "delta_t_air": {
        "nom": "Écart de température retenu côté air",
        "valeur": 12.0, "unite": "K",
        "nature": "plage_de_conception",
        "source": "Écart soufflage/reprise courant en allée confinée.",
        "reserve": "Un écart plus large réduit le débit mais relève la "
                   "température de reprise, ce que la classe ASHRAE admise "
                   "par le matériel borne.",
    },
    "vitesse_eau": {
        "nom": "Vitesse retenue dans la canalisation",
        "valeur": 2.0, "unite": "m/s",
        "nature": "plage_de_conception",
        "source": "Vitesse d'usage en réseau bouclé : au-delà, les pertes de "
                  "charge et le bruit deviennent dimensionnants.",
        "reserve": None,
    },
    "vitesse_air": {
        "nom": "Vitesse retenue dans la gaine",
        "valeur": 7.0, "unite": "m/s",
        "nature": "plage_de_conception",
        "source": "Vitesse déjà élevée pour une gaine principale de bâtiment "
                  "tertiaire ; la retenir joue EN FAVEUR de l'air dans la "
                  "comparaison qui suit.",
        "reserve": "Descendre à 5 m/s pour le bruit multiplierait la section "
                   "d'air par 1,4 sans rien changer côté eau.",
    },
}


def _c(cle):
    return CONSTANTES[cle]["valeur"]


# ═══════════════════════════════════════════════════════════════════════════
#  2. LES RÉGIMES DE DENSITÉ — quatre points de repère, pas une échelle
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE CETTE TABLE SERT, ET CE QU'ELLE NE SERT PAS. Elle donne quatre baies
# réelles avec leur puissance ET leur masse, parce que c'est le couple qui
# décide et qu'aucune loi ne relie l'une à l'autre : une baie de stockage est
# lourde et peu consommatrice, une baie d'accélérateurs est les deux. Elle ne
# sert PAS à interpoler — une densité intermédiaire n'a pas la masse moyenne
# des deux régimes qui l'encadrent, elle a celle du matériel qu'on y met.
#
# LA MASSE EST LA GRANDEUR QUI MANQUE DANS LES DOSSIERS. On trouve partout la
# puissance par baie ; la masse n'apparaît qu'au moment où le bureau de
# structure la demande, c'est-à-dire trop tard pour changer de bâtiment.

REGIMES = {
    "classique": {
        "nom": "Baie classique d'hébergement",
        "kw_baie": 5.0,
        "masse_baie_kg": 700,
        "quoi": "Serveurs généralistes, stockage, réseau. C'est le régime pour "
                "lequel la quasi-totalité du parc existant a été construite.",
        "source_masse": "Ordre de grandeur d'une baie 42 U garnie de serveurs "
                        "1U et 2U, hors baies de stockage denses.",
    },
    "dense_air": {
        "nom": "Baie dense refroidie à l'air",
        "kw_baie": 30.0,
        "masse_baie_kg": 1200,
        "quoi": "Le haut de ce que l'air sait faire, et seulement en allée "
                "strictement confinée avec un écart de température élargi. "
                "Au-delà, ce n'est plus une question de moyens.",
        "source_masse": "Baie pleine de serveurs biprocesseurs denses, "
                        "alimentations et brassage compris.",
    },
    "ia_accelerateurs": {
        "nom": "Baie d'accélérateurs, génération en déploiement",
        "kw_baie": 130.0,
        "masse_baie_kg": 1360,
        "quoi": "Grappe d'accélérateurs interconnectés livrée en armoire "
                "complète, refroidie par plaques froides. La baie n'est plus "
                "un contenant : c'est une machine unique qu'on ne dégarnit "
                "pas pour la déplacer.",
        "source_masse": "Ordre de grandeur publié pour les armoires "
                        "d'accélérateurs interconnectés de cette génération, "
                        "soit environ 1,4 tonne prête à poser.",
    },
    "ia_suivante": {
        "nom": "Baie d'accélérateurs, génération annoncée",
        "kw_baie": 300.0,
        "masse_baie_kg": 2000,
        "quoi": "Densité annoncée par les feuilles de route des fabricants. "
                "Elle sert ici de BORNE DE CONCEPTION : un bâtiment livré "
                "dans trois ans l'accueillera ou ne l'accueillera pas, et "
                "cela se décide aujourd'hui.",
        "source_masse": "HYPOTHÈSE DU CABINET, extrapolée du régime précédent "
                        "à raison de la masse ajoutée par le refroidissement "
                        "et la distribution électrique. Aucune baie de série "
                        "n'est disponible pour la vérifier.",
    },
}


# L'ORDRE EST UNE DONNÉE. Il porte la montée en densité, et c'est lui qui rend
# lisible « le régime le plus proche » dans un formulaire. Un dictionnaire ne
# garantit pas cet ordre à la relecture ; cette liste, si.
ORDRE_REGIMES = ["classique", "dense_air", "ia_accelerateurs", "ia_suivante"]


# ═══════════════════════════════════════════════════════════════════════════
#  3. LES FAMILLES DE DIFFUSION, ET CE QUI PORTE LEUR PLAFOND
# ═══════════════════════════════════════════════════════════════════════════
# LA DIFFUSION N'EST PAS LE REFROIDISSEMENT, et les confondre est l'erreur la
# plus coûteuse de ce sujet. `technique_dc.MODES_REFROIDISSEMENT` dit comment
# la chaleur QUITTE LE SITE ; cette table dit comment elle quitte la puce et
# traverse la salle. Une tour évaporative refroidit indifféremment une salle à
# 5 ou à 300 kW par baie : le plafond n'est pas chez elle, il est chez le
# terminal. Une famille qui n'a pas de plafond propre le DIT et nomme ce qui le
# porte, plutôt que d'afficher une limite empruntée.
#
# LES PLAFONDS SONT DES PLAGES DE CONCEPTION DU CABINET. Ils ne sont pas
# normatifs, et un constructeur produira toujours un cas qui les dépasse de
# quelques kilowatts en conditions choisies. Ce qu'ils mesurent est l'endroit
# où la famille cesse d'être RAISONNABLE — où la tenir demande des moyens qui
# coûtent plus que la famille suivante.

DIFFUSION = {
    "air_libre": {
        "nom": "Air soufflé, salle non confinée",
        "plafond_kw_baie": 5.0,
        "plafond_porte_par": None,
        "principe": "Air froid soufflé en salle ou par faux-plancher, reprise "
                    "libre en volume. Rien ne sépare l'air chaud de l'air "
                    "froid : ils se mélangent, et le mélange est la limite.",
        "ce_qui_plafonne": "Le recyclage d'air chaud en tête de baie. Au-delà "
                           "de quelques kilowatts, la température d'entrée du "
                           "haut de baie décroche de celle du bas, et "
                           "souffler plus froid ne fait qu'aggraver le "
                           "mélange.",
        "renovation": "C'est l'état de la majorité des salles existantes.",
    },
    "air_confine": {
        "nom": "Air soufflé, allée confinée",
        "plafond_kw_baie": 15.0,
        "plafond_porte_par": None,
        "principe": "L'allée froide ou l'allée chaude est fermée : l'air ne se "
                    "mélange plus, et tout le débit traverse les serveurs.",
        "ce_qui_plafonne": "Le débit d'air disponible par baie, donc la "
                           "section de plancher technique et de plénum. On "
                           "gagne en confinant ce qu'on ne peut plus gagner "
                           "en soufflant.",
        "renovation": "Confiner une salle existante est l'intervention la "
                      "moins coûteuse de cette table : cloisons, portes de "
                      "bout d'allée, obturateurs. Elle se fait salle occupée.",
    },
    "air_confine_haut": {
        "nom": "Air soufflé, confinement et écart élargi — la limite de l'air",
        "plafond_kw_baie": 30.0,
        "plafond_porte_par": None,
        "principe": "Confinement strict, écart de température porté au maximum "
                    "que la classe ASHRAE du matériel admet, plénum et faux-"
                    "plancher dimensionnés pour le débit.",
        "ce_qui_plafonne": "La physique de l'air, et non les moyens : à "
                           "puissance égale l'air demande une section de "
                           "passage sans commune mesure avec celle de l'eau — "
                           "le calcul de ce module la chiffre. Au-delà, la "
                           "gaine ne tient plus dans le bâtiment.",
        "renovation": "Atteindre ce niveau sur un site existant suppose de "
                      "reprendre le plénum et souvent la hauteur sous dalle. "
                      "Ce n'est plus une adaptation, c'est un chantier.",
    },
    "porte_arriere": {
        "nom": "Échangeur en porte arrière",
        "plafond_kw_baie": 60.0,
        "plafond_porte_par": None,
        "principe": "Une batterie à eau montée sur la porte arrière de la baie "
                    "reprend l'air chaud à la sortie des serveurs. La salle "
                    "reste à l'air, mais la chaleur part en eau dès la baie.",
        "ce_qui_plafonne": "La surface d'échange que la porte peut porter et "
                           "le débit d'air que les ventilateurs des serveurs "
                           "fournissent — c'est encore l'air qui traverse le "
                           "serveur.",
        "renovation": "LE SEUL BARREAU INTERMÉDIAIRE, et c'est ce qui en fait "
                      "l'option de rénovation la plus fréquente : il amène "
                      "l'eau jusqu'à la baie sans toucher au serveur, donc "
                      "sans changer de parc informatique.",
    },
    "dlc": {
        "nom": "Plaques froides sur les composants (DLC)",
        "plafond_kw_baie": None,
        "plafond_porte_par": "plancher, distribution électrique et unité de "
                             "distribution de fluide (CDU) — aucun plafond de "
                             "refroidissement n'apparaît dans les plages "
                             "déployées aujourd'hui",
        "principe": "L'eau tempérée arrive au contact des composants les plus "
                    "chauds et capte l'essentiel de leur chaleur. Une part "
                    "résiduelle, de l'ordre de 20 à 30 %, reste évacuée par "
                    "l'air de la salle.",
        "ce_qui_plafonne": "RIEN, du côté du froid — et c'est le point de "
                           "bascule de tout ce module. Passé cette famille, "
                           "la contrainte qui mord n'est plus thermique : "
                           "c'est la charge au sol, l'ampérage à amener et la "
                           "place de la CDU.",
        "renovation": "Suppose une boucle hydraulique neuve jusqu'à la baie, "
                      "une détection de fuite, une CDU, et un parc "
                      "informatique compatible. Ce n'est pas une adaptation "
                      "de site : c'est un autre site dans le même bâtiment.",
    },
    "immersion": {
        "nom": "Immersion en bain diélectrique",
        "plafond_kw_baie": None,
        "plafond_porte_par": "plancher et exploitation — la masse du bac "
                             "rempli devient le sujet avant la thermique",
        "principe": "Les cartes baignent dans un fluide diélectrique qui capte "
                    "la quasi-totalité de la chaleur. Plus de flux d'air à "
                    "organiser en salle.",
        "ce_qui_plafonne": "La manutention et la masse : un bac rempli change "
                           "l'ordre de grandeur de la charge au sol, et la "
                           "maintenance d'une carte immergée n'est pas celle "
                           "d'un serveur en baie.",
        "renovation": "Reste minoritaire en exploitation. Le plancher est "
                      "presque toujours le premier obstacle.",
    },
}

# L'ORDRE EST UNE DONNÉE, PAS UN AFFICHAGE. Il porte la progression de la
# contrainte — air libre, air confiné, air poussé, eau à la baie, eau au
# composant, immersion — et c'est lui qui permet de dire « la famille suivante »
# sans la nommer. Un dictionnaire ne garantit pas cet ordre à la relecture ;
# cette liste, si.
ORDRE_DIFFUSION = ["air_libre", "air_confine", "air_confine_haut",
                   "porte_arriere", "dlc", "immersion"]

DIFFUSION_SOURCE = (
    "PLAGES DE CONCEPTION DU CABINET, PAS DES VALEURS NORMATIVES. Aucun texte "
    "ne fixe la densité au-delà de laquelle une famille cesse d'être tenable ; "
    "ces plafonds situent l'endroit où la tenir coûte plus cher que la famille "
    "suivante. Un cas particulier les dépassera toujours de quelques "
    "kilowatts. Ce qu'ils permettent de trancher, c'est l'écart d'un facteur "
    "quatre ou dix — pas l'écart de dix pour cent.")


# ═══════════════════════════════════════════════════════════════════════════
#  4. LES PLANCHERS — ce que le bâtiment porte
# ═══════════════════════════════════════════════════════════════════════════
# DEUX CRITÈRES, ET LE SECOND EST CELUI QUI TOMBE EN PREMIER. La charge
# répartie (kPa, donc kg/m²) est celle que tout le monde cite ; la charge
# PONCTUELLE sous un pied est celle qui perce un faux-plancher. Une baie de
# 1 360 kg sur quatre pieds applique 340 kg par point, quand une dalle de faux-
# plancher courante est donnée pour une charge ponctuelle de service de l'ordre
# de 250 à 450 kg selon la série. Le module rend les deux, parce qu'un dossier
# qui ne regarde que la charge répartie conclut « ça passe » et découvre le
# contraire le jour de la livraison.
#
# ET LA CHARGE ROULANTE EST UN TROISIÈME CRITÈRE, celui qu'on oublie toujours :
# amener une baie d'une tonne et demie jusqu'à sa place la fait rouler sur tout
# le trajet, sur des dalles qui n'ont jamais été prévues pour cela.

PLANCHERS = {
    "courant": {
        "nom": "Salle informatique courante",
        "kpa": 7.2,
        "quoi": "Dimensionnement usuel d'une salle serveurs de bâtiment "
                "tertiaire ou d'un centre de données d'hébergement classique.",
        "reserve": "Ordre de grandeur d'usage. La valeur réelle se lit sur la "
                   "note de calcul de structure du bâtiment, pas ici.",
    },
    "renforce": {
        "nom": "Salle renforcée",
        "kpa": 12.0,
        "quoi": "Salle conçue pour des baies denses ou du stockage lourd, "
                "fréquente sur les constructions récentes.",
        "reserve": "Ordre de grandeur d'usage, à confirmer bâtiment par "
                   "bâtiment.",
    },
    "lourd": {
        "nom": "Dalle lourde étudiée pour la charge",
        "kpa": 20.0,
        "quoi": "Dalle dimensionnée spécifiquement, généralement sur terre-"
                "plein ou avec une trame resserrée.",
        "reserve": "Au-delà, la charge cesse d'être un sujet de dalle et "
                   "devient un sujet de fondation.",
    },
}

# ── LE FAUX-PLANCHER, QUI CÈDE AVANT LA DALLE ─────────────────────────────
# CE QUE CE SECOND TABLEAU CORRIGE. Le premier compare une charge répartie à
# une capacité en kilopascals — c'est le critère de la DALLE. Or ce n'est
# presque jamais la dalle qui arrête une baie dense : c'est la dalle de
# faux-plancher, jugée sur une charge PONCTUELLE sous un pied. Une baie
# d'accélérateurs de 1,4 tonne sur quatre pieds applique 340 kg par point, ce
# qui est déjà au niveau de service d'un panneau courant. Sans ce tableau, le
# module aurait rendu « ça passe » sur le seul critère qui ne mord pas.
#
# LA CHARGE DE SERVICE EST LA MOITIÉ DE LA CHARGE ULTIME, usage constant du
# métier. Comparer une masse réelle à une charge ultime reviendrait à
# dimensionner sans coefficient de sécurité.
FAUX_PLANCHERS = {
    "aucun": {
        "nom": "Pas de faux-plancher — pose directe sur dalle",
        "ponctuel_service_kg": None,
        "quoi": "Distribution en chemins de câbles aériens. C'est la "
                "disposition retenue sur les salles denses récentes, et c'est "
                "précisément parce que le faux-plancher est le maillon qui "
                "cède le premier.",
        "reserve": "Le critère ponctuel ne disparaît pas : il se reporte sur "
                   "la dalle, qui l'absorbe beaucoup mieux.",
    },
    "standard": {
        "nom": "Faux-plancher courant",
        "ponctuel_service_kg": 285,
        "quoi": "Panneau de série d'une salle d'hébergement classique "
                "(environ 5,6 kN de charge ultime).",
        "reserve": "Ordre de grandeur d'usage : la classe réelle se lit sur la "
                   "fiche du fabricant, série par série.",
    },
    "renforce": {
        "nom": "Faux-plancher renforcé",
        "ponctuel_service_kg": 340,
        "quoi": "Panneau renforcé (environ 6,7 kN de charge ultime), courant "
                "sur les salles conçues pour des baies denses.",
        "reserve": "Ordre de grandeur d'usage, à confirmer sur la fiche "
                   "produit et l'état réel des vérins.",
    },
    "lourd": {
        "nom": "Faux-plancher de forte capacité",
        "ponctuel_service_kg": 455,
        "quoi": "Panneau de forte capacité (environ 8,9 kN de charge ultime), "
                "avec vérins rapprochés.",
        "reserve": "Au-delà, l'usage est d'abandonner le faux-plancher plutôt "
                   "que de le renforcer encore.",
    },
}


PLANCHERS_SOURCE = (
    "ORDRES DE GRANDEUR D'USAGE. Ces trois valeurs situent un bâtiment dans "
    "une famille ; elles ne remplacent AUCUNEMENT le diagnostic de structure "
    "qui, seul, engage. Le résultat de ce module vaut pour décider s'il faut "
    "commander ce diagnostic — pas pour s'en dispenser.")


# ═══════════════════════════════════════════════════════════════════════════
#  5. LE CALCUL
# ═══════════════════════════════════════════════════════════════════════════

def _section_fluide(kw, cp, rho, delta_t, vitesse):
    """Débit et section de passage pour évacuer `kw` avec un fluide donné.

    Une seule fonction pour l'eau et pour l'air : ce sont les mêmes équations,
    et les écrire deux fois aurait fait diverger les deux moitiés de la
    comparaison — c'est-à-dire exactement le chiffre que ce module existe pour
    produire.
    """
    debit_masse = kw / (cp * delta_t)                 # kg/s
    debit_volume = debit_masse / rho                  # m³/s
    section = debit_volume / vitesse                  # m²
    return {
        # LA SECTION EXACTE VOYAGE À CÔTÉ DE LA SECTION AFFICHABLE, et ce
        # n'est pas une coquetterie : le rapport eau/air se calculait sur la
        # valeur ARRONDIE à six décimales, et sortait 822 à 5 kW contre 824 à
        # 300 kW. Un rapport qui ne dépend que des fluides ne peut PAS varier
        # avec la densité : l'écart était un artefact de l'arrondi, et il
        # aurait discrédité la seule phrase que ce calcul existe pour dire.
        "_section_exacte": section,
        "debit_masse_kg_s": round(debit_masse, 4),
        "debit_m3_h": round(debit_volume * 3600.0, 1),
        "section_m2": round(section, 6),
        "diametre_equivalent_mm": round((4.0 * section / 3.141592653589793)
                                        ** 0.5 * 1000.0, 1),
        "cote_carre_m": round(section ** 0.5, 2),
        "delta_t_k": delta_t,
        "vitesse_m_s": vitesse,
    }


def transport(kw_baie):
    """Ce qu'il faut de section à l'eau et à l'air pour la même chaleur.

    LE RAPPORT NE DÉPEND PAS DE LA DENSITÉ, et c'est ce que le résultat doit
    faire comprendre. Il ne dépend que des fluides et des vitesses retenues :
    il vaut autant à 5 kW qu'à 300. Ce que la densité change, c'est la TAILLE
    ABSOLUE — une gaine de 22 cm ne pose de problème à personne, une gaine de
    1,13 m ne rentre pas dans un faux-plafond existant. C'est là que « la
    densité impose l'eau » cesse d'être une opinion.
    """
    eau = _section_fluide(kw_baie, _c("cp_eau"), _c("rho_eau"),
                          _c("delta_t_eau"), _c("vitesse_eau"))
    air = _section_fluide(kw_baie, _c("cp_air"), _c("rho_air"),
                          _c("delta_t_air"), _c("vitesse_air"))
    return {
        "eau": eau, "air": air,
        "rapport_sections": round(air["_section_exacte"]
                                  / eau["_section_exacte"], 0),
        "lecture": "À vitesses et écarts déclarés, l'air demande environ %d "
                   "fois la section de passage de l'eau pour évacuer la même "
                   "chaleur. Ce rapport est une propriété des deux fluides : "
                   "il est le même à toutes les densités. Ce que la densité "
                   "change, c'est que la gaine cesse de tenir dans le "
                   "bâtiment — ici %s m de côté contre %s mm de diamètre."
                   % (round(air["_section_exacte"] / eau["_section_exacte"]),
                      ("%.2f" % air["cote_carre_m"]).replace(".", ","),
                      ("%.0f" % eau["diametre_equivalent_mm"])),
    }


def diffusions(kw_baie):
    """Les familles qui tiennent cette densité, et celles qui ne la tiennent
    plus.

    L'ORDRE DÉCLARÉ EST RESPECTÉ pour que « la première famille admise » ait un
    sens : c'est celle qui coûte le moins de bâtiment, et c'est la réponse que
    cherche un lecteur qui a une densité et pas encore de projet.
    """
    admises, exclues = [], []
    for cle in ORDRE_DIFFUSION:
        v = DIFFUSION[cle]
        pl = v.get("plafond_kw_baie")
        ligne = {"cle": cle, "nom": v["nom"], "plafond_kw_baie": pl,
                 "plafond_porte_par": v.get("plafond_porte_par"),
                 "ce_qui_plafonne": v["ce_qui_plafonne"],
                 "renovation": v["renovation"]}
        if pl is None or kw_baie <= pl:
            admises.append(ligne)
        else:
            ligne["depassement"] = round(kw_baie / pl, 1)
            exclues.append(ligne)
    return {
        "admises": admises, "exclues": exclues,
        "premiere_admise": admises[0] if admises else None,
        "liquide_impose": bool(admises) and admises[0]["cle"] in ("dlc",
                                                                 "immersion"),
        "source": DIFFUSION_SOURCE,
    }


def plancher(masse_baie_kg=None, capacite_kpa=None, faux_plancher=None):
    """La charge que la baie applique, et lequel des deux critères mord.

    DEUX CRITÈRES DE NATURES DIFFÉRENTES, ET C'EST TOUT L'INTÉRÊT.

      · LA CHARGE RÉPARTIE se compare à la capacité de la DALLE, exprimée en
        kilopascals. Elle se calcule sur la surface d'INFLUENCE — allées
        comprises —, parce que les baies ne pavent pas le sol et qu'une charge
        d'exploitation est par définition moyennée. Une première version de ce
        module la calculait sous l'emprise nue : elle rendait un refus sur des
        salles d'hébergement ordinaires, qui fonctionnent. C'était faux.

      · LA CHARGE PONCTUELLE se compare à la dalle de FAUX-PLANCHER, sous un
        pied. C'est presque toujours celle-ci qui mord la première, et c'est la
        raison pour laquelle les salles denses récentes se posent directement
        sur dalle.

    LE VERDICT EST LE PLUS DÉFAVORABLE DES DEUX, et il DIT lequel. Rendre le
    meilleur ferait passer une baie que le faux-plancher n'accepte pas ;
    rendre un verdict sans dire lequel des deux le fonde enverrait reprendre
    la dalle là où il suffisait de retirer le faux-plancher.

    RIEN N'EST DEVINÉ. Sans masse déclarée, le verdict est « indéterminé » et
    NOMME ce qui manque : aucune loi ne relie la puissance d'une baie à son
    poids, et en inventer une ferait sortir un GO sur une supposition.
    """
    manques = []
    if not masse_baie_kg:
        manques.append("la masse d'une baie en ordre de marche")
    if not capacite_kpa:
        manques.append("la capacité déclarée du plancher")
    if manques:
        return {"verdict": "indetermine", "manques": manques,
                "message": "Le plancher ne peut pas être tranché : il manque "
                           + " et ".join(manques) + "."}

    influence = _c("emprise_baie_m2")
    nue = _c("emprise_baie_nue_m2")
    repartie = masse_baie_kg / influence                          # kg/m²
    pression_nue = masse_baie_kg / nue                            # kg/m²
    capacite = capacite_kpa * 1000.0 / _c("g")                    # kg/m²
    par_pied = masse_baie_kg / float(_c("pieds_par_baie"))        # kg
    taux_dalle = repartie / capacite

    fp = FAUX_PLANCHERS.get(faux_plancher or "")
    ponctuel_admis = fp.get("ponctuel_service_kg") if fp else None
    taux_fp = (par_pied / ponctuel_admis) if ponctuel_admis else None

    def _classer(t):
        return "go" if t <= 0.8 else ("limite" if t <= 1.0 else "nogo")

    v_dalle = _classer(taux_dalle)
    v_fp = _classer(taux_fp) if taux_fp is not None else None
    rang = {"go": 0, "limite": 1, "nogo": 2}
    verdict = v_dalle if v_fp is None or rang[v_dalle] >= rang[v_fp] else v_fp
    qui = ("la dalle" if (v_fp is None or rang[v_dalle] >= rang[v_fp])
           else "le faux-plancher")

    MOT = {
        "go": "La baie passe, avec de la marge sous les capacités déclarées.",
        "limite": "La baie passe sans réserve utile : un ajout d'équipement — "
                  "unité de distribution de fluide, collecteurs, batterie en "
                  "porte — fait basculer le verdict.",
        "nogo": "La baie NE PASSE PAS.",
    }
    message = MOT[verdict]
    if verdict != "go":
        message += " Le critère qui mord est %s." % qui
    if verdict == "nogo" and qui == "le faux-plancher":
        message += (" C'est la bonne nouvelle de ce verdict : retirer le "
                    "faux-plancher et distribuer en aérien est une opération "
                    "de salle, pas une reprise de structure.")
    elif verdict == "nogo":
        message += (" Ce n'est pas un sujet de refroidissement, c'est un sujet "
                    "de dalle.")

    return {
        "verdict": verdict,
        "critere_qui_mord": qui if verdict != "go" else None,
        "masse_baie_kg": masse_baie_kg,
        "message": message,
        # ── critère 1 : la dalle, en charge répartie ──────────────────────
        "dalle": {
            "verdict": v_dalle,
            "surface_influence_m2": influence,
            "charge_repartie_kg_m2": round(repartie, 0),
            "charge_repartie_kpa": round(repartie * _c("g") / 1000.0, 2),
            "capacite_kg_m2": round(capacite, 0),
            "capacite_kpa": capacite_kpa,
            "taux_occupation": round(taux_dalle, 2),
        },
        # ── critère 2 : le faux-plancher, en charge ponctuelle ────────────
        "faux_plancher": {
            "verdict": v_fp,
            "cle": faux_plancher if fp else None,
            "nom": fp["nom"] if fp else None,
            "charge_par_pied_kg": round(par_pied, 0),
            "ponctuel_admis_kg": ponctuel_admis,
            "taux_occupation": round(taux_fp, 2) if taux_fp is not None else None,
            "message": (None if fp else
                        "Le faux-plancher n'est pas déclaré : le critère qui "
                        "mord le plus souvent n'est donc PAS éprouvé ici. "
                        "%d kg par pied sont à confronter à la fiche des "
                        "dalles." % round(par_pied)),
        },
        # La pression sous l'emprise nue est rendue pour information : elle ne
        # se compare à aucune des deux capacités ci-dessus, et le dire évite
        # qu'on la reprenne comme charge répartie — ce que ce module a fait.
        "pression_sous_emprise_kg_m2": round(pression_nue, 0),
        "a_verifier": [
            "Charge roulante sur le trajet de mise en place : la baie roule du "
            "quai jusqu'à son emplacement, sur des dalles et des panneaux qui "
            "n'ont pas été dimensionnés pour cela. C'est un critère distinct "
            "de la charge statique, et il est souvent le plus contraignant.",
            "Charge d'exploitation ajoutée : unité de distribution de fluide, "
            "collecteurs, batteries en porte arrière et cheminements de "
            "fluides s'ajoutent à la baie et ne figurent pas dans sa masse "
            "constructeur.",
            "Concentration en rangée : plusieurs baies contiguës chargent la "
            "même travée. La surface d'influence retenue ici (%s m² par baie) "
            "suppose une implantation en rangées séparées par des allées."
            % ("%.2f" % influence).replace(".", ","),
        ],
        "source": PLANCHERS_SOURCE,
    }


def salle(kw_baie, masse_baie_kg=None, regime=None, capacite_kpa=None,
          plancher_cle=None, faux_plancher=None, diffusion_existante=None):
    """L'étude complète pour une densité : froid, plancher, transport,
    rénovation.

    LES QUATRE RÉSULTATS PARTENT ENSEMBLE, et c'est le point. Pris séparément,
    chacun se lit à l'avantage de la décision déjà prise : « le liquide
    s'impose » sans la charge au sol donne un projet qui achète des CDU pour
    une salle qui ne les portera pas ; la charge au sol sans le transport
    laisse croire qu'un renforcement de dalle suffirait à garder l'air.
    """
    kw_baie = float(kw_baie)
    if kw_baie <= 0:
        raise ValueError("La puissance par baie doit être strictement positive.")

    origine_masse = "declaree"
    if masse_baie_kg is None and regime in REGIMES:
        masse_baie_kg = REGIMES[regime]["masse_baie_kg"]
        origine_masse = "reprise_du_regime"
    if capacite_kpa is None and plancher_cle in PLANCHERS:
        capacite_kpa = PLANCHERS[plancher_cle]["kpa"]

    dif = diffusions(kw_baie)
    pla = plancher(masse_baie_kg, capacite_kpa, faux_plancher)
    tra = transport(kw_baie)
    emprise = _c("emprise_baie_m2")

    return {
        "version": VERSION,
        "kw_baie": kw_baie,
        "emprise_baie_m2": emprise,
        "densite_kw_m2": round(kw_baie / emprise, 1),
        "masse": {"valeur_kg": masse_baie_kg, "origine": origine_masse,
                  "regime": regime if origine_masse == "reprise_du_regime"
                  else None},
        "diffusion": dif,
        "plancher": pla,
        "transport": tra,
        "reserve_charge": reserve_de_charge(),
        "renovation": _renovation(dif, pla, diffusion_existante),
        "constantes": CONSTANTES,
    }


def _renovation(dif, pla, existante):
    """Ce que cette densité veut dire pour un site EXISTANT.

    C'est la moitié de la question posée : la densité ne complique pas la
    construction neuve, où elle se paie en conception ; elle complique la
    RÉNOVATION, où elle se heurte à un bâtiment déjà bâti. Le module distingue
    donc deux obstacles de nature différente — celui qui se lève par des
    travaux, et celui qui ne se lève pas.
    """
    cible = dif.get("premiere_admise")
    obstacles, leves = [], []

    if existante in DIFFUSION and cible:
        i_ex = ORDRE_DIFFUSION.index(existante)
        i_ci = ORDRE_DIFFUSION.index(cible["cle"])
        if i_ci > i_ex:
            franchis = ORDRE_DIFFUSION[i_ex + 1:i_ci + 1]
            obstacles.append(
                "La salle est en « %s » et cette densité demande au minimum "
                "« %s » : %d changement(s) de famille, dont %s."
                % (DIFFUSION[existante]["nom"], cible["nom"], len(franchis),
                   "le passage de l'air à l'eau jusqu'à la baie"
                   if "porte_arriere" in franchis or "dlc" in franchis
                   else "un renforcement du confinement et du plénum"))
        else:
            leves.append("La famille de diffusion en place tient déjà cette "
                         "densité : le sujet n'est pas le froid.")
    elif cible:
        obstacles.append("La famille de diffusion en place n'est pas "
                         "déclarée : l'écart à franchir ne peut pas être "
                         "mesuré, seulement la cible (« %s »)." % cible["nom"])

    if pla.get("verdict") == "nogo":
        if pla.get("critere_qui_mord") == "le faux-plancher":
            obstacles.append(
                "Le FAUX-PLANCHER ne porte pas la baie : %s kg par pied pour "
                "%s kg admis. Cet obstacle-là se lève — on retire le "
                "faux-plancher et on distribue en aérien —, et c'est une "
                "opération de salle, pas une reprise de structure."
                % (pla["faux_plancher"]["charge_par_pied_kg"],
                   pla["faux_plancher"]["ponctuel_admis_kg"]))
        else:
            obstacles.append(
                "La DALLE ne porte pas la baie (%s kg/m² répartis pour %s "
                "kg/m² déclarés). C'est l'obstacle qui ne se lève pas par un "
                "changement d'équipement : reprendre une dalle en salle "
                "occupée n'est pas une opération de rénovation ordinaire, et "
                "elle décide souvent seule de construire ailleurs."
                % (pla["dalle"]["charge_repartie_kg_m2"],
                   pla["dalle"]["capacite_kg_m2"]))
    elif pla.get("verdict") == "limite":
        obstacles.append(
            "Le plancher passe sans réserve utile — %s est à %s %% de sa "
            "capacité déclarée. Les équipements que la densité entraîne "
            "s'ajoutent après coup et feront basculer ce verdict."
            % (pla.get("critere_qui_mord") or "la dalle",
               round((pla["faux_plancher"]["taux_occupation"]
                      if pla.get("critere_qui_mord") == "le faux-plancher"
                      else pla["dalle"]["taux_occupation"]) * 100)))
    elif pla.get("verdict") == "indetermine":
        obstacles.append("Le plancher n'est pas tranché : " +
                         pla.get("message", ""))

    return {
        "cible": cible, "obstacles": obstacles, "leves": leves,
        "verdict": ("bloque" if pla.get("verdict") == "nogo"
                    else "a_etudier" if obstacles else "ouvert"),
        "note": "Ce module compare une densité à un bâtiment. Il ne dit pas "
                "si la rénovation est moins chère que la construction neuve : "
                "cela se chiffre sur l'opération, avec le coût du site, le "
                "raccordement obtenu et la valeur du délai gagné.",
    }


# ═══════════════════════════════════════════════════════════════════════════
#  6. LA RÉSERVE DE CHARGE — la pratique qui se perd si elle n'est pas écrite
# ═══════════════════════════════════════════════════════════════════════════

RESERVE_CHARGE_KG = 2268          # 5 000 lb, valeur citée au document


def reserve_de_charge():
    """La réserve à spécifier avant que les poutrelles ne soient fabriquées.

    POURQUOI ELLE EST ICI ET PAS DANS UNE NOTE. C'est une décision qui se prend
    au stade conception et qui devient irréversible à la fabrication : les
    tuyauteries, les chemins de câbles et les équipements s'ajoutent tout au
    long du projet — parfois APRÈS que les poutrelles ont été fabriquées —, et
    une charpente dimensionnée au juste besoin du jour n'a plus rien à leur
    offrir.

    CE QU'ELLE N'EST PAS, ET C'EST LE PIÈGE DE LECTURE. Ce n'est pas une
    réserve par mètre carré. C'est une capacité supplémentaire portée par
    l'ÉLÉMENT de structure, à répartir sur sa surface d'influence. La lire au
    mètre carré la multiplierait par la trame et donnerait une charpente
    absurde ; la lire comme un total de bâtiment la diviserait de même.
    """
    return {
        "valeur_kg": RESERVE_CHARGE_KG,
        "valeur_lb": 5000,
        "porte_par": "l'élément de structure — poutrelle ou solive —, à "
                     "répartir sur sa surface d'influence, et NON par mètre "
                     "carré de plancher",
        "quand": "Au stade conception, avant la commande de la charpente. "
                 "Après fabrication, elle ne s'ajoute plus.",
        "qui": "L'ingénieur de structure du projet la fixe, d'après la "
               "fonction prévue du bâtiment et les extensions envisagées ; le "
               "concepteur de poutrelles dit ce que cela implique en "
               "fabrication et en pose. C'est le rapprochement des deux qui "
               "donne la bonne valeur.",
        "origine": "document",
        "citation": "« We strongly recommend incorporating an add-load into "
                    "all designs. And it can be substantial – around 5,000 "
                    "pounds or more – to provide the flexibility data centers "
                    "increasingly need. »",
        "reserve": "La valeur citée relève d'un marché où les charges, les "
                   "trames et les usages diffèrent des nôtres. Ce qui se "
                   "reprend est le MÉCANISME — réserver au stade conception "
                   "une capacité qu'on ne saura chiffrer qu'après —, pas le "
                   "nombre, qui se fixe projet par projet.",
        "lien_densite": "Une réserve de cette nature est ce qui sépare un site "
                        "où la densité peut monter d'un site où elle ne le "
                        "pourra plus. Elle se décide des années avant qu'on "
                        "sache quelles baies y entreront.",
    }


# ═══════════════════════════════════════════════════════════════════════════
#  7. LES PRATIQUES DE CONSTRUCTION LUES AU DOCUMENT — avec leur provenance
# ═══════════════════════════════════════════════════════════════════════════
# D'OÙ ELLES VIENNENT, ET POURQUOI C'EST ÉCRIT. La source est un livre blanc
# DataCenterDynamics d'août 2026 COMMANDITÉ par un fabricant de charpente
# métallique : neuf de ses onze textes sont signés par son personnel, et sa
# dernière page est une publicité pour l'un de ses produits. Cela n'invalide
# rien — un fabricant sait ce qu'il fabrique — mais cela change ce qu'on peut
# en tirer : le MÉCANISME décrit se vérifie et se reprend, l'ARGUMENT de vente
# ne se reprend pas.
#
# CHAQUE ENTRÉE PORTE DONC SON ORIGINE ET SA RÉSERVE, et ce qui a été ÉCARTÉ
# est déclaré juste en dessous, avec le motif. Un tri qui ne montre que ce
# qu'il garde n'est pas un tri : c'est une reprise.

CONSTRUCTION = {
    "add_load": {
        "nom": "Réserve de charge posée au stade conception",
        "pratique": "Spécifier une capacité supplémentaire sur les éléments de "
                    "plancher, avant la commande de la charpente.",
        "mecanisme": "Les tuyauteries, chemins de câbles et équipements "
                     "s'ajoutent tout au long du projet, parfois après "
                     "fabrication ; une charpente au juste besoin n'a plus "
                     "rien à leur offrir.",
        "ne_couvre_pas": "Elle ne dit rien de la charge des baies elles-mêmes, "
                         "qui relève de la descente de charge du projet.",
        "origine": "document",
        "reserve": "Le nombre cité relève d'un autre marché ; le mécanisme se "
                   "reprend, la valeur se fixe projet par projet.",
    },
    "profondeur_poutrelle": {
        "nom": "Profondeur de la poutrelle à âme ajourée",
        "pratique": "Comparer poutrelle à âme ajourée et profilé laminé sur la "
                    "PROFONDEUR disponible, pas sur l'habitude.",
        "mecanisme": "Un profilé à ailes larges se trouve couramment autour de "
                     "1,00 à 1,10 m de hauteur ; une poutrelle à âme ajourée "
                     "atteint sans difficulté le double. La profondeur "
                     "commande la raideur et la charge admissible, donc la "
                     "portée entre appuis — donc la liberté d'implanter les "
                     "baies et le froid sans poteau au milieu.",
        "ne_couvre_pas": "Elle ne dit pas quel système est le moins cher : "
                         "cela dépend de la portée, de la charge et du marché "
                         "de l'acier au moment de la commande.",
        "origine": "document",
        "reserve": None,
    },
    "ame_ajouree_fluides": {
        "nom": "Passage des fluides dans l'âme, pas sous la poutre",
        "pratique": "Faire cheminer ventilation, électricité et plomberie À "
                    "TRAVERS l'âme ajourée plutôt qu'en dessous.",
        "mecanisme": "Ce qui passe sous la poutre s'ajoute à sa hauteur et se "
                     "paie en hauteur d'étage sur tout le bâtiment. Ce qui "
                     "passe dedans ne coûte rien de plus.",
        "ne_couvre_pas": "La coordination reste à faire : une réservation non "
                         "prévue à la fabrication ne se perce pas sur "
                         "chantier.",
        "origine": "document",
        "reserve": None,
    },
    "composite_seuil": {
        "nom": "Composite ou non composite, selon la portée",
        "pratique": "Sous environ 6 m de portée, le non-composite peut être "
                    "plus économique ; au-delà d'environ 9 m et à charge "
                    "élevée, le composite s'impose.",
        "mecanisme": "Le composite fait travailler la dalle béton en "
                     "compression avec l'acier, par connecteurs : l'ensemble "
                     "devient un seul élément, plus raide et plus résistant à "
                     "section moindre. La complexité qu'il ajoute ne se "
                     "rentabilise qu'à partir d'une certaine portée.",
        "ne_couvre_pas": "Les seuils sont des ordres de grandeur de "
                         "conception, convertis d'unités impériales ; ils "
                         "situent, ils ne tranchent pas un cas.",
        "origine": "document",
        "reserve": "Seuils cités par le fabricant, cohérents avec l'usage, "
                   "mais sans méthode publiée.",
    },
    "connexion_affleurante": {
        "nom": "Connexion à âme affleurante",
        "pratique": "Encastrer la poutrelle au nu de la poutre maîtresse au "
                    "lieu de la poser dessus.",
        "mecanisme": "Posée dessus, la poutrelle empêche la poutre maîtresse "
                     "de participer à l'action composite avec la dalle. "
                     "Abaissée au nu, elle la libère — et l'action composite "
                     "s'obtient sans acier supplémentaire. Le comportement "
                     "vibratoire s'en trouve aussi amélioré.",
        "ne_couvre_pas": "Le gain de matière annoncé par le fabricant n'est "
                         "pas repris ici : voir les écarts.",
        "origine": "document",
        "reserve": None,
    },
    "carbone_incorpore": {
        "nom": "Le carbone incorporé est figé à l'achat",
        "pratique": "Traiter le carbone de la structure comme une décision "
                    "d'achat, prise une fois, et non comme une performance "
                    "d'exploitation à améliorer ensuite.",
        "mecanisme": "Le carbone incorporé est émis à la fabrication : il est "
                     "dans le bâtiment le jour de la livraison. Aucune "
                     "conduite d'exploitation ne le réduit, et il ne se "
                     "rattrape pas. C'est l'inverse exact du carbone "
                     "opérationnel, qu'on améliore chaque année.",
        "ne_couvre_pas": "Il ne se compare pas au carbone opérationnel sans "
                         "horizon déclaré : sur trente ans d'exploitation, "
                         "l'ordre des deux dépend entièrement du mix "
                         "électrique retenu.",
        "origine": "mecanisme_etabli",
        "reserve": None,
    },
    "epd": {
        "nom": "La déclaration environnementale de produit comme trace",
        "pratique": "Exiger l'EPD des produits structurels et lire le "
                    "potentiel de réchauffement (GWP) qui y figure.",
        "mecanisme": "Sans document par produit, le carbone incorporé n'est "
                     "ni mesurable ni opposable : il reste une affirmation "
                     "commerciale. L'EPD est ce qui la rend vérifiable.",
        "ne_couvre_pas": "Une EPD ne classe pas les fournisseurs : les "
                         "périmètres et les règles de catégorie doivent être "
                         "les mêmes pour que deux chiffres se comparent.",
        "origine": "mecanisme_etabli",
        "reserve": None,
    },
    "four_electrique": {
        "nom": "Four électrique à arc contre haut fourneau",
        "pratique": "Distinguer la filière de production de l'acier dans la "
                    "spécification, et pas seulement la nuance.",
        "mecanisme": "Le four électrique à arc part de ferraille recyclée "
                     "plutôt que de minerai et de charbon ; l'écart "
                     "d'émissions entre les deux filières est de l'ordre d'un "
                     "facteur trois, avant toute autre optimisation.",
        "ne_couvre_pas": "L'écart dépend du mix électrique qui alimente le "
                         "four : la même filière n'a pas la même empreinte "
                         "selon le pays.",
        "origine": "mecanisme_etabli",
        "reserve": "Le facteur cité l'est par un sidérurgiste sur sa propre "
                   "production. L'ordre de grandeur est corroboré ailleurs ; "
                   "le chiffre exact d'un fournisseur se lit sur son EPD.",
    },
    "maquette_source_unique": {
        "nom": "Une seule source de vérité pour la maquette",
        "pratique": "Tenir la maquette et les documents dans un environnement "
                    "de données commun, où le terrain lit la même version que "
                    "l'étude.",
        "mecanisme": "Sur un chantier tenu en douze à quatorze mois avec des "
                     "effectifs qui décuplent en quelques mois, ce n'est pas "
                     "la pièce manquante qui coûte : c'est la pièce périmée "
                     "qu'on croit à jour.",
        "ne_couvre_pas": "Un environnement commun ne règle pas la "
                         "coordination : il rend visible qu'elle n'a pas été "
                         "faite.",
        "origine": "document",
        "reserve": "Décrit par un éditeur d'outils, dont c'est le produit.",
    },
    "megawatt_pas_metre_carre": {
        "nom": "Le centre de données se caractérise en mégawatts",
        "pratique": "Décrire l'opération par sa puissance avant sa surface, y "
                    "compris dans les pièces de marché.",
        "mecanisme": "La surface ne dit plus rien de ce qu'un bâtiment "
                     "contient : à densité variable d'un facteur soixante "
                     "entre une baie classique et une baie d'accélérateurs, "
                     "deux salles de même surface n'ont ni le même "
                     "raccordement, ni le même froid, ni le même plancher.",
        "ne_couvre_pas": "La puissance seule ne suffit pas non plus : c'est le "
                         "couple puissance-par-baie et masse-par-baie qui "
                         "commande le bâtiment, et c'est l'objet du calcul "
                         "ci-dessus.",
        "origine": "document",
        "reserve": None,
    },
}

# ── Ce qui a été lu et NON retenu, avec le motif ────────────────────────────
# UN TRI QUI NE MONTRE QUE CE QU'IL GARDE N'EST PAS UN TRI. Ces entrées ne sont
# pas des oublis : ce sont des refus, et ils se contestent — ce qui suppose
# qu'ils soient lisibles.
ECARTES = {
    "gain_de_poids_35": {
        "affirmation": "Une approche particulière de la connexion affleurante "
                       "permettrait « jusqu'à 35 % de poids d'acier en "
                       "moins » à performance vibratoire équivalente.",
        "motif": "Aucune méthode, aucune référence de comparaison, aucun "
                 "périmètre. « Jusqu'à » sans cas de base ne se vérifie pas et "
                 "ne s'oppose à personne. Le MÉCANISME de la connexion "
                 "affleurante est retenu ; ce chiffre ne l'est pas.",
    },
    "scope_2_automatique": {
        "affirmation": "« À mesure que la part d'électricité renouvelable "
                       "augmente, les émissions de scope 2 incorporées à nos "
                       "produits diminuent automatiquement. Cela se produit "
                       "sans aucune action supplémentaire de l'équipe "
                       "projet. »",
        "motif": "C'est le raisonnement en approche marché, et il ne tient que "
                 "sur des contrats d'achat annuels : une tonne d'acier "
                 "produite une nuit sans vent n'est pas décarbonée parce que "
                 "des certificats ont été acquis sur l'année. Cette "
                 "formulation est exactement celle que le moteur de "
                 "décarbonation du cabinet signale comme trompeuse. Elle est "
                 "écartée en tant qu'ARGUMENT ; le fait sous-jacent — un "
                 "fournisseur qui décarbone son électricité fait baisser le "
                 "carbone de ses produits — reste vrai et se lit sur les EPD "
                 "successives.",
    },
    "produit_commercial": {
        "affirmation": "Une gamme d'acier à carbone réduit du commanditaire, "
                       "présentée en dernière page.",
        "motif": "Un produit nommé n'est pas une pratique. Le cabinet ne "
                 "prescrit pas de fournisseur ; ce qui se reprend est le "
                 "critère — filière de production et EPD — qui permet de "
                 "comparer celui-là aux autres.",
    },
    "engagement_amont_fournisseur": {
        "affirmation": "Engager le sidérurgiste très en amont et regrouper le "
                       "tonnage à l'échelle nationale sécuriserait le "
                       "planning.",
        "motif": "C'est le modèle d'affaires du commanditaire, présenté comme "
                 "une bonne pratique. Il y a un fond réel — les délais "
                 "d'approvisionnement d'acier sont un jalon de planning, pas "
                 "un détail d'achat —, mais en marché public la conclusion est "
                 "inverse : on ne pré-engage pas un fournisseur avant "
                 "publication. Ce qui est retenu ailleurs, c'est le JALON ; "
                 "l'engagement amont ne l'est pas.",
    },
    "tentes_provisoires": {
        "affirmation": "Héberger des serveurs sous structures temporaires pour "
                       "démarrer l'entraînement avant la livraison du "
                       "bâtiment.",
        "motif": "Fait rapporté chez un exploitant américain, pas une "
                 "pratique transposable : la sécurité incendie, l'ICPE et la "
                 "réglementation thermique d'un bâtiment provisoire "
                 "accueillant plusieurs mégawatts ne se traitent pas ici comme "
                 "là-bas. Le mentionner comme bonne pratique serait "
                 "irresponsable.",
    },
}

CONSTRUCTION_SOURCE = (
    "LECTURE D'UN LIVRE BLANC COMMANDITÉ, PAS D'UNE NORME. La source est un "
    "eBook DataCenterDynamics d'août 2026 dont le commanditaire est un "
    "fabricant de charpente métallique, et dont la majorité des textes sont "
    "signés par son personnel. Ce qui en est repris ici est le MÉCANISME — ce "
    "qui fonctionne, et pourquoi —, jamais la recommandation commerciale. Les "
    "affirmations écartées sont déclarées avec leur motif, et se contestent.")


# ═══════════════════════════════════════════════════════════════════════════
#  8. L'ÉCHELLE FRANÇAISE — ce que la densité fait au parc, pas à une salle
# ═══════════════════════════════════════════════════════════════════════════
# POURQUOI UN CHIFFRE DE MARCHÉ DANS UN MODULE DE CALCUL. Tout ce qui précède
# raisonne sur UNE salle. Or la question posée — la densité complique la
# rénovation et reporte la pression sur le neuf — est une question de PARC : on
# ne peut y répondre qu'en confrontant la puissance à installer au bâti qui
# pourrait l'accueillir. Le chiffre ci-dessous est donc une donnée d'entrée du
# raisonnement, pas une illustration.
#
# CE QU'IL EST, ET CE QU'IL N'EST PAS. C'est une PROJECTION de cabinet, publiée
# pour une fédération professionnelle. Elle porte sur la puissance informatique
# INSTALLÉE, non sur la consommation électrique du pays ni sur la puissance
# raccordée — trois grandeurs qu'on confond régulièrement et dont les ordres de
# grandeur diffèrent d'un facteur deux ou trois. Elle ne devient pas plus vraie
# d'être reprise ici : elle est déclarée avec son émetteur, son horizon et sa
# réserve, et le calcul qui s'en sert dit ce qu'il en fait.

MARCHE_FR = {
    "puissance_2030_gw": 2.3,
    "multiplicateur": 3.15,
    "part_ia_basse": 0.35,
    "part_ia_haute": 0.40,
    "horizon": 2030,
    "nature": "projection_de_cabinet",
    "source": "Étude de cabinet pour France Datacenter : la puissance "
              "électrique installée en France serait multipliée par un peu "
              "plus de trois d'ici 2030, pour atteindre 2,3 GW, dont 35 à "
              "40 % liés à l'IA.",
    "reserve": "Le multiplicateur « un peu plus de trois » est repris ici à "
               "3,15 pour pouvoir en déduire un point de départ ; « un peu "
               "plus » n'est pas un nombre, et la valeur 2026 qui en découle "
               "est donc une DÉDUCTION, pas une donnée publiée. Une "
               "projection à quatre ans n'est pas un engagement : elle vaut "
               "comme ordre de grandeur pour dimensionner un raisonnement, "
               "pas comme base de plan d'affaires.",
}


def pression_construction(regime_ia="ia_accelerateurs",
                          plancher_existant="courant"):
    """Ce que la part IA de la projection 2030 demande comme bâtiment.

    LE RAISONNEMENT, EN TROIS PAS, ET CHACUN EST CONTESTABLE SÉPARÉMENT.

      1. La projection donne la puissance installée en 2030 et la part liée à
         l'IA. On en déduit l'incrément à construire — et le point de départ,
         qui est une déduction du multiplicateur, pas une donnée.
      2. Cette part IA, ramenée à une densité par baie, donne un NOMBRE DE
         BAIES. Ce pas suppose que toute la puissance IA se tienne à cette
         densité : c'est une BORNE, pas une prévision, et c'est pourquoi la
         fonction rend aussi le compte à la densité que l'air sait tenir.
      3. La charge au sol de ces baies se compare au plancher d'une salle
         existante. C'est ce dernier pas qui répond à la question posée : si
         elle ne passe pas, la puissance ne va pas dans le parc existant.

    CE QUE LA FONCTION NE FAIT PAS : prédire où les centres se construiront,
    ni combien coûtera un mètre carré neuf. Elle établit qu'une part
    identifiable de la puissance projetée ne peut PAS se loger dans le bâti
    conçu pour le régime classique — ce qui est une contrainte, pas un marché.
    """
    m = MARCHE_FR
    ia_basse = m["puissance_2030_gw"] * m["part_ia_basse"] * 1000.0   # MW
    ia_haute = m["puissance_2030_gw"] * m["part_ia_haute"] * 1000.0   # MW
    depart = m["puissance_2030_gw"] / m["multiplicateur"] * 1000.0    # MW

    reg = REGIMES[regime_ia]
    air = REGIMES["dense_air"]
    cap = PLANCHERS[plancher_existant]["kpa"] * 1000.0 / _c("g")      # kg/m²
    # LE MÊME CRITÈRE QUE `plancher()`, ET PAS UN AUTRE. Cette ligne divisait
    # par l'emprise NUE quand la salle divise par la surface d'INFLUENCE : le
    # parc aurait annoncé un refus que la salle dément deux écrans plus bas.
    # Deux fabriques d'un même chiffre, c'est la garantie qu'elles divergent.
    charge = reg["masse_baie_kg"] / _c("emprise_baie_m2")             # kg/m²

    def _baies(mw, kw_baie):
        return int(round(mw * 1000.0 / kw_baie))

    return {
        "projection": dict(m),
        "puissance_2026_deduite_mw": round(depart),
        "increment_a_construire_mw": round(m["puissance_2030_gw"] * 1000.0
                                           - depart),
        "part_ia_mw": [round(ia_basse), round(ia_haute)],
        "baies_au_regime_ia": [_baies(ia_basse, reg["kw_baie"]),
                               _baies(ia_haute, reg["kw_baie"])],
        "baies_si_meme_puissance_en_air": [_baies(ia_basse, air["kw_baie"]),
                                           _baies(ia_haute, air["kw_baie"])],
        "regime_retenu": {"cle": regime_ia, "nom": reg["nom"],
                          "kw_baie": reg["kw_baie"],
                          "masse_baie_kg": reg["masse_baie_kg"]},
        "plancher_existant": {"cle": plancher_existant,
                              "nom": PLANCHERS[plancher_existant]["nom"],
                              "capacite_kg_m2": round(cap)},
        "charge_du_regime_kg_m2": round(charge),
        "tient_dans_le_parc_existant": charge <= cap,
        "facteur_de_depassement": round(charge / cap, 1) if cap else None,
        "lecture": _lecture_pression(ia_basse, ia_haute, reg, air, charge, cap,
                                     plancher_existant),
    }


def _milliers(x):
    """Le séparateur de milliers, en espace fine insécable.

    IL EST ICI ET PAS DANS TROIS ENDROITS. Les nombres de cette lecture
    partaient de deux fabriques différentes — l'une groupait, l'autre non — et
    la même charge s'affichait « 1889 kg/m² » dans l'encart de la page et
    « 1 889 kg/m² » dans la carte deux lignes plus bas. Un lecteur qui voit
    deux graphies du même nombre se demande si ce sont deux nombres.
    """
    return "{:,}".format(int(round(x))).replace(",", "\u202f")


def _lecture_pression(ia_basse, ia_haute, reg, air, charge, cap, pl_cle):
    """La phrase que le calcul autorise, et pas une de plus.

    ELLE SUIT LE NOMBRE AU LIEU DE LE PRÉCÉDER. Une première version affirmait
    « un nombre modeste » quel que soit le résultat — vrai au régime IA, faux
    au régime classique, où le compte de baies est six fois plus grand. Et
    elle annonçait « 1,0 fois trop » pour un dépassement de un pour mille,
    formulation absurde qui aurait décrédibilisé un constat exact. Les deux
    tournures se choisissent désormais sur la valeur.
    """
    n_ia = int(round(ia_basse * 1000.0 / reg["kw_baie"]))
    n_air = int(round(ia_basse * 1000.0 / air["kw_baie"]))
    comparaison = ("contre %s en baies que l'air sait refroidir — moins "
                   "nombreuses, et c'est précisément ce qui trompe"
                   % _milliers(n_air)) if n_ia < n_air else (
        "contre %s en baies que l'air sait refroidir" % _milliers(n_air))

    # LE FAUX-PLANCHER EST LE CRITÈRE QUI MORD LE PREMIER, et une lecture de
    # parc qui ne parlerait que de la dalle passerait à côté du cas le plus
    # fréquent : une salle dont la dalle tient et dont les panneaux non.
    pied = reg["masse_baie_kg"] / float(_c("pieds_par_baie"))
    admis = FAUX_PLANCHERS["standard"]["ponctuel_service_kg"]
    fp = ("" if pied <= admis else
          " S'y ajoute un critère que la capacité en kilopascals ne voit pas : "
          "%d kg par pied, pour %d kg admis par un panneau de faux-plancher "
          "courant. Beaucoup de salles buteront là AVANT de buter sur leur "
          "dalle — et cet obstacle-là se lève en retirant le faux-plancher."
          % (round(pied), admis))

    if charge <= cap:
        return ("À %.0f–%.0f MW liés à l'IA, la charge répartie de ce régime "
                "(%s kg/m²) reste sous la capacité d'une %s (%s kg/m²) : le "
                "parc existant peut en accueillir une partie, sous réserve du "
                "diagnostic de structure bâtiment par bâtiment.%s"
                % (ia_basse, ia_haute, _milliers(charge),
                   PLANCHERS[pl_cle]["nom"].lower(), _milliers(cap), fp))

    ecart = charge / cap
    combien = ("soit %s fois trop" % ("%.1f" % ecart).replace(".", ",")
               if ecart >= 1.15 else
               "soit exactement au niveau de la capacité, sans aucune marge")
    return (
        "%.0f à %.0f MW de puissance informatique liée à l'IA sont à installer "
        "d'ici %d. À %s kW par baie, cela représente environ %s baies, %s. Ce "
        "ne sont donc pas des mètres carrés qui manquent, c'est de la CAPACITÉ "
        "PORTANTE : ces baies appliquent %s kg/m² répartis là où une %s en "
        "admet %s, %s.%s Cette part de la puissance projetée ne se loge pas "
        "dans le bâti conçu pour le régime classique sans reprise de "
        "plancher — et une reprise de dalle en salle occupée décide souvent "
        "seule de construire ailleurs. C'est là que la densité cesse d'être un "
        "sujet de refroidissement pour devenir un sujet de construction neuve."
        % (ia_basse, ia_haute, MARCHE_FR["horizon"], ("%.0f" % reg["kw_baie"]),
           _milliers(n_ia), comparaison, _milliers(charge),
           PLANCHERS[pl_cle]["nom"].lower(), _milliers(cap), combien, fp))


# ═══════════════════════════════════════════════════════════════════════════
#  9. CE QUE LE MODULE SERT AUX PAGES
# ═══════════════════════════════════════════════════════════════════════════

def glossaire():
    """Les familles d'infobulles versées au glossaire unique de la page."""
    return {
        "diffusion": {k: {
            "nom": v["nom"],
            "aide": (v["principe"] + "\n\nCe qui plafonne : " +
                     v["ce_qui_plafonne"] +
                     ("\n\nPlafond : %s kW par baie (plage de conception)."
                      % ("%.0f" % v["plafond_kw_baie"])
                      if v.get("plafond_kw_baie")
                      else "\n\nAucun plafond de refroidissement propre — il "
                           "est porté par : " + (v.get("plafond_porte_par")
                                                 or "—") + ".") +
                     "\n\nEn rénovation : " + v["renovation"]),
        } for k, v in DIFFUSION.items()},
        "regime": {k: {
            "nom": v["nom"],
            "aide": ("%s\n\n%s kW et environ %s kg par baie.\n\nMasse : %s"
                     % (v["quoi"], ("%.0f" % v["kw_baie"]),
                        v["masse_baie_kg"], v["source_masse"])),
        } for k, v in REGIMES.items()},
        "plancher_dc": {k: {
            "nom": v["nom"],
            "aide": ("%s\n\nCapacité déclarée : %s kPa, soit environ %d kg/m². "
                     "\n\n%s" % (v["quoi"], ("%.1f" % v["kpa"]).replace(".", ","),
                                 round(v["kpa"] * 1000.0 / _c("g")),
                                 v["reserve"])),
        } for k, v in PLANCHERS.items()},
        "faux_plancher": {k: {
            "nom": v["nom"],
            "aide": ("%s\n\n%s\n\n%s" % (
                v["quoi"],
                ("Charge ponctuelle de service : environ %d kg sous un pied — "
                 "soit la moitié de la charge ultime, usage constant du "
                 "métier." % v["ponctuel_service_kg"])
                if v["ponctuel_service_kg"] else
                "Aucune charge ponctuelle admissible à opposer : il n'y a pas "
                "de panneau.",
                v["reserve"])),
        } for k, v in FAUX_PLANCHERS.items()},
        "pratique_construction": {k: {
            "nom": v["nom"],
            "aide": (v["pratique"] + "\n\nPourquoi cela marche : " +
                     v["mecanisme"] + "\n\nCe que cela ne couvre pas : " +
                     v["ne_couvre_pas"] +
                     ("\n\nRéserve : " + v["reserve"] if v.get("reserve")
                      else "")),
        } for k, v in CONSTRUCTION.items()},
    }


def referentiel():
    """Tout ce que ce module sert aux pages, en un seul appel."""
    return {
        "version": VERSION,
        "constantes": CONSTANTES,
        "regimes": REGIMES,
        "ordre_regimes": ORDRE_REGIMES,
        "diffusion": DIFFUSION,
        "ordre_diffusion": ORDRE_DIFFUSION,
        "diffusion_source": DIFFUSION_SOURCE,
        "planchers": PLANCHERS,
        "faux_planchers": FAUX_PLANCHERS,
        "planchers_source": PLANCHERS_SOURCE,
        "construction": CONSTRUCTION,
        "ecartes": ECARTES,
        "construction_source": CONSTRUCTION_SOURCE,
        "reserve_charge": reserve_de_charge(),
        "marche_fr": MARCHE_FR,
        "pression_construction": pression_construction(),
        "glossaire": glossaire(),
    }
