"""Ce qu'il faut savoir pour répondre à un client sur un centre de données.

CE QUE CE MODULE EST. Le vocabulaire technique du métier, expliqué : les modes
de refroidissement, les architectures de production et de distribution
électrique, les grands enjeux (Tier, PUE, WUE, ICPE) et les trois natures de
travaux (construction neuve, fit-out, rétrofit). Il ne calcule rien. Il sert
les infobulles des formulaires et les encarts d'explication des pages
`/datacenter` et `/ingenierie-datacenter`.

POURQUOI IL EXISTE SÉPARÉMENT. Les listes déroulantes de ces deux pages
proposent « Free cooling indirect à assistance adiabatique », « 2N »,
« Tier III » — des étiquettes exactes et opaques. Sans explication, un
formulaire de ce genre ne s'adresse qu'à ceux qui n'en avaient pas besoin, et
celui qui choisit au hasard produit un dossier faux sans le savoir. Le savoir
métier vivait jusqu'ici dans les têtes ; il est ici.

CE QU'IL N'EST PAS. Ni une norme, ni un avis de conception. Chaque entrée dit
ce que la technique FAIT, à quelle condition, et ce qu'elle coûte en contrainte
— c'est ce qui permet de tenir une conversation client sans promettre. Le choix
pour un site donné se fait sur une étude de site, avec des données de climat,
de réseau et de matériel qui ne sont pas ici.

LE LIEN AVEC LE MOTEUR DE CALCUL. Les modes de refroidissement portent la clé
de la famille du moteur (`datacenter.REFROIDISSEMENT`) quand elle existe, et le
disent quand elle n'existe pas : le free-chilling est un MODE DE CONDUITE d'une
production d'eau glacée, pas une septième famille, et le laisser croire ferait
chercher une option qui n'est pas dans la liste. La cohérence des clés est
vérifiée au chargement — une famille ajoutée au moteur sans explication ici
serait une étiquette muette de plus.
"""

VERSION = "2026-08-a"


# ═══════════════════════════════════════════════════════════════════════════
#  1. LES MODES DE REFROIDISSEMENT
# ═══════════════════════════════════════════════════════════════════════════
# LA CONFUSION QUE CETTE TABLE EXISTE POUR LEVER. « Free cooling » désigne dans
# la bouche de trois interlocuteurs trois choses différentes : l'air extérieur
# soufflé en salle, un échangeur qui isole la salle de cet air, et l'arrêt du
# compresseur d'un groupe froid quand il fait froid dehors. Les trois n'ont ni
# le même coût, ni le même risque, ni la même consommation d'eau. Un client qui
# dit « on fera du free cooling » n'a rien dit tant qu'on n'a pas demandé
# laquelle des trois.
#
# CHAQUE ENTRÉE PORTE CINQ CHOSES, dans cet ordre :
#   · principe    — ce que la machine fait, physiquement ;
#   · quand       — la condition à laquelle ça marche ;
#   · cout        — ce que ça demande en investissement et en place ;
#   · contrainte  — ce que ça impose au reste du projet ;
#   · erreur      — la faute qu'on voit le plus souvent sur ce mode.
#
# La cinquième est celle qui sert en réunion : elle donne la question à poser.

MODES_REFROIDISSEMENT = {
    "air_dx": {
        "nom": "Détente directe sur air (DX)",
        "famille": "air_dx",
        "principe": "Un circuit frigorifique complet par armoire : l'évaporateur "
                    "refroidit l'air de la salle, le condenseur rejette la "
                    "chaleur à l'extérieur. Aucun réseau d'eau, aucune "
                    "production centralisée.",
        "quand": "Petites salles, salles techniques d'immeuble, sites sans place "
                 "pour une production centralisée ni personnel d'exploitation "
                 "sur site.",
        "cout": "Le moins cher à installer, le plus cher à exploiter. Pas de "
                "local technique de production, pas de réseau hydraulique.",
        "contrainte": "La redondance se fait par machines entières : une armoire "
                      "de secours par salle, pas un composant de secours. La "
                      "densité admissible par baie plafonne vite.",
        "erreur": "La retenir pour un site qui grandira. Passer du DX à une "
                  "production centralisée ne s'ajoute pas : cela se refait, "
                  "salle occupée.",
    },
    "eau_glacee": {
        "nom": "Production d'eau glacée par groupe froid",
        "famille": "eau_glacee",
        "principe": "Des groupes frigorifiques centralisés produisent de l'eau à "
                    "basse température, distribuée vers des unités terminales en "
                    "salle. Le compresseur tourne toute l'année.",
        "quand": "La référence des grands sites. Elle admet toutes les densités "
                 "courantes et se redonde composant par composant.",
        "cout": "Local de production, réseau hydraulique bouclé, vannes "
                "d'isolement, appoint et traitement d'eau. Investissement élevé, "
                "durée de vie longue.",
        "contrainte": "Le réseau devient le point unique : deux groupes froid sur "
                      "une antenne unique ne font qu'une seule chaîne, quelle que "
                      "soit la redondance affichée sur la production.",
        "erreur": "Compter la redondance sur les machines et pas sur la "
                  "distribution. C'est le défaut le plus fréquent des dossiers "
                  "annonçant du 2N.",
    },
    "free_chilling": {
        "nom": "Free-chilling (refroidissement naturel côté eau glacée)",
        # Ce mode n'a PAS de famille dans le moteur, et le dit. Voir plus bas :
        # `famille` à None signifie « conduite d'une autre famille », et
        # `porte_par` dit laquelle. Sans cela, un lecteur chercherait dans la
        # liste déroulante du calcul une option qui n'y est pas.
        "famille": None,
        "porte_par": "eau_glacee",
        "principe": "MODE DE CONDUITE d'une production d'eau glacée, pas une "
                    "famille à part : quand l'air extérieur est assez froid, un "
                    "échangeur — batterie à eau glycolée en amont, ou "
                    "aéroréfrigérant dédié — produit tout ou partie de l'eau "
                    "glacée sans faire tourner le compresseur. En mi-saison le "
                    "free-chilling est partiel : le compresseur ne fournit que "
                    "l'appoint.",
        "quand": "Dès que le régime d'eau le permet. C'est le régime de "
                 "température, pas le climat, qui décide : une boucle 7/12 °C "
                 "ne bascule qu'en hiver, une boucle 18/24 °C bascule la moitié "
                 "de l'année sous climat tempéré. Élargir le régime coûte des "
                 "échangeurs plus grands, pas des machines de plus.",
        "cout": "Surface d'échange supplémentaire et vannes de basculement. "
                "Surcoût modéré sur une installation neuve, difficile à ajouter "
                "après coup faute de place en toiture.",
        "contrainte": "Le nombre d'heures gagnées se calcule sur un fichier "
                      "météo horaire du SITE, pas sur une moyenne. Une "
                      "installation vendue « free-chilling » sans ce calcul "
                      "n'annonce aucune économie vérifiable.",
        "erreur": "Le confondre avec le free cooling direct. Le free-chilling "
                  "n'introduit AUCUN air extérieur en salle : c'est précisément "
                  "son intérêt sur un site pollué, salin ou urbain dense.",
    },
    "free_cooling_air": {
        "nom": "Free cooling direct sur air extérieur",
        "famille": "free_cooling_air",
        "principe": "L'air extérieur filtré est soufflé directement en salle et "
                    "l'air chaud est rejeté. Aucune machine frigorifique en "
                    "fonctionnement nominal — seulement des ventilateurs, et un "
                    "appoint pour les heures extrêmes.",
        "quand": "Climat tempéré ET classe ASHRAE élargie admise par le "
                 "matériel informatique. Les deux conditions sont nécessaires : "
                 "la seconde est un choix de projet qui engage le constructeur "
                 "des serveurs.",
        "cout": "Grandes sections de gaines et de prises d'air, filtration "
                "conséquente, volets motorisés. La place en façade et en toiture "
                "devient dimensionnante.",
        "contrainte": "L'air extérieur entre : sa pollution, son humidité et sa "
                      "salinité entrent avec lui. Filtration, contrôle "
                      "d'hygrométrie et surveillance de la corrosion deviennent "
                      "des sujets d'exploitation permanents.",
        "erreur": "L'annoncer sans avoir fait valider la classe ASHRAE par le "
                  "client informatique. Une garantie serveur perdue coûte plus "
                  "que l'énergie économisée.",
    },
    "adiabatique": {
        "nom": "Free cooling indirect à assistance adiabatique",
        "famille": "adiabatique",
        "principe": "Un échangeur air/air — roue, plaques ou caloduc — sépare "
                    "l'air de la salle de l'air extérieur. Aux heures chaudes, "
                    "on humidifie l'air extérieur avant l'échangeur : "
                    "l'évaporation abaisse sa température et prolonge le "
                    "fonctionnement sans machine frigorifique.",
        "quand": "Le compromis le plus répandu sur les grands sites récents : il "
                 "garde la salle isolée de l'extérieur ET consomme peu d'eau, "
                 "puisque l'humidification ne fonctionne qu'aux heures chaudes.",
        "cout": "Échangeurs volumineux, réseau d'eau d'appoint traitée, "
                "surveillance sanitaire du circuit d'humidification.",
        "contrainte": "La consommation d'eau est SAISONNIÈRE : le WUE annuel "
                      "lisse des pointes estivales qui tombent au moment où la "
                      "ressource est la plus tendue et où un arrêté de "
                      "restriction peut s'appliquer.",
        "erreur": "Présenter le WUE annuel à une autorité de l'eau. C'est la "
                  "pointe qui se négocie, pas la moyenne.",
    },
    "tour_evaporative": {
        "nom": "Tour de refroidissement évaporative",
        "famille": "tour_evaporative",
        "principe": "L'eau du circuit de condensation est refroidie par "
                    "évaporation d'une partie d'elle-même dans un flux d'air. La "
                    "température atteinte descend sous celle de l'air, ce qu'un "
                    "échangeur sec ne sait pas faire.",
        "quand": "Le meilleur rendement énergétique historique des grandes "
                 "puissances, et le seul procédé qui tienne ses performances "
                 "sous climat chaud et sec.",
        "cout": "Traitement d'eau permanent, purges, appoint continu, et un plan "
                "de gestion du risque de légionelle avec analyses périodiques.",
        "contrainte": "Consommation d'eau CONTINUE et élevée, et rubrique ICPE "
                      "2921 au titre du refroidissement évaporatif par "
                      "dispersion d'eau dans un flux d'air — avec un régime qui "
                      "dépend de la puissance thermique évacuée.",
        "erreur": "Traiter le classement ICPE en fin de chantier. Le régime "
                  "d'enregistrement porte un délai d'instruction qui est un "
                  "jalon de planning, pas une formalité.",
    },
    "liquide_dlc": {
        "nom": "Refroidissement liquide direct (DLC, plaques froides)",
        "famille": "liquide_dlc",
        "principe": "Une plaque froide parcourue d'eau tempérée est plaquée "
                    "directement sur le processeur et les composants les plus "
                    "chauds. Elle capte 70 à 80 % de la chaleur du serveur à la "
                    "source ; le reste est évacué par l'air de la salle, qui "
                    "reste donc nécessaire.",
        "quand": "Densité par baie hors d'atteinte de l'air — calcul intensif, "
                 "grappes d'accélérateurs. C'est la densité qui l'impose, pas "
                 "l'efficacité énergétique, qui n'est qu'un bénéfice second.",
        "cout": "Une boucle hydraulique supplémentaire jusqu'à la baie, avec ses "
                "collecteurs, sa détection de fuite et son unité de distribution "
                "(CDU). Le serveur doit être compatible : ce n'est pas une "
                "adaptation de site.",
        "contrainte": "L'eau captée sort CHAUDE — c'est l'intérêt : le rejet peut "
                      "se faire à sec, sans machine frigorifique, et la chaleur "
                      "devient réutilisable en réseau urbain. Mais la salle "
                      "garde une part d'air à traiter, et deux régimes de "
                      "température coexistent.",
        "erreur": "Dimensionner le froid air comme s'il n'y en avait plus. La "
                  "part non captée reste à évacuer, et elle n'est pas nulle.",
    },
    "immersion": {
        "nom": "Immersion en bain diélectrique (monophasique)",
        "famille": "immersion",
        "principe": "Les cartes sont immergées dans un fluide diélectrique qui "
                    "capte la quasi-totalité de la chaleur. Plus de ventilateurs "
                    "dans les serveurs, plus de flux d'air à organiser en salle.",
        "quand": "Densités extrêmes, ou sites où la place et le bruit priment. "
                 "Reste minoritaire en exploitation.",
        "cout": "Bacs, fluide, manutention spécifique. La maintenance d'un "
                "serveur immergé n'est pas la maintenance d'un serveur en baie.",
        "contrainte": "Garanties constructeur à négocier, filière de "
                      "récupération du fluide à organiser, plancher à "
                      "redimensionner pour la charge.",
        "erreur": "L'évaluer sur le seul PUE. Le coût d'exploitation et la "
                  "disponibilité des compétences décident plus souvent que "
                  "l'énergie.",
    },
}

MODES_SOURCE = (
    "CADRAGE MÉTIER, PAS UNE NORME. Ces descriptions disent le principe de "
    "fonctionnement et ses conséquences de projet ; elles ne fixent aucune "
    "performance. Les plages de PUE associées à chaque famille sont posées "
    "ailleurs — au moteur de calcul, avec leur réserve. Le choix pour un site "
    "donné se fait sur un fichier météo horaire, la classe ASHRAE admise par "
    "le matériel et les courbes du constructeur retenu.")


# ═══════════════════════════════════════════════════════════════════════════
#  2. LES ARCHITECTURES DE PRODUCTION ET DE DISTRIBUTION ÉLECTRIQUE
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE LA TABLE SÉPARE, ET QU'ON CONFOND TOUT LE TEMPS. Une architecture
# électrique se lit sur deux axes indépendants :
#
#   · la PRODUCTION — d'où vient l'énergie et qui prend le relais : le
#     raccordement, le poste de livraison, les transformateurs, les groupes
#     électrogènes, les onduleurs et leur stockage ;
#   · la DISTRIBUTION — comment elle arrive à la baie : le nombre de chemins,
#     leur indépendance réelle, et le point où ils se rejoignent.
#
# LA FAUTE CLASSIQUE EST DE CROIRE QUE LE PREMIER SUFFIT. Deux chaînes de
# production complètes qui se rejoignent sur un tableau terminal unique ne font
# qu'un seul chemin : la redondance s'arrête au dernier organe commun, et c'est
# lui, pas la production, qui détermine le niveau réellement atteint.

ARCHITECTURES_ELEC = {
    # ── Production ────────────────────────────────────────────────────────
    "raccordement": {
        "nom": "Raccordement au réseau public",
        "axe": "production",
        "principe": "Le point de livraison du distributeur ou du transporteur. "
                    "Sa tension — HTA ou HTB — découle de la puissance "
                    "souscrite, et son délai de mise à disposition découle de "
                    "l'état du réseau local.",
        "ce_qui_decide": "La puissance souscrite, et elle seule, décide de la "
                         "tension, du type de poste et de l'interlocuteur. Sur "
                         "un centre de données, ce délai est le plus long du "
                         "projet et il ne se rattrape pas.",
        "point_faible": "Deux arrivées depuis le même poste source ne font pas "
                        "deux sources : elles tombent ensemble. L'indépendance "
                        "se vérifie sur le schéma du gestionnaire de réseau, "
                        "pas sur le contrat. Et au regard du référentiel Tier, "
                        "AUCUNE arrivée publique ne compte : tout service "
                        "venant d'au-delà de la limite de propriété et hors du "
                        "contrôle de l'exploitant est traité comme non fiable. "
                        "La production sur site est la source primaire ; le "
                        "réseau est une alternative économique. ENFIN, UNE "
                        "PUISSANCE EFFAÇABLE N'EST PAS UNE PUISSANCE : un "
                        "raccordement non ferme s'obtient plus vite parce que "
                        "le gestionnaire se réserve de le réduire, et la part "
                        "réduite ne se compte ni au bilan de puissance, ni "
                        "dans une garantie de service. Ce qu'elle coûte en "
                        "calcul non servi se calcule sur les clauses de la "
                        "convention.",
        "referentiel": "nfc13100",
    },
    "poste_livraison": {
        "nom": "Poste de livraison et transformation HTA/BT",
        "axe": "production",
        "principe": "Cellules d'arrivée et de protection, comptage, puis "
                    "transformateurs qui abaissent à la tension de "
                    "distribution.",
        "ce_qui_decide": "Le nombre de transformateurs et leur schéma de "
                         "couplage fixent ce qu'on peut entretenir sans "
                         "coupure. C'est le premier endroit où la redondance "
                         "se paie.",
        "point_faible": "Un jeu de barres unique en aval de deux "
                        "transformateurs ramène la redondance à zéro pour tout "
                        "défaut sur ce jeu de barres.",
        "referentiel": "nfc13200",
    },
    "groupes": {
        "nom": "Groupes électrogènes de secours",
        "axe": "production",
        "principe": "Moteurs diesel qui reprennent la charge après la "
                    "défaillance réseau, une fois les onduleurs ayant tenu le "
                    "temps du démarrage et du couplage.",
        "ce_qui_decide": "La puissance déclarée n'a de sens qu'avec son régime "
                         "d'utilisation : une puissance de secours n'est pas "
                         "une puissance continue, et le même moteur n'annonce "
                         "pas le même chiffre selon le régime retenu.",
        "point_faible": "Ils sont testés à vide et défaillent en charge. "
                        "L'essai qui compte est la reprise de la charge réelle, "
                        "au commissioning puis périodiquement en exploitation. "
                        "Et la CLASSE de service décide de l'éligibilité à un "
                        "niveau Tier III ou IV : un groupe limité en heures "
                        "consécutives à la puissance demandée n'y répond pas, "
                        "et une classe « secours » l'est par définition.",
        "referentiel": "iso8528",
        "icpe": "2910",
    },
    "stockage_fioul": {
        "nom": "Stockage de combustible et autonomie",
        "axe": "production",
        "principe": "Cuves, rétention, réseau d'alimentation et nourrices. "
                    "L'autonomie visée — souvent 48 à 72 heures — dicte le "
                    "volume.",
        "ce_qui_decide": "Le volume stocké commande à la fois l'autonomie "
                         "annoncée au client et le régime ICPE du site. Les "
                         "deux se décident ensemble ou pas du tout.",
        "point_faible": "Un contrat de réapprovisionnement ne vaut pas "
                        "autonomie : en crise régionale, la file d'attente est "
                        "la même pour tout le monde.",
        "icpe": "4734",
    },
    "onduleurs": {
        "nom": "Onduleurs (ASI) et stockage d'énergie",
        "axe": "production",
        "principe": "Ils tiennent la charge sans coupure entre la perte réseau "
                    "et la reprise par les groupes, et filtrent la qualité de "
                    "l'énergie en fonctionnement normal.",
        "ce_qui_decide": "L'autonomie de batterie n'a pas besoin d'être longue "
                         "— quelques minutes suffisent si les groupes "
                         "démarrent. Une autonomie surdimensionnée coûte du "
                         "local, de la ventilation et du remplacement "
                         "périodique.",
        "point_faible": "Le by-pass statique est le chemin qui reste quand tout "
                        "le reste a lâché : un by-pass non maintenu annule "
                        "l'intérêt de l'onduleur au pire moment.",
        "icpe": "2925",
    },
    # ── Distribution ──────────────────────────────────────────────────────
    "radial_simple": {
        "nom": "Distribution radiale simple",
        "axe": "distribution",
        "principe": "Un seul chemin depuis le tableau général jusqu'à la baie. "
                    "Toute intervention sur ce chemin coupe ce qu'il alimente.",
        "ce_qui_decide": "Le coût le plus bas, et un niveau de disponibilité qui "
                         "ne dépasse pas la maintenance programmée avec arrêt.",
        "point_faible": "Aucune maintenance sans coupure. Ce n'est pas un "
                        "défaut, c'est le choix assumé — à condition qu'il soit "
                        "écrit.",
    },
    "double_voie": {
        "nom": "Double voie A/B jusqu'à la baie",
        "axe": "distribution",
        "principe": "Deux chemins complets et physiquement séparés, chacun "
                    "capable de porter la totalité de la charge. Les serveurs "
                    "à double alimentation en profitent directement.",
        "ce_qui_decide": "C'est la condition de la maintenance sans "
                         "interruption. Elle se vérifie sur les cheminements "
                         "réels : deux voies dans le même chemin de câbles "
                         "n'en font qu'une pour un incendie.",
        "point_faible": "Les équipements à alimentation SIMPLE — matériel "
                        "réseau, baies de stockage anciennes — ramènent le "
                        "problème : ils exigent un commutateur de source "
                        "(STS), lequel devient à son tour un organe unique.",
    },
    "n_plus_1": {
        "nom": "Redondance N+1 sur unités",
        "axe": "distribution",
        "principe": "Une unité de secours pour N unités nécessaires. La panne "
                    "d'une unité est couverte ; la deuxième ne l'est plus.",
        "ce_qui_decide": "Le compte porte sur les UNITÉS, pas sur la puissance. "
                         "Trois unités à 500 kW pour un besoin de 1 000 kW, "
                         "c'est du N+1 ; deux unités à 750 kW aussi, et elles "
                         "ne coûtent pas la même chose.",
        "point_faible": "Pendant la maintenance de l'unité de secours, "
                        "l'installation est en N : la fenêtre d'entretien est "
                        "une fenêtre de vulnérabilité, et elle se planifie.",
    },
    "deux_n": {
        "nom": "Redondance 2N — deux chaînes complètes",
        "axe": "distribution",
        "principe": "Deux installations complètes et indépendantes, chacune "
                    "dimensionnée pour la totalité. L'une peut être arrêtée "
                    "entièrement.",
        "ce_qui_decide": "C'est ce que demande la tolérance à la panne unique "
                         "AVEC maintenance concurrente. Cela double des chaînes "
                         "entières : c'est le premier multiplicateur de coût "
                         "des lots électricité et froid.",
        "point_faible": "Chaque chaîne tourne à la moitié de sa capacité, donc "
                        "hors de son point de meilleur rendement : le 2N "
                        "dégrade le PUE, et c'est normal.",
    },
    "block_redondant": {
        "nom": "Redondance distribuée (block redundant, « catcher »)",
        "axe": "distribution",
        "principe": "N chaînes de production alimentent la charge, plus une "
                    "chaîne de réserve qui peut reprendre celle qui manque, "
                    "par commutation. Le coût est celui du N+1, la souplesse "
                    "s'approche du 2N.",
        "ce_qui_decide": "Un compromis économique sur les grandes puissances. "
                         "Il repose entièrement sur les commutateurs et sur "
                         "leur logique de bascule.",
        "point_faible": "La logique de commutation devient le point unique. "
                        "Elle doit être éprouvée au commissioning en conditions "
                        "réelles, pas simulée sur table.",
    },
    "terminal": {
        "nom": "Distribution terminale : tableaux, canalisations et bandeaux",
        "axe": "distribution",
        "principe": "Tableaux divisionnaires, canalisations préfabriquées ou "
                    "câbles, unités de distribution en baie. C'est le dernier "
                    "mètre, et souvent le seul modifié pendant l'exploitation.",
        "ce_qui_decide": "Le sous-comptage se pose ICI ou nulle part : sans "
                         "mesure par départ, la consommation par consommateur "
                         "reste une hypothèse et le PUE partiel ne se démontre "
                         "pas.",
        "point_faible": "La sélectivité des protections se vérifie sur le "
                        "calcul de courts-circuits complet. Un défaut en baie "
                        "qui fait déclencher le tableau général est un défaut "
                        "de sélectivité, pas de matériel.",
        "referentiel": "cei60909",
    },
}

ARCHITECTURES_SOURCE = (
    "VOCABULAIRE DE CONCEPTION, PAS UN SCHÉMA TYPE. Les schémas de redondance "
    "nommés ici sont ceux du métier ; leur qualification en niveau de "
    "disponibilité relève du référentiel Uptime Institute, qui se lit "
    "séparément et ne s'auto-attribue pas. Le dimensionnement, les "
    "protections et la sélectivité relèvent des normes d'installation "
    "citées, dans leur indice en vigueur à la date du marché.")


# ═══════════════════════════════════════════════════════════════════════════
#  3. LES ENJEUX QU'UN CLIENT POSE EN PREMIER
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE CETTE TABLE SERT. Quatre sujets reviennent dans toutes les premières
# réunions : « quel Tier ? », « quel PUE ? », « et l'eau ? », « on est ICPE ? ».
# Y répondre vite et juste est la moitié du travail commercial ; y répondre
# faux engage. Chaque entrée porte donc ce que la notion MESURE, ce qu'elle
# n'atteste pas, et le piège de conversation qui lui est propre.

ENJEUX_DC = {
    "tier": {
        "nom": "Classification Tier (Uptime Institute)",
        "mesure": "La TOPOLOGIE des chaînes d'alimentation et de "
                  "refroidissement : nombre de chemins actifs, capacité de "
                  "maintenance sans interruption, tolérance à la panne unique. "
                  "Quatre niveaux, du chemin unique (I) à la tolérance à la "
                  "panne avec maintenance concurrente (IV).",
        "n_atteste_pas": "Ni la performance énergétique, ni la sécurité "
                         "incendie, ni la conformité réglementaire française. "
                         "Un site Tier IV peut être hors la loi et consommer "
                         "deux fois trop.",
        "piege": "« Tier III » ne s'attribue pas : c'est une certification "
                 "délivrée par l'Uptime Institute, et elle porte SÉPARÉMENT "
                 "sur les documents de conception et sur l'ouvrage construit. "
                 "Écrire « certifié Tier III » pour un site conçu selon les "
                 "principes du niveau III est un risque contractuel, pas une "
                 "approximation commerciale. Et le niveau d'un site est le "
                 "PLUS BAS de ses sous-systèmes, jamais leur moyenne : une "
                 "chaîne électrique tolérante à la panne desservie par une "
                 "production de froid à chemin unique fait un site de "
                 "niveau I.",
        "a_repondre": "Demandez de quel Tier il s'agit : celui du besoin "
                      "métier — combien d'heures d'arrêt le client accepte — "
                      "ou celui d'une certification qu'il compte acheter. Les "
                      "deux réponses ne conduisent pas au même budget. Puis "
                      "demandez les ESSAIS : le référentiel se démontre par "
                      "des épreuves dont l'issue est observable, pas par une "
                      "liste de matériel, et beaucoup de conceptions qui "
                      "passent une liste de contrôle échouent à l'épreuve.",
        "referentiel": "uptime",
    },
    "pue": {
        "nom": "PUE — Power Usage Effectiveness",
        "mesure": "Le rapport entre l'énergie totale consommée par le site et "
                  "l'énergie consommée par le matériel informatique. Un PUE de "
                  "1,3 signifie 30 % d'énergie non informatique : froid, "
                  "pertes de conversion, éclairage, bureaux inclus s'ils sont "
                  "au même comptage.",
        "n_atteste_pas": "Aucune sobriété : un site qui fait tourner des "
                         "serveurs inutiles très efficacement affiche un "
                         "excellent PUE. L'indicateur est un RENDEMENT "
                         "d'infrastructure, pas une mesure d'utilité.",
        "piege": "Un PUE annoncé sans son périmètre de comptage, sa période "
                 "et son taux de charge ne veut rien dire. Le même site "
                 "affiche 1,2 à pleine charge en hiver et 1,6 à 30 % de charge "
                 "en été — sans qu'aucune valeur ne soit fausse.",
        "a_repondre": "Trois questions avant tout chiffre : mesuré ou calculé, "
                      "sur quelle période, et à quel taux de charge. Un PUE "
                      "engagé au marché sans plan de comptage est une clause "
                      "invérifiable, donc inopposable.",
        "referentiel": "en50600",
    },
    "wue": {
        "nom": "WUE — Water Usage Effectiveness",
        "mesure": "Les litres d'eau consommés sur le site par kilowattheure "
                  "informatique. Il rend visible le coût en eau du gain "
                  "énergétique obtenu par voie évaporative.",
        "n_atteste_pas": "L'eau consommée AILLEURS pour produire l'électricité "
                         "du site, qui pèse souvent plus lourd que celle du "
                         "refroidissement et qui dépend du mix électrique du "
                         "pays, pas de la conception du bâtiment.",
        "piege": "La moyenne annuelle lisse la pointe estivale, qui est le "
                 "seul moment qui compte pour une autorité de l'eau : c'est "
                 "en août, sous arrêté de restriction, qu'un site adiabatique "
                 "consomme le plus.",
        "a_repondre": "Présentez la pointe et le profil mensuel, pas la "
                      "moyenne. Et dites si le chiffre couvre l'eau du site "
                      "seule ou l'eau du site et de la production électrique — "
                      "l'écart entre les deux dépasse souvent le facteur dix.",
        "referentiel": "en50600",
    },
    "icpe": {
        "nom": "Réglementation ICPE — installations classées",
        "mesure": "Le régime administratif du site — déclaration, "
                  "enregistrement ou autorisation — selon les rubriques de la "
                  "nomenclature atteintes par les installations : groupes "
                  "électrogènes, stockage de combustible, fluides "
                  "frigorigènes, refroidissement évaporatif, batteries.",
        "n_atteste_pas": "Rien de la qualité technique du projet. C'est une "
                         "autorisation d'exploiter, indépendante du niveau de "
                         "disponibilité visé et de tout référentiel de "
                         "conception.",
        "piege": "Le régime se déclenche sur des SEUILS, et un équipement "
                 "ajouté en cours de projet peut faire basculer le site d'un "
                 "régime à l'autre — d'une déclaration en ligne à une "
                 "autorisation avec enquête publique. Le délai d'instruction "
                 "est alors un jalon de planning qui ne se négocie pas.",
        "a_repondre": "Faites le criblage des rubriques dès l'esquisse, sur "
                      "les puissances et les volumes envisagés, et refaites-le "
                      "à chaque modification du programme. C'est ce que fait "
                      "le module de criblage de cette page — qui pré-qualifie "
                      "et ne classe pas.",
        "referentiel": "icpe",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  4. LES TROIS NATURES DE TRAVAUX
# ═══════════════════════════════════════════════════════════════════════════
# POURQUOI ELLES MANQUAIENT. Le cadre des phases décrivait implicitement une
# CONSTRUCTION NEUVE : programme, esquisse, permis, chantier, réception. Or la
# majorité des opérations de centre de données en France ne sont pas des
# constructions neuves — ce sont des aménagements de coquilles déjà bâties
# (fit-out) et des reprises d'installations en exploitation (rétrofit). Les
# deux ont des phases identiques en NOM et différentes en CONTENU, et c'est
# exactement le genre d'écart qui se découvre au moment du chiffrage.

NATURES_TRAVAUX = {
    "neuf": {
        "nom": "Construction neuve (shell & core puis aménagement)",
        "ce_que_c_est": "Le bâtiment et ses installations sont construits pour "
                        "l'usage : gros œuvre, enveloppe, locaux techniques et "
                        "salles conçus ensemble. Le maître d'ouvrage arbitre "
                        "tout, y compris l'implantation.",
        "phases": "La séquence complète, du programme à la garantie de parfait "
                  "achèvement. Le permis de construire et le dossier ICPE sont "
                  "sur le chemin critique.",
        "risque": "Le délai de raccordement au réseau électrique. Il est "
                  "généralement plus long que le chantier lui-même et ne se "
                  "rattrape par aucun moyen technique.",
        "moe": "Mission complète, architecte inclus. Le lot technique pèse "
               "l'essentiel de l'enveloppe : le chiffrage se fait au kilowatt "
               "informatique, pas au mètre carré.",
    },
    "fit_out": {
        "nom": "Fit-out — aménagement d'une coquille existante",
        "ce_que_c_est": "Le bâtiment existe, souvent livré en « shell & core » "
                        "par un promoteur : structure, enveloppe, dalles, "
                        "parfois l'arrivée électrique. L'opération consiste à "
                        "y installer les salles, la production de froid, la "
                        "distribution électrique et la sûreté.",
        "phases": "La séquence est raccourcie en amont — pas de programme "
                  "bâtiment, pas d'esquisse architecturale — et alourdie en "
                  "aval : les études d'exécution doivent composer avec un "
                  "existant qu'on n'a pas dessiné.",
        "risque": "Les capacités du bâtiment reçu : charge admissible au "
                  "plancher, hauteur libre sous poutre, réservations "
                  "disponibles, puissance du raccordement déjà négociée. Ce "
                  "sont des données d'entrée à RELEVER et à faire confirmer, "
                  "pas à supposer. Un plancher qui ne porte pas les batteries "
                  "prévues se découvre en phase d'exécution et se paie en "
                  "structure.",
        "moe": "La mission bascule vers la synthèse technique et la gestion "
               "d'interface avec le propriétaire du bâtiment. Le bail et son "
               "annexe technique deviennent des pièces d'étude au même titre "
               "que le CCTP.",
    },
    "retrofit": {
        "nom": "Rétrofit — reprise d'une installation en exploitation",
        "ce_que_c_est": "Le site fonctionne et doit continuer à fonctionner. "
                        "On remplace ou on renforce : groupes froid en fin de "
                        "vie, onduleurs, densification de salles, passage au "
                        "refroidissement liquide, mise en conformité.",
        "phases": "Chaque phase se double d'une étude de PHASAGE "
                  "d'exploitation : ce qui se coupe, quand, pendant combien de "
                  "temps, et avec quel repli. C'est cette étude, et non les "
                  "plans, qui décide de la faisabilité.",
        "risque": "L'état réel de l'existant. Les plans d'origine ne "
                  "correspondent plus, les modifications successives ne sont "
                  "pas tracées, et le relevé sur site est la seule donnée "
                  "fiable. Prévoir un relevé et une provision pour "
                  "découvertes n'est pas de la prudence, c'est du chiffrage.",
        "moe": "La mission porte une responsabilité d'exploitation que le neuf "
               "n'a pas : toute intervention sur une installation en service "
               "est un risque d'indisponibilité pour le client final. Les "
               "consignations, les modes dégradés et les procédures de repli "
               "sont des livrables d'étude, pas des documents de chantier.",
    },
}

NATURES_NOTE = (
    "LA NATURE DES TRAVAUX SE DÉCLARE AU DÉBUT. Elle ne change ni le nom des "
    "phases ni la liste des pièces, mais elle change ce qu'il faut y mettre et "
    "où se trouve le risque. Un fit-out chiffré comme un neuf oublie le relevé "
    "de l'existant ; un rétrofit planifié comme un neuf oublie le phasage "
    "d'exploitation, qui est pourtant ce qui décide du délai.")


# ═══════════════════════════════════════════════════════════════════════════
#  LES CONTRÔLES DE COHÉRENCE
# ═══════════════════════════════════════════════════════════════════════════
# Ils portent sur des PROPRIÉTÉS, pas sur des comptes : un nombre figé se
# répare machinalement au premier ajout et cesse alors de vérifier quoi que ce
# soit. Ce qui est vérifié ici, c'est que ce module et le moteur de calcul
# parlent des mêmes familles, et que rien n'y est laissé vide.

_CHAMPS_MODE = ("nom", "principe", "quand", "cout", "contrainte", "erreur")
_CHAMPS_ARCHI = ("nom", "axe", "principe", "ce_qui_decide", "point_faible")
_CHAMPS_ENJEU = ("nom", "mesure", "n_atteste_pas", "piege", "a_repondre")
_CHAMPS_NATURE = ("nom", "ce_que_c_est", "phases", "risque", "moe")
_AXES = ("production", "distribution")


def _verifier():
    """Les fautes de structure de ce module, ou une liste vide.

    LA VÉRIFICATION QUI COMPTE est la dernière : toute famille du moteur de
    calcul doit avoir son explication ici. Sans elle, une famille ajoutée au
    calcul apparaîtrait dans la liste déroulante sans infobulle — et
    l'infobulle manquante est invisible, contrairement à une erreur.
    """
    fautes = []
    for table, champs, nom in ((MODES_REFROIDISSEMENT, _CHAMPS_MODE, "mode"),
                               (ARCHITECTURES_ELEC, _CHAMPS_ARCHI, "architecture"),
                               (ENJEUX_DC, _CHAMPS_ENJEU, "enjeu"),
                               (NATURES_TRAVAUX, _CHAMPS_NATURE, "nature")):
        for cle, v in table.items():
            for c in champs:
                if not (v.get(c) or "").strip():
                    fautes.append("%s %s : champ « %s » vide" % (nom, cle, c))
    for cle, v in ARCHITECTURES_ELEC.items():
        if v.get("axe") not in _AXES:
            fautes.append("architecture %s : axe inconnu (%s)" % (cle, v.get("axe")))
    for axe in _AXES:
        if not any(v.get("axe") == axe for v in ARCHITECTURES_ELEC.values()):
            fautes.append("aucune architecture sur l'axe « %s »" % axe)
    # Un mode sans famille du moteur DOIT dire par quelle famille il est porté,
    # sans quoi le lecteur cherche dans la liste de calcul une option absente.
    for cle, v in MODES_REFROIDISSEMENT.items():
        if not v.get("famille") and not v.get("porte_par"):
            fautes.append("mode %s : ni famille de calcul, ni famille porteuse "
                          "— le lecteur ne saura pas quoi choisir" % cle)
    try:
        import datacenter as _dc
        connues = set(_dc.REFROIDISSEMENT)
    except Exception:                                    # pragma: no cover
        connues = None
    if connues is not None:
        declarees = {v["famille"] for v in MODES_REFROIDISSEMENT.values()
                     if v.get("famille")}
        for f in sorted(connues - declarees):
            fautes.append("famille du moteur sans explication ici : %s" % f)
        for f in sorted(declarees - connues):
            fautes.append("famille expliquée ici et inconnue du moteur : %s" % f)
        for cle, v in MODES_REFROIDISSEMENT.items():
            p = v.get("porte_par")
            if p and p not in connues:
                fautes.append("mode %s : porté par une famille inconnue du "
                              "moteur (%s)" % (cle, p))
    return fautes


_FAUTES = _verifier()
if _FAUTES:
    raise RuntimeError("technique_dc — table incohérente : " + " ; ".join(_FAUTES))


# ═══════════════════════════════════════════════════════════════════════════
#  LE SERVICE AUX PAGES
# ═══════════════════════════════════════════════════════════════════════════

def _nom_dans_la_liste(famille):
    """Le libellé de la famille TEL QU'IL S'AFFICHE dans la liste déroulante.

    LE DÉFAUT CORRIGÉ, et il tenait à un mot. L'infobulle du free-chilling
    disait « se conduit sur "Production d'eau glacée par groupe froid" » — le
    nom que CE module donne au mode. La liste déroulante, elle, est construite
    sur le moteur de calcul, qui l'appelle « Eau glacée avec groupe froid ». On
    envoyait donc le lecteur chercher une option sous un nom qui n'y figure
    pas, c'est-à-dire exactement ce que cette mention existe pour éviter.

    Le nom vient donc du MOTEUR, et de lui seul. Faute de moteur lisible, on
    rend le nom de ce module : une désignation imparfaite vaut mieux qu'une
    clé technique.
    """
    try:
        import datacenter as _dc
        nom = (_dc.REFROIDISSEMENT.get(famille) or {}).get("nom")
        if nom:
            return nom
    except Exception:                                    # pragma: no cover
        pass
    for m in MODES_REFROIDISSEMENT.values():
        if m.get("famille") == famille:
            return m["nom"]
    return famille


def _aide_mode(v):
    """Le texte d'infobulle d'un mode de refroidissement.

    Il suit l'ordre dans lequel on pose les questions en réunion : ce que la
    machine fait, à quelle condition, ce que ça coûte, ce que ça impose, et
    l'erreur à ne pas commettre. La mention de la famille porteuse vient en
    tête quand il y en a une : c'est l'information qui évite de chercher une
    option absente de la liste.
    """
    bouts = []
    p = v.get("porte_par")
    if p:
        bouts.append("Pas une famille du calcul : se conduit sur « %s », "
                     "qu'il faut retenir dans la liste."
                     % _nom_dans_la_liste(p))
    bouts.append(v["principe"])
    bouts.append("Quand — " + v["quand"])
    bouts.append("Ce que ça coûte — " + v["cout"])
    bouts.append("Ce que ça impose — " + v["contrainte"])
    bouts.append("L'erreur classique — " + v["erreur"])
    return "\n\n".join(bouts)


def _aide_archi(v):
    return "\n\n".join([v["principe"],
                        "Ce que ça décide — " + v["ce_qui_decide"],
                        "Le point faible — " + v["point_faible"]])


def _aide_enjeu(v):
    return "\n\n".join([
        "Ce qu'il mesure — " + v["mesure"],
        "Ce qu'il n'atteste pas — " + v["n_atteste_pas"],
        "Le piège — " + v["piege"],
        "Comment répondre — " + v["a_repondre"]])


def _aide_nature(v):
    return "\n\n".join([v["ce_que_c_est"],
                        "Les phases — " + v["phases"],
                        "Le risque propre — " + v["risque"],
                        "La maîtrise d'œuvre — " + v["moe"]])


def glossaire():
    """Les quatre familles d'infobulles servies par ce module.

    Les clés sont celles des tables : le rendu pose data-info="famille:clé" et
    n'a rien à recopier. Reprises et non réécrites — une définition dupliquée
    est une définition qui divergera.
    """
    return {
        "mode_froid": {k: {"nom": v["nom"], "aide": _aide_mode(v)}
                       for k, v in MODES_REFROIDISSEMENT.items()},
        "archi_elec": {k: {"nom": v["nom"], "aide": _aide_archi(v)}
                       for k, v in ARCHITECTURES_ELEC.items()},
        "enjeu": {k: {"nom": v["nom"], "aide": _aide_enjeu(v)}
                  for k, v in ENJEUX_DC.items()},
        "nature_travaux": {k: {"nom": v["nom"], "aide": _aide_nature(v)}
                           for k, v in NATURES_TRAVAUX.items()},
    }


def mode_de_famille(famille):
    """Le mode de refroidissement qui porte une famille du moteur de calcul.

    Rend None plutôt que de lever : une famille inconnue vaut « pas
    d'explication », ce qui se rend par une absence d'infobulle et non par une
    page en erreur.
    """
    for cle, v in MODES_REFROIDISSEMENT.items():
        if v.get("famille") == famille:
            return dict(v, cle=cle)
    return None


def architectures(axe=None):
    """Les architectures électriques, filtrées sur un axe s'il y a lieu."""
    return [dict(v, cle=k) for k, v in ARCHITECTURES_ELEC.items()
            if not axe or v.get("axe") == axe]


def referentiel():
    """Tout ce que ce module sert aux pages, en un seul appel."""
    return {
        "version": VERSION,
        "modes_refroidissement": MODES_REFROIDISSEMENT,
        "modes_source": MODES_SOURCE,
        "architectures_elec": ARCHITECTURES_ELEC,
        "architectures_source": ARCHITECTURES_SOURCE,
        "enjeux": ENJEUX_DC,
        "natures_travaux": NATURES_TRAVAUX,
        "natures_note": NATURES_NOTE,
        "glossaire": glossaire(),
    }
