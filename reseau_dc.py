"""Le raccordement au réseau électrique et la production derrière le compteur.

CE QUE FAIT CE MODULE. Il traite la question qui décide aujourd'hui de la date
de mise sous tension d'un centre de données : à quelles conditions le
gestionnaire de réseau accorde la puissance demandée, et ce qu'il faut
installer sur le site quand il ne l'accorde pas fermement. Il pose les trois
modes de raccordement — ferme, non ferme, hors réseau —, la taxonomie de
flexibilité des charges informatiques, le catalogue des actifs derrière le
compteur, et il CALCULE la part de calcul non servie qui découle d'un
raccordement effaçable, ainsi que son effet sur le résultat d'exploitation.

POURQUOI CE MODULE EXISTE. Le reste de la plateforme dit partout que le délai
de raccordement est le poste le plus long du projet — la spécification HTB, le
conseil d'esquisse, l'échelle de tension du réseau, les postes d'actualisation
des coûts, la nature de site greenfield. Tous le disent EN PROSE. Aucun n'a de
champ, de formule ni de résultat. Et le centre de données comme charge
FLEXIBLE, c'est-à-dire comme quelque chose que le réseau peut demander de
réduire, n'était modélisé nulle part.

LA QUESTION QUE CE MODULE REND CALCULABLE. Accepter un raccordement effaçable
raccourcit l'attente ; il met en risque une part du calcul. Cette part se
chiffre, à partir de grandeurs que le projet connaît : la profondeur et la
fréquence de l'effacement telles qu'elles sont écrites dans la convention, le
taux de charge, la part de charge reportable et la puissance ferme installée
sur le site. Le résultat n'est pas une opinion sur le non ferme ; c'est le
nombre à partir duquel la décision se prend.

CE QU'IL NE FAIT PAS, ET IL FAUT LE LIRE AVANT DE S'EN SERVIR.

  · Il ne PRÉDIT aucun délai de raccordement. Le délai s'obtient par écrit du
    gestionnaire de réseau, pour un point de livraison donné et une puissance
    donnée. Aucune moyenne de marché ne le remplace, et les repères publiés
    que porte l'état de l'art sont des ordres de grandeur de marché, pas une
    réponse sur votre terrain.
  · Il ne chiffre aucun coût de fourniture ni d'investissement. Le coût est
    tenu par les modules d'économie de projet et d'actualisation.
  · Il ne classe pas le site au titre des installations classées. Il PORTE les
    grandeurs de la production sur site au criblage réglementaire, qui reste
    seul à répondre — et qui ne classe pas davantage.

LA CONSÉQUENCE QUE PERSONNE N'ANTICIPE, ET QUI EST LA RAISON D'ÊTRE DU PONT
VERS L'ICPE. Installer de la production sur site pour éviter une file
d'attente de raccordement, c'est remplacer une attente par une procédure
d'autorisation. Les seuils de la rubrique de combustion portent sur la
puissance THERMIQUE — environ deux fois et demie l'électrique — et une pile de
quelques dizaines de mégawatts électriques dépasse largement le seuil de
l'autorisation. Le module rend cet enchaînement visible au moment où la
décision se prend, c'est-à-dire des années avant qu'il ne se constate.
"""

VERSION = "2026-08-a"

HEURES_AN = 8760

RESERVE = (
    "ÉTUDE DE CADRAGE, PAS UNE OFFRE DE RACCORDEMENT. Les conditions d'un "
    "raccordement — puissance accordée, fermeté, profondeur et fréquence "
    "d'effacement, délai de mise à disposition — sont écrites par le "
    "gestionnaire de réseau dans une offre puis dans une convention. Ce module "
    "calcule les CONSÉQUENCES de conditions saisies ; il ne les prévoit pas et "
    "ne se substitue pas à la demande de raccordement. Les repères de marché "
    "cités le sont avec leur auteur, et aucun n'entre dans le calcul.")


# ═══════════════════════════════════════════════════════════════════════════
#  LES TROIS MODES DE RACCORDEMENT
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE CETTE TABLE APPORTE. Le raccordement se discute d'ordinaire comme une
# quantité — combien de mégawatts. Il se décide sur une QUALITÉ : ce que le
# gestionnaire garantit et ce qu'il ne garantit pas. Un même nombre de
# mégawatts, ferme ou effaçable, ne produit pas le même projet, ne se finance
# pas de la même façon et ne s'exploite pas de la même façon.
#
# `repere_delai` renvoie à une clé de l'état de l'art. Les ordres de grandeur
# de délai sont des observations de marché publiées par un tiers : ils sont
# nommés là, avec leur auteur et leur réserve, et ne sont pas recopiés ici.

MODES_RACCORDEMENT = {
    "ferme": {
        "nom": "Raccordement ferme",
        "garantit": "La puissance souscrite est disponible à toute heure. "
                    "L'indisponibilité relève de l'incident, pas de la "
                    "gestion courante du réseau.",
        "ne_garantit_pas": "La DATE. Sur un réseau contraint, c'est "
                           "précisément la fermeté qui fait attendre : la "
                           "puissance ferme suppose que le réseau ait été "
                           "renforcé pour la porter.",
        "ce_qui_fixe_le_delai": "Les travaux de renforcement du réseau amont "
                                "et le rang du projet dans la file d'attente. "
                                "Ni l'un ni l'autre ne dépend du maître "
                                "d'ouvrage.",
        "impose_au_site": "Rien de particulier au-delà des groupes de secours "
                          "qu'exige de toute façon le niveau de disponibilité "
                          "visé.",
        "repere_delai": "bcg_delai_ferme",
    },
    "non_ferme": {
        "nom": "Raccordement non ferme",
        "garantit": "Un accès au réseau plus tôt, sur la capacité existante, "
                    "sans attendre le renforcement.",
        "ne_garantit_pas": "La PUISSANCE, aux heures où le gestionnaire "
                           "appelle l'effacement. C'est la contrepartie "
                           "exacte du délai gagné, et elle est écrite dans la "
                           "convention.",
        "ce_qui_fixe_le_delai": "La capacité résiduelle du réseau existant au "
                                "point demandé. Le renforcement n'étant plus "
                                "sur le chemin, le délai tombe à celui du "
                                "poste de livraison et des travaux propres au "
                                "site.",
        "impose_au_site": "De quoi tenir pendant l'effacement : de la charge "
                          "reportable, de la production ferme sur site, ou "
                          "l'acceptation de ne pas servir une part du calcul. "
                          "Ces trois-là se combinent ; aucune ne se déduit "
                          "des deux autres.",
        "a_ecrire_dans_la_convention": "La PROFONDEUR de l'effacement (quelle "
                                       "part de la puissance est réduite), sa "
                                       "FRÉQUENCE (combien d'heures par an), "
                                       "son PRÉAVIS et sa DURÉE MAXIMALE "
                                       "d'appel consécutif. Sans ces quatre "
                                       "grandeurs, la part de calcul non "
                                       "servie ne se calcule pas — elle se "
                                       "suppose, et une hypothèse d'étude ne "
                                       "s'oppose pas au gestionnaire.",
        "repere_delai": "bcg_delai_non_ferme",
    },
    "hors_reseau": {
        "nom": "Site hors réseau",
        "garantit": "L'indépendance à la file d'attente : le calendrier ne "
                    "dépend plus que de la livraison des actifs de production.",
        "ne_garantit_pas": "L'économie. Toute la production, toute la "
                           "redondance et toute la réserve de combustible "
                           "sont portées par le projet, sans mutualisation "
                           "avec un système électrique.",
        "ce_qui_fixe_le_delai": "La livraison des machines de production et "
                                "l'instruction des autorisations "
                                "d'exploiter — dont celle des installations "
                                "classées, qui devient dimensionnante.",
        "impose_au_site": "Une production complète, sa redondance, son "
                          "combustible et son évacuation de chaleur. Un site "
                          "hors réseau est une centrale électrique qui abrite "
                          "un centre de données.",
        "repere_delai": "bcg_surcout_hors_reseau",
    },
}

MODES_SOURCE = (
    "Cadre d'ingénierie du cabinet. La distinction entre raccordement ferme et "
    "non ferme est celle qu'emploient les gestionnaires de réseau européens "
    "pour ouvrir un accès anticipé sur la capacité existante ; les conditions "
    "exactes, leur dénomination et leur rémunération diffèrent d'un pays et "
    "d'un gestionnaire à l'autre, et s'établissent sur l'offre de "
    "raccordement, pas sur cette table.")


# ═══════════════════════════════════════════════════════════════════════════
#  LES CINQ LEVIERS — ET LEUR CONTREPARTIE
# ═══════════════════════════════════════════════════════════════════════════
# CE QUI FAIT LA VALEUR DE CETTE TABLE, ce ne sont pas les leviers : c'est la
# CONTREPARTIE de chacun. Un levier sans contrepartie est un argument
# commercial ; un levier avec sa contrepartie est un arbitrage, et un arbitrage
# se documente, se chiffre et s'oppose.

LEVIERS = {
    "efficacite": {
        "nom": "Efficacité énergétique",
        "quoi": "Réduire l'énergie consommée à service rendu constant — "
                "refroidissement, chaîne électrique, taux d'utilisation des "
                "calculateurs.",
        "effet_reseau": "Moins de puissance appelée pour le même calcul : "
                        "c'est le seul levier qui réduit la demande au lieu de "
                        "la déplacer ou de la produire ailleurs.",
        "contrepartie": "Il ne libère aucun délai à lui seul. Un gain "
                        "d'efficacité qui n'est pas retiré de la puissance "
                        "DEMANDÉE au gestionnaire ne change rien à la file "
                        "d'attente, et un gain absorbé par une densité accrue "
                        "n'existe pas au bilan.",
    },
    "implantation": {
        "nom": "Implantation par rapport au réseau",
        "quoi": "Choisir le point de raccordement là où la capacité existe — "
                "près d'une production, sur une friche industrielle, dans un "
                "territoire excédentaire.",
        "effet_reseau": "Le renforcement n'est plus nécessaire, ou il est déjà "
                        "programmé pour d'autres motifs.",
        "contrepartie": "La LATENCE et l'écosystème. S'éloigner de la demande "
                        "coûte des millisecondes, et éloigne aussi les "
                        "opérateurs de télécommunications, les entreprises de "
                        "maintenance et la main-d'œuvre d'exploitation.",
    },
    "flexibilite": {
        "nom": "Flexibilité d'exploitation",
        "quoi": "Décaler, suspendre ou déplacer une part de la charge de "
                "calcul quand le réseau le demande.",
        "effet_reseau": "La pointe appelée baisse sans que le calcul annuel "
                        "baisse d'autant : c'est le levier qui rend un "
                        "raccordement non ferme tenable.",
        "contrepartie": "Toutes les charges ne se déplacent pas, et pas à "
                        "toute heure. Le report ne vaut que s'il reste du "
                        "creux pour rattraper : à taux de charge élevé, la "
                        "flexibilité cesse d'agir bien avant d'avoir tout "
                        "absorbé.",
    },
    "conception_raccordement": {
        "nom": "Conception du raccordement",
        "quoi": "Négocier une fermeté partielle, une montée en puissance par "
                "paliers, ou un accès anticipé sur la capacité existante.",
        "effet_reseau": "Le raccordement se dimensionne sur la capacité "
                        "réellement disponible plutôt que sur la pointe "
                        "théorique du site.",
        "contrepartie": "L'indisponibilité du réseau devient un risque "
                        "d'exploitation, donc un risque de revenu. Elle se "
                        "transfère du gestionnaire vers le projet, et elle "
                        "doit se retrouver dans le contrat client.",
    },
    "actifs_site": {
        "nom": "Actifs derrière le compteur",
        "quoi": "Produire ou stocker sur le site, en aval du point de "
                "livraison : moteurs, turbines, piles, photovoltaïque, "
                "éolien, batteries.",
        "effet_reseau": "La puissance appelée au réseau baisse pendant "
                        "l'effacement ; le site devient partiellement "
                        "autonome.",
        "contrepartie": "Une base de coûts, une emprise foncière, des "
                        "autorisations d'exploiter et des émissions. Et un "
                        "second réseau à raccorder si le combustible est du "
                        "gaz — donc un second délai, sur lequel le projet n'a "
                        "pas davantage de prise.",
    },
}

GRID_POSITIF = (
    "CE QUE « POSITIF POUR LE SYSTÈME » VEUT DIRE, et ce n'est pas « vertueux ». "
    "Un site est positif pour le système électrique lorsqu'il déclenche peu "
    "d'investissement supplémentaire de réseau et de production, tout en "
    "répartissant les coûts fixes existants sur une consommation plus grande — "
    "ou, au minimum, lorsque le solde des deux est positif. C'est une "
    "définition ÉCONOMIQUE et vérifiable, pas une qualité morale : elle se "
    "démontre sur le coût évité de renforcement et sur le taux d'utilisation "
    "des ouvrages, deux grandeurs que seul le gestionnaire de réseau détient.")


# ═══════════════════════════════════════════════════════════════════════════
#  LA FLEXIBILITÉ DES CHARGES — CE QUI SE DÉPLACE, ET CE QUI NE SE DÉPLACE PAS
# ═══════════════════════════════════════════════════════════════════════════
# LA FAUTE QUE CETTE TABLE EXISTE POUR EMPÊCHER : annoncer « le centre est
# flexible » à partir d'une moyenne. La flexibilité n'est pas une propriété du
# bâtiment, c'est une propriété de la CHARGE qu'il héberge — et la même salle
# passe de très flexible à pas flexible du tout selon le contrat client signé.

CHARGES = {
    "entrainement": {
        "nom": "Entraînement et affinage de modèles",
        "peut_attendre": "Oui — l'échéance se compte en jours ou en semaines.",
        "peut_etre_suspendue": "Oui, à partir d'un point de reprise. Le coût "
                               "d'une suspension est le travail perdu depuis "
                               "le dernier point, pas la totalité du calcul.",
        "horizon": "jours",
        "part_reportable": 0.80,
        "nature": "hypothese",
        "reserve": "Part d'ordre de grandeur, à remplacer par la politique "
                   "d'ordonnancement réelle de l'exploitant. Elle suppose des "
                   "points de reprise fréquents ; sans eux, une suspension "
                   "coûte beaucoup plus que le temps suspendu.",
    },
    "lots": {
        "nom": "Inférence par lots ou asynchrone",
        "peut_attendre": "Oui, dans une fenêtre inférieure à la journée.",
        "peut_etre_suspendue": "Oui — les travaux sont indépendants et se "
                               "reprennent sans perte.",
        "horizon": "heures",
        "part_reportable": 0.70,
        "nature": "hypothese",
        "reserve": "Suppose que l'engagement de service porte sur la journée "
                   "et non sur l'heure. Un engagement horaire ramène cette "
                   "part près de zéro.",
    },
    "agentique": {
        "nom": "Agents et raisonnement",
        "peut_attendre": "Quelques minutes, pas davantage — un agent qui "
                         "attend une heure a échoué.",
        "peut_etre_suspendue": "Oui, mais la reprise doit être rapide : "
                               "l'état de la session est vivant.",
        "horizon": "minutes",
        "part_reportable": 0.30,
        "nature": "hypothese",
        "reserve": "La fenêtre de quelques minutes ne couvre pas un "
                   "effacement de plusieurs heures : cette part ne vaut que "
                   "pour des appels courts et rapprochés.",
    },
    "interactif": {
        "nom": "Interactif temps réel",
        "peut_attendre": "Non. La réponse est attendue immédiatement.",
        "peut_etre_suspendue": "Non. Une suspension est une indisponibilité "
                               "de service, pas un report.",
        "horizon": "aucun",
        "part_reportable": 0.0,
        "nature": "definition",
        "reserve": "Ce n'est pas une hypothèse basse, c'est la définition de "
                   "la classe : une charge interactive qui se reporte cesse "
                   "d'être interactive.",
    },
}

CHARGES_SOURCE = (
    "Taxonomie du cabinet, bâtie sur deux questions opposables : la charge "
    "peut-elle ATTENDRE, et peut-elle être SUSPENDUE. Les parts reportables "
    "sont des ordres de grandeur déclarés, destinés à être remplacés par la "
    "politique d'ordonnancement de l'exploitant et par les engagements de "
    "service souscrits auprès des clients — ce sont ces derniers qui "
    "décident, pas la nature technique du calcul.")

MECANISMES_FLEX = {
    "temporel": {
        "nom": "Report dans le temps",
        "quoi": "Décaler la charge vers une heure où la puissance est "
                "disponible, sur le même site.",
        "maturite": "En cours de déploiement : les ordonnanceurs savent le "
                    "faire, les contrats commencent à le prévoir.",
        "obstacle": "L'engagement de service. Un report n'est possible que si "
                    "le contrat client l'autorise, et la plupart ne disent "
                    "rien — ce qui vaut interdiction.",
    },
    "spatial": {
        "nom": "Déplacement entre sites",
        "quoi": "Exécuter la charge sur un autre site du parc, où la "
                "puissance est disponible à cette heure.",
        "maturite": "Frontière : techniquement démontré, contractuellement "
                    "rare.",
        "obstacle": "La RÉSIDENCE DES DONNÉES. Un déplacement transfrontalier "
                    "se heurte aux engagements de localisation, et une "
                    "certification de site ne se transporte pas avec la "
                    "charge.",
    },
    "virtuel": {
        "nom": "Effacement par un tiers",
        "quoi": "Une charge industrielle voisine s'efface pour le compte du "
                "centre de données, qui continue de consommer.",
        "maturite": "Frontière : le mécanisme existe sur plusieurs marchés, "
                    "son emploi par des centres de données est nouveau.",
        "obstacle": "Ce n'est pas un réglage interne mais un CONTRAT avec un "
                    "tiers, dont la disponibilité dépend de son propre plan "
                    "de charge industriel. La flexibilité achetée est aussi "
                    "fiable que l'industriel qui la vend.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  LES ACTIFS DERRIÈRE LE COMPTEUR
# ═══════════════════════════════════════════════════════════════════════════
# LE CHAMP QUI DÉCIDE DE TOUT ICI EST `ferme`. Une source intermittente ne
# couvre PAS un effacement : l'effacement est appelé quand le réseau est
# tendu, c'est-à-dire souvent quand il n'y a ni vent ni soleil. Compter du
# photovoltaïque dans la puissance qui tient pendant l'effacement est la faute
# de dimensionnement la plus coûteuse de ce sujet, et le module la refuse.
#
# `icpe` nomme la rubrique de la nomenclature que l'actif déclenche. Le champ
# porte le même nom et le même rôle que dans la table des architectures
# électriques ; un contrôle de démarrage vérifie que la rubrique existe.

BTM = {
    "turbine_gaz": {
        "nom": "Turbine à gaz",
        "axe": "production",
        "ferme": True,
        "quoi": "Production ferme au gaz naturel, en cycle simple, "
                "dimensionnable jusqu'à plusieurs dizaines de mégawatts.",
        "delai": "Long sur les grandes machines : le carnet de commandes des "
                 "constructeurs est le facteur dimensionnant, avant le génie "
                 "civil.",
        "emprise": "Modérée par mégawatt, mais elle appelle un poste de "
                   "détente gaz et une évacuation des fumées.",
        "icpe": "2910",
        "attention": "Elle suppose un RACCORDEMENT AU RÉSEAU DE GAZ, dont le "
                     "délai est instruit par un autre gestionnaire. Éviter "
                     "une file d'attente électrique en entrant dans une file "
                     "d'attente gazière n'est un gain que si on a comparé les "
                     "deux.",
    },
    "moteur_alternatif": {
        "nom": "Moteurs alternatifs",
        "axe": "production",
        "ferme": True,
        "quoi": "Groupes à combustion interne, au gazole ou au gaz, "
                "modulaires et rapides à mettre en œuvre.",
        "delai": "Le plus court des productions fermes : la modularité permet "
                 "une mise en service par tranches.",
        "emprise": "Importante en nombre de machines, et bruyante — "
                   "l'implantation se traite tôt avec l'acoustique et le "
                   "voisinage.",
        "icpe": "2910",
        "attention": "La classe de service décide de ce qui compte : un "
                     "moteur de secours appelé quelques centaines d'heures "
                     "par an n'est plus un moteur de secours, ni au regard "
                     "des émissions, ni au regard de la maintenance.",
    },
    "pile_combustible": {
        "nom": "Piles à combustible",
        "axe": "production",
        "ferme": True,
        "quoi": "Production ferme par conversion électrochimique, au gaz "
                "naturel ou à l'hydrogène.",
        "delai": "Moyen ; la filière est industrialisée mais les volumes "
                 "disponibles restent limités.",
        "emprise": "Importante par mégawatt.",
        "icpe": "2910",
        "attention": "L'approvisionnement en hydrogène décarboné n'est pas "
                     "acquis sur la plupart des territoires : la machine "
                     "existe avant son combustible.",
    },
    "photovoltaique": {
        "nom": "Photovoltaïque sur site",
        "axe": "production",
        "ferme": False,
        "quoi": "Production intermittente, corrélée à l'ensoleillement.",
        "delai": "Court.",
        "emprise": "Très importante rapportée au mégawatt : sur un site de "
                   "centre de données, la toiture ne couvre qu'une fraction "
                   "de pourcent du besoin.",
        "icpe": None,
        "attention": "NE COUVRE PAS UN EFFACEMENT. Elle réduit l'énergie "
                     "achetée sur l'année ; elle ne garantit aucune puissance "
                     "à l'heure où le réseau la retire.",
    },
    "eolien": {
        "nom": "Éolien sur site",
        "axe": "production",
        "ferme": False,
        "quoi": "Production intermittente, corrélée au régime de vent.",
        "delai": "Long : l'autorisation et le recours pèsent plus que le "
                 "montage.",
        "emprise": "Très importante, avec des distances d'éloignement "
                   "réglementaires.",
        "icpe": None,
        "attention": "NE COUVRE PAS UN EFFACEMENT, pour la même raison que le "
                     "photovoltaïque — et la corrélation entre pointe de "
                     "réseau et absence de vent est précisément ce qui crée "
                     "la tension.",
    },
    "batterie_lithium": {
        "nom": "Batteries lithium-ion",
        "axe": "stockage",
        "ferme": True,
        "quoi": "Restitution ferme d'une énergie stockée, sur une durée "
                "limitée par la capacité installée.",
        "delai": "Court, et la filière est la seule dont le coût baisse "
                 "structurellement.",
        "emprise": "Modérée, avec des exigences de sécurité incendie et de "
                   "distances qui pèsent plus que la surface.",
        "icpe": "2925",
        "attention": "FERME MAIS BORNÉE EN DURÉE. Une batterie tient un "
                     "effacement d'une heure, pas d'une journée : sa "
                     "contribution se calcule en énergie, pas seulement en "
                     "puissance, et le module ne la compte comme ferme que "
                     "pour la durée déclarée.",
    },
    "stockage_emergent": {
        "nom": "Stockages de longue durée",
        "axe": "stockage",
        "ferme": True,
        "quoi": "Technologies visant plusieurs heures à plusieurs jours de "
                "restitution — thermique, mécanique, chimies alternatives.",
        "delai": "Incertain : peu de références en exploitation à cette "
                 "échelle.",
        "emprise": "Variable selon la technologie, généralement importante.",
        "icpe": None,
        "attention": "À traiter comme une option à instruire, pas comme une "
                     "solution disponible. Un projet qui en dépend n'a pas de "
                     "solution.",
    },
    "raccordement_gaz": {
        "nom": "Raccordement au réseau de gaz",
        "axe": "liaison",
        "ferme": None,
        "quoi": "L'amenée de gaz sans laquelle turbines, moteurs à gaz et "
                "piles ne produisent pas.",
        "delai": "Instruit par le gestionnaire du réseau de gaz, selon sa "
                 "propre capacité et sa propre file d'attente.",
        "emprise": "Un poste de détente et une servitude de canalisation.",
        "icpe": None,
        "attention": "C'EST UN SECOND DÉLAI SUR UN SECOND RÉSEAU. Il ne "
                     "s'additionne pas au délai électrique, il le REMPLACE — "
                     "et rien ne garantit qu'il soit plus court.",
    },
    "stockage_combustible": {
        "nom": "Stockage de combustible liquide",
        "axe": "liaison",
        "ferme": None,
        "quoi": "Les cuves sans lesquelles une production au gazole ne tient "
                "pas la durée annoncée.",
        "delai": "Court en travaux, long en instruction dès que le volume "
                 "monte.",
        "emprise": "Cuvette de rétention, distances d'éloignement, accès "
                   "pompiers.",
        "icpe": "4734",
        "attention": "LE VOLUME EXPLOSE avec les heures de fonctionnement. "
                     "Douze heures de secours et quelques centaines d'heures "
                     "de production ne sont pas le même ordre de grandeur, et "
                     "le régime administratif suit.",
    },
}

FACTEURS_DIMENSIONNANTS = [
    {"cle": "fermete", "nom": "Fermeté du raccordement obtenu",
     "quoi": "La profondeur et la fréquence de l'effacement écrites dans la "
             "convention. C'est le premier facteur : il fixe le besoin.",
     "qui_le_detient": "Le gestionnaire de réseau, dans son offre."},
    {"cle": "flexibilite_charge", "nom": "Flexibilité propre de la charge",
     "quoi": "La part de calcul réellement reportable, telle que l'autorisent "
             "les engagements de service souscrits.",
     "qui_le_detient": "L'exploitant et ses contrats clients, pas la "
                       "technique."},
    {"cle": "site", "nom": "Contraintes physiques du site",
     "quoi": "L'emprise disponible, l'acoustique, les distances "
             "d'éloignement, l'accès aux réseaux de gaz.",
     "qui_le_detient": "Le terrain, et il ne se négocie pas."},
    {"cle": "livraison", "nom": "Vitesse de livraison des actifs",
     "quoi": "Le carnet de commandes des constructeurs de machines de "
             "production, aujourd'hui plus contraignant que le montage.",
     "qui_le_detient": "Le marché des équipements de production."},
    {"cle": "prix_gaz", "nom": "Prix du gaz",
     "quoi": "Il décide de l'économie d'exploitation d'une production ferme "
             "au gaz, donc de sa taille optimale.",
     "qui_le_detient": "Le marché, et il n'est pas prévisible sur la durée "
                       "d'amortissement des machines."},
    {"cle": "cout_batterie", "nom": "Trajectoire du coût des batteries",
     "quoi": "Elle déplace l'arbitrage entre puissance de production et "
             "capacité de stockage, année après année.",
     "qui_le_detient": "Le marché ; c'est la seule des six grandeurs dont la "
                       "tendance longue soit favorable."},
]

CARBONE_SECOND_ORDRE = (
    "UNE RÉSERVE QUI NOUS APPARTIENT. La littérature de marché traite le "
    "carbone comme un facteur de second ordre dans le dimensionnement de la "
    "production sur site, la vitesse de mise sous tension primant sur tout le "
    "reste. Ce n'est pas la position tenue ailleurs dans cette plateforme : "
    "l'analyse de matérialité et le plan de décarbonation traitent l'intensité "
    "carbone comme un critère de premier rang, et une production fossile sur "
    "site déplace le scope 2 vers le scope 1 — c'est-à-dire vers des émissions "
    "directes, déclarées, et non compensables par un contrat de fourniture. "
    "Les deux lectures se présentent ensemble ; celle qui l'emporte est un "
    "arbitrage de direction, pas un résultat de calcul.")

IMPLANTATIONS = {
    "renforcement_programme": {
        "nom": "Aligné sur un renforcement déjà programmé",
        "quoi": "Le site se pose là où le gestionnaire a déjà décidé de "
                "renforcer, pour d'autres motifs que le projet.",
        "ce_qui_le_rend_possible": "Le schéma de développement du réseau, qui "
                                   "est public et se lit avant de chercher un "
                                   "terrain.",
        "risque": "Le calendrier du renforcement n'est pas un engagement "
                  "envers le projet : il se décale sans que le projet ait "
                  "voix au chapitre.",
    },
    "friche_industrielle": {
        "nom": "Industrie qui se retire",
        "quoi": "Reprendre le raccordement d'un site industriel fermé ou "
                "réduit, dont la puissance est déjà construite.",
        "ce_qui_le_rend_possible": "Le raccordement existe et le poste est "
                                   "là. C'est le chemin le plus court vers la "
                                   "puissance.",
        "risque": "Le transfert du droit de raccordement n'est pas "
                  "automatique, et la dépollution du site peut coûter le "
                  "délai qu'elle fait gagner.",
    },
    "production_nouvelle": {
        "nom": "Production nouvelle à venir",
        "quoi": "S'implanter auprès d'une production en construction, en "
                "s'y raccordant directement ou par le réseau local.",
        "ce_qui_le_rend_possible": "Le producteur cherche un débouché ferme, "
                                   "le centre cherche une puissance : les "
                                   "deux besoins se rencontrent.",
        "risque": "Le calendrier du projet devient celui de la production, et "
                  "un retard de mise en service de celle-ci n'a aucune "
                  "solution de repli.",
    },
    "territoire_excedentaire": {
        "nom": "Territoire déjà en excédent",
        "quoi": "S'implanter là où la production dépasse durablement la "
                "consommation locale.",
        "ce_qui_le_rend_possible": "La capacité est disponible immédiatement, "
                                   "et le site améliore le taux "
                                   "d'utilisation des ouvrages existants.",
        "risque": "L'éloignement de la demande, donc la latence, et souvent "
                  "l'absence d'écosystème d'exploitation sur place.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  LE CALCUL DU CALCUL NON SERVI
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE CETTE FONCTION REND VISIBLE, ET QU'AUCUNE SYNTHÈSE NE REND VISIBLE :
# la flexibilité ne sert QUE s'il reste du creux pour rattraper. Le travail
# reporté doit s'exécuter plus tard, sur une capacité qui n'est pas déjà prise.
# À taux de charge élevé, ce creux se referme, et augmenter la part reportable
# cesse de réduire quoi que ce soit. C'est la borne haute que les études de
# marché constatent sans l'expliquer, et elle sort ici du mécanisme.
#
# TOUS LES TERMES SONT RENDUS. Un chiffre de non-servi dont on ne voit pas la
# décomposition ne se discute pas avec un gestionnaire de réseau ni avec un
# client : il se croit ou il se rejette. Le résultat porte donc chaque terme
# avec son unité et la formule qui le produit.

def _part(v):
    """Une part entre 0 et 1, ou None. Hors bornes vaut illisible, pas borné.

    LA RAISON DE NE PAS BORNER EN SILENCE : une part saisie à 30 pour « 30 % »
    est une faute de saisie fréquente. La ramener à 1 rendrait un résultat
    plausible et faux ; la refuser fait corriger la saisie.
    """
    import math
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f) or f < 0 or f > 1:
        return None
    return f


def _positif(v):
    """Une valeur numérique positive ou nulle, ou None."""
    import math
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f) or f < 0:
        return None
    return f


def part_reportable_du_profil(repartition):
    """La part reportable d'un mélange de charges, pondérée par la taxonomie.

    `repartition` : un dict {classe de charge: part du parc}. Les parts sont
    normalisées et le résultat DIT si elles ne sommaient pas à un — une
    répartition qui somme à 0,6 n'est pas une erreur bénigne : elle signifie
    que 40 % du parc n'a pas été classé, et la moyenne calculée sur les seuls
    60 % déclarés serait présentée comme celle de l'ensemble.
    """
    if not isinstance(repartition, dict) or not repartition:
        return {"nature": "refus", "erreur": "repartition_absente",
                "message": ("Aucune répartition de charges déclarée. La part "
                            "reportable dépend de ce que le site héberge, pas "
                            "de sa technique : sans répartition, elle se "
                            "saisit directement.")}
    inconnues = [k for k in repartition if k not in CHARGES]
    if inconnues:
        return {"nature": "refus", "erreur": "classe_inconnue",
                "message": ("Classe de charge inconnue : %s. Les classes sont "
                            "%s." % (", ".join(sorted(inconnues)),
                                     ", ".join(sorted(CHARGES)))),
                "classes": sorted(CHARGES)}
    parts = {}
    for k, v in repartition.items():
        p = _part(v)
        if p is None:
            return {"nature": "refus", "erreur": "part_illisible",
                    "message": ("Part illisible ou hors de [0 ; 1] pour la "
                                "classe « %s » : « %s ». Les parts se "
                                "saisissent en fraction, pas en pourcentage."
                                % (k, v)),
                    "saisi": str(v)[:20]}
        parts[k] = p
    total = sum(parts.values())
    if total <= 0:
        return {"nature": "refus", "erreur": "repartition_nulle",
                "message": "Toutes les parts déclarées sont nulles : il n'y a "
                           "pas de parc à pondérer."}
    valeur = sum(parts[k] * CHARGES[k]["part_reportable"] for k in parts) / total
    out = {
        "nature": "calcule",
        "part_reportable": valeur,
        "detail": {k: {"part_du_parc": parts[k] / total,
                       "part_reportable_de_la_classe":
                           CHARGES[k]["part_reportable"]} for k in parts},
        "source": CHARGES_SOURCE,
        "calcul": "moyenne des parts reportables, pondérée par la part de "
                  "chaque classe dans le parc",
    }
    if abs(total - 1.0) > 1e-9:
        out["somme_declaree"] = total
        out["alerte"] = (
            "Les parts déclarées somment à %.2f et non à 1. La moyenne a été "
            "calculée sur ce qui est déclaré, donc sur %.0f %% du parc : le "
            "reste n'est pas « non reportable », il est NON CLASSÉ, et la "
            "valeur rendue le suppose semblable au classé."
            % (total, total * 100))
    return out


def calcul_non_servi(profil):
    """La part de calcul non servie qu'entraîne un raccordement effaçable.

    LES ENTRÉES, toutes explicites et aucune inventée :
      · `puissance_it_kw`        la puissance informatique de plaque ;
      · `taux_charge`            la charge moyenne, en fraction de la plaque ;
      · `part_non_ferme`         la part de la puissance qui est effaçable ;
      · `frequence_effacement`   la part des heures de l'année où il est appelé ;
      · `profondeur_effacement`  la part de la puissance effaçable réellement
                                 retirée à l'appel — 1 par défaut, et DIT ;
      · `btm_ferme_kw`           la puissance FERME installée sur le site ;
      · `part_reportable`        la part de charge décalable, ou une
                                 `repartition_charges` qui la pondère.

    CE QUI N'EST PAS UNE ENTRÉE : aucun repère de marché. Les ordres de
    grandeur publiés servent à COMPARER un résultat, jamais à le produire.
    """
    profil = profil if isinstance(profil, dict) else {}
    p_it = _positif(profil.get("puissance_it_kw"))
    u = _part(profil.get("taux_charge"))
    p_nf = _part(profil.get("part_non_ferme"))
    f = _part(profil.get("frequence_effacement"))
    btm = _positif(profil.get("btm_ferme_kw")) or 0.0

    manques = []
    if p_it is None or p_it <= 0:
        manques.append("la puissance informatique installée (kW)")
    if u is None or u <= 0:
        manques.append("le taux de charge moyen, en fraction de la puissance "
                       "installée")
    if p_nf is None:
        manques.append("la part non ferme du raccordement, telle qu'elle est "
                       "écrite dans l'offre du gestionnaire de réseau")
    if f is None:
        manques.append("la fréquence d'appel de l'effacement, en part des "
                       "heures de l'année")
    if manques:
        return {"nature": "incomplet", "manques": manques, "reserve": RESERVE,
                "message": ("Le calcul du non-servi ne se fait pas sur des "
                            "valeurs par défaut : chacune de ces grandeurs "
                            "change le résultat d'un ordre de grandeur, et "
                            "aucune ne se devine.")}

    # La profondeur vaut 1 à défaut — l'effacement retire toute la part non
    # ferme — et le résultat DIT que la valeur a été supposée. Une profondeur
    # partielle est fréquente en convention ; la supposer sans le dire ferait
    # passer une hypothèse favorable pour une donnée.
    d_saisi = profil.get("profondeur_effacement")
    d = _part(d_saisi)
    d_suppose = d is None
    if d_suppose:
        if d_saisi not in (None, ""):
            return {"nature": "refus", "erreur": "profondeur_illisible",
                    "message": ("Profondeur d'effacement illisible ou hors de "
                                "[0 ; 1] : « %s ». Elle se saisit en "
                                "fraction de la part non ferme."
                                % d_saisi),
                    "saisi": str(d_saisi)[:20]}
        d = 1.0

    # La part reportable : saisie directement, ou pondérée par la répartition
    # des charges. La saisie directe l'emporte, et le résultat dit laquelle a
    # servi.
    x = _part(profil.get("part_reportable"))
    origine_x = "part reportable saisie"
    pondere = None
    if x is None and profil.get("repartition_charges"):
        pondere = part_reportable_du_profil(profil.get("repartition_charges"))
        if pondere.get("nature") == "calcule":
            x = pondere["part_reportable"]
            origine_x = "pondérée par la répartition des charges déclarée"
        else:
            return dict(pondere, reserve=RESERVE)
    if x is None:
        x = 0.0
        origine_x = ("aucune part reportable déclarée — le calcul est fait "
                     "SANS report, ce qui est le cas défavorable")

    # ── Les termes, dans l'ordre où ils s'enchaînent ────────────────────────
    dispo = p_it * (1.0 - p_nf * d) + btm      # puissance tenue en effacement
    demande = p_it * u                          # puissance appelée par le calcul
    deficit = max(0.0, demande - dispo)         # kW manquants à l'heure d'appel
    non_servi_brut = f * HEURES_AN * deficit    # kWh/an, avant tout report
    creux = (1.0 - f) * HEURES_AN * max(0.0, p_it - demande)
    reporte = min(non_servi_brut * x, creux)
    non_servi_net = non_servi_brut - reporte
    demande_an = demande * HEURES_AN
    part = (non_servi_net / demande_an) if demande_an else None

    # Le report est-il limité par la flexibilité, ou par le creux ? La réponse
    # change la décision : dans le premier cas, plus de flexibilité aide ;
    # dans le second, elle n'aidera plus, et il faut de la puissance ferme.
    plafonne_par_le_creux = (non_servi_brut * x) > creux + 1e-9
    out = {
        "nature": "calcule",
        "version": VERSION,
        "part_non_servie": part,
        "energie_non_servie_kwh_an": non_servi_net,
        "termes": {
            "puissance_installee_kw": p_it,
            "puissance_tenue_en_effacement_kw": dispo,
            "puissance_appelee_kw": demande,
            "deficit_horaire_kw": deficit,
            "non_servi_brut_kwh_an": non_servi_brut,
            "creux_de_rattrapage_kwh_an": creux,
            "reporte_kwh_an": reporte,
            "non_servi_net_kwh_an": non_servi_net,
            "demande_annuelle_kwh": demande_an,
        },
        "hypotheses": {
            "part_non_ferme": p_nf,
            "frequence_effacement": f,
            "profondeur_effacement": d,
            "profondeur_supposee": d_suppose,
            "taux_charge": u,
            "part_reportable": x,
            "origine_part_reportable": origine_x,
            "btm_ferme_kw": btm,
            "heures_an": HEURES_AN,
        },
        "formules": [
            "puissance tenue = installée × (1 − part non ferme × profondeur) "
            "+ puissance ferme sur site",
            "déficit horaire = max(0 ; appelée − tenue)",
            "non servi brut = fréquence × 8760 × déficit",
            "creux de rattrapage = (1 − fréquence) × 8760 × (installée − appelée)",
            "reporté = min(non servi brut × part reportable ; creux)",
            "part non servie = (brut − reporté) / (appelée × 8760)",
        ],
        "plafonne_par_le_creux": plafonne_par_le_creux,
        "reserve": RESERVE,
        "limite": (
            "L'ANNÉE EST TRAITÉE EN DEUX BLOCS : les heures d'effacement et "
            "les autres. Le calcul ne voit donc pas la FORME de l'effacement, "
            "et deux cents heures continues ne valent pas deux cents heures "
            "dispersées — les premières dépassent l'horizon de report de "
            "toutes les classes de charge, les secondes non. Une série "
            "horaire de charge et d'appels lève cette limite ; c'est la même "
            "donnée qui lève celle du pilotage carbone horaire."),
    }
    if pondere and pondere.get("nature") == "calcule":
        out["ponderation_charges"] = pondere
    if d_suppose:
        out["alerte_profondeur"] = (
            "La profondeur d'effacement n'a pas été saisie : le calcul "
            "suppose que l'appel retire TOUTE la part non ferme. C'est le cas "
            "défavorable. La convention de raccordement dit souvent autre "
            "chose, et cette valeur-là est celle qui compte.")
    out["lecture"] = _lecture_non_servi(out)
    return out


def _lecture_non_servi(r):
    """Ce que le résultat veut dire, en une phrase qui engage."""
    part = r["part_non_servie"]
    t = r["termes"]
    if not part:
        if t["deficit_horaire_kw"] <= 0:
            return ("Aucun calcul n'est perdu : la puissance tenue pendant "
                    "l'effacement couvre la puissance appelée. Ce résultat "
                    "tient à la charge MOYENNE ; vérifiez-le à la pointe, qui "
                    "est le moment où l'effacement est appelé.")
        return ("Le report absorbe la totalité du déficit. Il suppose que le "
                "travail décalé s'exécute effectivement plus tard, et que les "
                "engagements de service l'autorisent.")
    bouts = ["Environ %.1f %% du calcul annuel n'est pas servi." % (part * 100)]
    if r["plafonne_par_le_creux"]:
        bouts.append(
            "LE REPORT EST PLAFONNÉ PAR LE CREUX, pas par la flexibilité : "
            "augmenter la part de charge décalable ne réduira plus rien, "
            "parce qu'il ne reste pas assez d'heures libres pour rattraper. "
            "À ce point, seule de la puissance ferme sur site agit encore.")
    elif r["hypotheses"]["part_reportable"] > 0:
        bouts.append(
            "Le report n'est pas encore limité par le creux : de la "
            "flexibilité supplémentaire réduirait encore ce chiffre.")
    if r["hypotheses"]["btm_ferme_kw"] <= 0:
        bouts.append(
            "Aucune puissance ferme sur site n'est déclarée. C'est le levier "
            "qui ferme l'écart quand la flexibilité ne le peut plus — et "
            "celui qui déclenche les rubriques d'installation classée.")
    return " ".join(bouts)


# ═══════════════════════════════════════════════════════════════════════════
#  L'EFFET SUR LE RÉSULTAT D'EXPLOITATION
# ═══════════════════════════════════════════════════════════════════════════

def effet_sur_la_marge(part_non_servie, marge_operationnelle):
    """Ce que coûte, en résultat, un point de calcul non servi.

    L'ÉLASTICITÉ SE DÉDUIT, ELLE NE S'IMPORTE PAS. Les coûts fixes d'un centre
    de données ne baissent pas quand le revenu baisse : bâtiment, chaîne
    électrique, amortissement des calculateurs et personnel restent dus. Un
    point de revenu perdu est donc un point de résultat perdu en valeur
    absolue, ce qui représente 1/marge point de résultat en relatif.

    C'est pourquoi ce module ne porte AUCUNE constante d'élasticité : une
    constante recopiée d'une étude serait celle de la structure de coûts de
    cette étude, appliquée en silence à un projet qui n'a pas la même.
    """
    s = _part(part_non_servie)
    m = _part(marge_operationnelle)
    if s is None:
        return {"nature": "refus", "erreur": "part_illisible",
                "message": ("Part de calcul non servie illisible ou hors de "
                            "[0 ; 1] : « %s »." % part_non_servie),
                "saisi": str(part_non_servie)[:20]}
    if m is None or m <= 0 or m >= 1:
        return {"nature": "refus", "erreur": "marge_illisible",
                "message": ("Marge opérationnelle illisible ou hors de "
                            "]0 ; 1[ : « %s ». Elle ne se devine pas : "
                            "l'élasticité en dépend entièrement, et une marge "
                            "par défaut ferait passer la structure de coûts "
                            "d'un autre projet pour celle-ci."
                            % marge_operationnelle),
                "saisi": str(marge_operationnelle)[:20]}
    elasticite = 1.0 / m
    return {
        "nature": "calcule",
        "elasticite": elasticite,
        "marge_operationnelle": m,
        "part_non_servie": s,
        "perte_de_resultat_relative": s * elasticite,
        "calcul": ("élasticité = 1 / marge ; perte relative de résultat = "
                   "part non servie × élasticité"),
        "pourquoi": ("Les coûts fixes ne baissent pas avec le revenu. Un "
                     "point de calcul non servi est un point de revenu perdu, "
                     "et il se retranche d'un résultat qui ne représente "
                     "qu'une fraction du revenu."),
        "lecture": ("Un point de calcul non servi coûte %.2f point de "
                    "résultat. Sur %.1f %% de calcul non servi, le résultat "
                    "recule de %.1f %% en relatif."
                    % (elasticite, s * 100, s * elasticite * 100)),
        "limite": ("Le raisonnement suppose que le revenu est proportionnel "
                   "au calcul servi et que rien dans les coûts ne varie avec "
                   "lui. Un contrat client qui prévoit des pénalités "
                   "d'indisponibilité aggrave le résultat au-delà de ce "
                   "calcul ; une part de coût réellement variable "
                   "l'atténue."),
        "reserve": RESERVE,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  LE PONT VERS LES MODULES VOISINS
# ═══════════════════════════════════════════════════════════════════════════
# C'EST ICI QUE CE MODULE GAGNE SON EXISTENCE. Le calcul du non-servi se
# ferait sur un tableur ; l'enchaînement qui suit, non — parce qu'il suppose
# de connaître en même temps la nomenclature des installations classées, les
# classes de service des groupes et les règles du niveau de disponibilité
# visé. C'est cet enchaînement qui se découvre trop tard sur les projets.

def consequences_btm(profil):
    """Ce que la production sur site déclenche, ailleurs que sur la facture.

    TROIS CONSÉQUENCES, et aucune n'est intuitive :

      · le RÉGIME ADMINISTRATIF bascule, parce que les seuils de la rubrique
        de combustion portent sur la puissance thermique et qu'une pile de
        production dépasse d'un ordre de grandeur des groupes de secours ;
      · le COMBUSTIBLE choisi déplace la contrainte au lieu de la supprimer —
        le gazole fait exploser le volume stocké, le gaz appelle un second
        raccordement sur un second réseau ;
      · la CAPACITÉ QUALIFIANTE au titre du niveau de disponibilité n'est pas
        la puissance installée, et une pile dimensionnée pour tenir un
        effacement ne satisfait pas pour autant l'exigence de secours.
    """
    profil = profil if isinstance(profil, dict) else {}
    p_btm = _positif(profil.get("btm_puissance_elec_kw"))
    combustible = (profil.get("btm_combustible") or "").strip().lower() or None
    heures = _positif(profil.get("btm_heures_an"))

    out = {"nature": "calcule", "version": VERSION, "reserve": RESERVE,
           "manques": [], "alertes": []}

    if p_btm is None or p_btm <= 0:
        out["nature"] = "incomplet"
        out["manques"].append(
            "la puissance électrique installée de la production sur site "
            "(kW) — sans elle, aucune conséquence administrative ne se "
            "crible")
        return out

    # ── Le régime administratif, avec et sans la production sur site ────────
    try:
        import icpe_dc
    except Exception:                                    # pragma: no cover
        icpe_dc = None
    if icpe_dc is not None:
        secours = _positif(profil.get("groupes_puissance_elec_kw")) or 0.0
        sans = icpe_dc.cribler(profil)
        enrichi = dict(profil)
        enrichi["groupes_puissance_elec_kw"] = secours + p_btm
        # La puissance thermique saisie ne vaut que pour les groupes de
        # secours : la laisser ferait ignorer la production ajoutée, et le
        # criblage rendrait le régime d'avant en le présentant comme celui
        # d'après. On la retire pour forcer la conversion sur le total.
        enrichi.pop("groupes_puissance_thermique_mw", None)
        avec = icpe_dc.cribler(enrichi)
        bascule = sans["regime_site"] != avec["regime_site"]
        out["icpe"] = {
            "regime_sans_production": sans["regime_site"],
            "regime_sans_production_nom": sans["regime_site_detail"]["nom"],
            "regime_avec_production": avec["regime_site"],
            "regime_avec_production_nom": avec["regime_site_detail"]["nom"],
            "bascule": bascule,
            "declenchees": avec["declenchees"],
            "a_verifier": avec["a_verifier"],
            "puissance_elec_cumulee_kw": secours + p_btm,
            "reserve": avec["reserve"],
        }
        if bascule:
            out["alertes"].append(
                "LE RÉGIME ADMINISTRATIF BASCULE de « %s » à « %s » du seul "
                "fait de la production sur site. Le délai d'instruction "
                "correspondant entre au chemin critique du programme, et il "
                "se compare au délai de raccordement qu'on cherchait à "
                "éviter : c'est cette comparaison-là qui décide, pas le "
                "délai de raccordement seul."
                % (sans["regime_site_detail"]["nom"],
                   avec["regime_site_detail"]["nom"]))
        # L'allègement lié au faible nombre d'heures ne vaut plus.
        if heures is None:
            out["manques"].append(
                "le nombre d'heures de fonctionnement annuel de la production "
                "sur site — c'est lui qui décide si les exigences allégées "
                "des moteurs de secours s'appliquent encore")
        out["allegement_heures"] = (
            "L'ALLÈGEMENT NE S'APPLIQUE PLUS. Les exigences d'émission "
            "réduites que la nomenclature reconnaît aux moteurs de SECOURS "
            "tiennent à leur très faible nombre d'heures. Une machine appelée "
            "pour tenir un effacement fonctionne, elle ne secourt pas : "
            "l'allègement tombe avec les heures, et les valeurs limites "
            "d'émission applicables sont à instruire sur le régime réel de "
            "fonctionnement.")

    # ── Le combustible : la contrainte se déplace, elle ne disparaît pas ────
    if combustible not in ("gaz", "gazole"):
        out["manques"].append(
            "le combustible de la production sur site — « gaz » ou "
            "« gazole ». Le choix ne change pas le régime de combustion, il "
            "change ce qui l'accompagne : un stockage à instruire d'un côté, "
            "un raccordement à obtenir de l'autre")
    elif combustible == "gazole":
        out["combustible"] = _volume_gazole(p_btm, heures)
    else:
        out["combustible"] = {
            "voie": "gaz",
            "stockage": "Aucun stockage de combustible liquide au titre de la "
                        "production sur site — donc pas de rubrique de "
                        "stockage à ce titre. Les cuves des groupes de "
                        "secours restent, elles, à cribler.",
            "en_echange": BTM["raccordement_gaz"]["attention"],
            "a_obtenir": ("La capacité et le délai de raccordement au réseau "
                          "de gaz, par écrit, auprès de son gestionnaire — "
                          "au même titre et au même moment que la demande de "
                          "raccordement électrique."),
        }

    # ── Le double emploi : tenir un effacement n'est pas secourir ───────────
    out["duty"] = _duty_tier(profil, p_btm)
    return out


def _volume_gazole(p_btm_kw, heures):
    """Le volume de gazole qu'appelle une production sur site, et son régime.

    LA COMPARAISON QUI COMPTE est celle avec la réserve exigée au titre du
    niveau de disponibilité : douze heures à la capacité N. Les deux volumes
    ne sont pas du même ordre, et c'est le grand qui décide du régime
    administratif — pas celui que le dossier de disponibilité met en avant.
    """
    try:
        import tier_dc
    except Exception:                                    # pragma: no cover
        return {"voie": "gazole", "manque": "le module de disponibilité n'est "
                                            "pas lisible sur ce serveur"}
    conso = tier_dc.CONSO_SPECIFIQUE_L_KWH
    out = {"voie": "gazole",
           "consommation_specifique_l_kwh": conso,
           "source": tier_dc.CONSO_SOURCE,
           "reserve_tier_m3": p_btm_kw * conso * tier_dc.AUTONOMIE_H / 1000.0,
           "heures_tier": tier_dc.AUTONOMIE_H}
    if heures is None or heures <= 0:
        out["manque"] = ("le nombre d'heures de fonctionnement annuel : sans "
                         "lui, le volume à stocker ne se calcule pas")
        return out
    m3 = p_btm_kw * conso * heures / 1000.0
    out["volume_m3"] = m3
    out["heures"] = heures
    out["calcul"] = ("volume = puissance électrique × consommation spécifique "
                     "× heures de fonctionnement")
    out["rapport_a_la_reserve_tier"] = (
        (heures / tier_dc.AUTONOMIE_H) if tier_dc.AUTONOMIE_H else None)
    out["note"] = (
        "Volume pour tenir les heures déclarées SANS réapprovisionnement. Un "
        "approvisionnement en cours de fonctionnement le réduit — et devient "
        "alors une dépendance logistique à traiter comme telle, avec ses "
        "propres aléas."
    )
    # Au-delà du plus haut seuil criblé, la question n'est plus la rubrique.
    try:
        import icpe_dc
        d = icpe_dc._densite_gazole()
        seuils = icpe_dc.RUBRIQUES["4734"]["seuils"]
        plafond = max(b for b, _h, _r in seuils)
    except Exception:                                    # pragma: no cover
        d, plafond = None, None
    if d and plafond:
        tonnes = m3 * d / 1000.0
        out["tonnes"] = tonnes
        out["plafond_criblage_t"] = plafond
        if tonnes > plafond:
            out["hors_perimetre"] = (
                "SORTIE DU PÉRIMÈTRE CRIBLÉ. Le tonnage dépasse le plus haut "
                "seuil que porte le criblage de ce dépôt : à ce niveau, la "
                "question n'est plus seulement le régime de la rubrique de "
                "stockage mais l'application de la réglementation des sites "
                "à risque d'accident majeur, que ce module NE TRAITE PAS. "
                "C'est un sujet de bureau d'études spécialisé, et il se pose "
                "avant le choix du combustible, pas après.")
    elif not d:
        out["tonnes_manque"] = (
            "la masse volumique du gazole n'est pas lisible sur ce serveur : "
            "le tonnage, donc le régime, n'est pas calculé")
    return out


def _duty_tier(profil, p_btm_kw):
    """Deux besoins, deux résultats — et surtout, jamais un seul.

    LA CONFUSION QUE CETTE FONCTION EXISTE POUR EMPÊCHER : « nous avons
    installé quarante mégawatts sur site, la redondance est couverte ». Tenir
    un effacement est un service de LONGUE DURÉE, que seule une classe de
    service sans limite d'heures satisfait ; secourir est un service de courte
    durée à la capacité N. Une même machine peut faire les deux, mais elle ne
    le fait pas par hasard : cela se décide à l'achat, et se lit sur la classe.
    """
    try:
        import tier_dc
    except Exception:                                    # pragma: no cover
        return {"manque": "le module de disponibilité n'est pas lisible"}
    classe = profil.get("btm_classe_iso")
    if not classe:
        return {"manque": ("la classe de service de la production sur site — "
                           "c'est elle qui décide si ces kilowatts comptent "
                           "pour le niveau de disponibilité visé, et une "
                           "machine de secours n'y compte pas"),
                "classes": sorted(tier_dc.CLASSES_GROUPE),
                "pourquoi": _DUTY_POURQUOI}
    q = tier_dc.capacite_qualifiante_groupes(
        p_btm_kw, classe, profil.get("btm_certifiee_kw"))
    if q.get("nature") == "refus":
        return dict(q, pourquoi=_DUTY_POURQUOI)
    return {
        "nature": "calcule",
        "qualifiante": q,
        "pourquoi": _DUTY_POURQUOI,
        "lecture": (
            "Sur %.0f kW installés, %.0f kW comptent pour le niveau de "
            "disponibilité (%s). Les kilowatts qui ne comptent pas ne sont "
            "pas perdus : ils tiennent l'effacement. Mais ils ne tiennent que "
            "cela, et le dossier de disponibilité ne doit pas les afficher."
            % (q["puissance_nominale_kw"], q["qualifiante_kw"], q["origine"])),
    }


_DUTY_POURQUOI = (
    "DEUX BESOINS DISTINCTS, ET ILS NE SE CONFONDENT PAS. Tenir un effacement "
    "demande de fonctionner longtemps et souvent : seule une classe de "
    "service sans limite d'heures y répond, et une classe intermédiaire doit "
    "être déclassée. Secourir demande de démarrer vite et de tenir la "
    "capacité N le temps de la réserve exigée. Une pile dimensionnée pour "
    "l'un ne satisfait pas l'autre par construction, et l'écart ne se "
    "constate qu'à l'essai intégré — c'est-à-dire à la fin.")


# ═══════════════════════════════════════════════════════════════════════════
#  L'ÉTUDE COMPLÈTE — CE QUE SERT LA ROUTE
# ═══════════════════════════════════════════════════════════════════════════

def etudier(profil):
    """Le mode retenu, le calcul non servi, son effet marge, et l'ICPE.

    LES QUATRE RÉSULTATS SE PRÉSENTENT ENSEMBLE, et c'est le point. Pris
    séparément, chacun se lit à l'avantage de la décision qu'on avait déjà
    prise : le délai gagné sans le calcul perdu, le calcul perdu sans le
    délai gagné, la production sur site sans son régime administratif.
    """
    profil = profil if isinstance(profil, dict) else {}
    mode = (profil.get("mode_raccordement") or "").strip().lower() or None
    out = {"version": VERSION, "reserve": RESERVE}

    if mode and mode not in MODES_RACCORDEMENT:
        return {"nature": "refus", "erreur": "mode_inconnu",
                "message": ("Mode de raccordement inconnu : « %s ». Les modes "
                            "sont %s." % (profil.get("mode_raccordement"),
                                          ", ".join(MODES_RACCORDEMENT))),
                "modes": sorted(MODES_RACCORDEMENT), "reserve": RESERVE}
    if mode:
        out["mode"] = dict(MODES_RACCORDEMENT[mode], cle=mode)
        out["mode"]["repere"] = _repere(MODES_RACCORDEMENT[mode]
                                        .get("repere_delai"))

    ns = calcul_non_servi(profil)
    out["non_servi"] = ns
    if ns.get("nature") == "calcule" and profil.get("marge_operationnelle") is not None:
        out["marge"] = effet_sur_la_marge(ns["part_non_servie"],
                                          profil.get("marge_operationnelle"))
    if profil.get("btm_puissance_elec_kw"):
        out["production_sur_site"] = consequences_btm(profil)
    return out


def _repere(cle):
    """Le repère de marché associé à un mode, lu à l'état de l'art.

    IL NE REVIENT PAS DANS LE CALCUL. Il s'affiche à côté du résultat, avec
    son auteur et sa réserve, pour que le lecteur situe le cas étudié dans ce
    qui s'observe ailleurs — et rien de plus. Une valeur publiée par un tiers
    qui entrerait dans une formule y entrerait sans que personne ne le voie.
    """
    if not cle:
        return None
    try:
        import etat_art
        fait = next((f for f in etat_art.FAITS if f["cle"] == cle), None)
        if not fait:
            return None
        src = etat_art.SOURCES.get(fait["source"], {})
        return {
            "enonce": fait["enonce"],
            "editeur": src.get("editeur"),
            "date": src.get("date"),
            "nature": etat_art.NATURES.get(src.get("nature"), {}).get("nom"),
            "poids": etat_art.NATURES.get(src.get("nature"), {}).get("poids"),
            "page": fait.get("page"),
            "reserve": fait.get("reserve"),
            "n_entre_pas_dans_le_calcul": True,
        }
    except Exception:                                    # pragma: no cover
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  LES CHAMPS DE SAISIE
# ═══════════════════════════════════════════════════════════════════════════
# AUCUN CHAMP NE PORTE DE VALEUR PAR DÉFAUT. Sur ce sujet plus qu'ailleurs,
# une valeur par défaut deviendrait la réponse : personne ne conteste un
# formulaire déjà rempli, et une fréquence d'effacement supposée fait basculer
# le résultat d'un facteur trois sans que personne ne s'en aperçoive.

CHAMPS = [
    {"id": "mode_raccordement", "label": "Mode de raccordement envisagé",
     "type": "choix", "options": list(MODES_RACCORDEMENT),
     "aide": "Ferme, non ferme, ou hors réseau. Le mode se lit sur l'offre du "
             "gestionnaire de réseau ; tant qu'aucune offre n'est reçue, il "
             "s'agit d'une hypothèse d'étude et le dossier doit le dire."},
    {"id": "puissance_it_kw", "label": "Puissance informatique installée",
     "unite": "kW", "type": "nombre",
     "aide": "La puissance de plaque du parc informatique, hors "
             "refroidissement et hors pertes de la chaîne électrique."},
    {"id": "taux_charge", "label": "Taux de charge moyen",
     "unite": "0–1", "type": "nombre",
     "aide": "La charge moyenne rapportée à la puissance installée. C'est "
             "elle qui décide du creux disponible pour rattraper un report : "
             "plus elle est haute, moins la flexibilité agit."},
    {"id": "part_non_ferme", "label": "Part non ferme du raccordement",
     "unite": "0–1", "type": "nombre",
     "aide": "La part de la puissance souscrite que le gestionnaire peut "
             "réduire. Elle se lit dans l'offre de raccordement, pas dans une "
             "moyenne de marché."},
    {"id": "frequence_effacement", "label": "Fréquence d'appel de l'effacement",
     "unite": "0–1", "type": "nombre",
     "aide": "La part des heures de l'année où l'effacement est appelé — 0,10 "
             "pour un dixième de l'année, soit environ 876 heures. C'est une "
             "clause de convention, pas une prévision météorologique."},
    {"id": "profondeur_effacement", "label": "Profondeur de l'effacement",
     "unite": "0–1", "type": "nombre",
     "aide": "La part de la puissance non ferme réellement retirée à chaque "
             "appel. Non renseignée, le calcul suppose la totalité — le cas "
             "défavorable — et le dit dans son résultat."},
    {"id": "part_reportable", "label": "Part de la charge reportable",
     "unite": "0–1", "type": "nombre",
     "aide": "La part du calcul qui peut être décalée dans le temps sans "
             "manquer un engagement de service. À défaut, elle se pondère par "
             "la répartition des classes de charge hébergées."},
    {"id": "btm_ferme_kw", "label": "Puissance ferme disponible sur le site",
     "unite": "kW", "type": "nombre",
     "aide": "La puissance qui TIENT pendant l'effacement : production "
             "pilotable et stockage. Le photovoltaïque et l'éolien n'en font "
             "pas partie — l'effacement est appelé quand le réseau est tendu, "
             "c'est-à-dire souvent sans vent ni soleil."},
    {"id": "btm_puissance_elec_kw",
     "label": "Puissance électrique des machines de production sur site",
     "unite": "kW", "type": "nombre",
     "aide": "La puissance installée des machines à combustion, qui décide du "
             "criblage réglementaire. Elle diffère de la précédente : une "
             "batterie tient un effacement sans être une machine à "
             "combustion."},
    {"id": "btm_combustible", "label": "Combustible de la production sur site",
     "type": "choix", "options": ["gaz", "gazole"],
     "aide": "Le choix ne change pas la rubrique de combustion ; il change ce "
             "qui l'accompagne — un stockage à instruire pour le gazole, un "
             "raccordement à obtenir pour le gaz."},
    {"id": "btm_heures_an", "label": "Heures de fonctionnement annuel prévues",
     "unite": "h/an", "type": "nombre",
     "aide": "Le nombre d'heures pour lesquelles la production sur site est "
             "appelée. C'est lui qui fait tomber les exigences allégées "
             "reconnues aux moteurs de secours, et lui qui dimensionne le "
             "stockage de combustible."},
    {"id": "btm_classe_iso", "label": "Classe de service des machines",
     "type": "choix", "options": ["continu", "prime", "secours"],
     "aide": "La classe décide de ce qui compte pour le niveau de "
             "disponibilité visé. Une machine de secours ne compte pas, quel "
             "que soit le rôle qu'on lui donne par ailleurs."},
    {"id": "btm_certifiee_kw",
     "label": "Puissance certifiée sans limite de durée",
     "unite": "kW", "type": "nombre",
     "aide": "Si le constructeur atteste une capacité tenable sans limite "
             "d'heures, elle l'emporte sur le déclassement par défaut de la "
             "classe."},
    {"id": "marge_operationnelle", "label": "Marge opérationnelle attendue",
     "unite": "0–1", "type": "nombre",
     "aide": "Le résultat d'exploitation rapporté au revenu. Elle décide "
             "entièrement de ce que coûte un point de calcul non servi, et "
             "aucune valeur par défaut ne la remplace : celle d'un autre "
             "projet donnerait un chiffre faux d'aspect juste."},
]


# ═══════════════════════════════════════════════════════════════════════════
#  LE GLOSSAIRE ET LE RÉFÉRENTIEL
# ═══════════════════════════════════════════════════════════════════════════

def modes():
    """Les modes de raccordement, avec leur repère de marché résolu."""
    return [dict(v, cle=k, repere=_repere(v.get("repere_delai")))
            for k, v in MODES_RACCORDEMENT.items()]


def glossaire():
    """Les familles d'infobulles servies par ce module.

    Elles ne recouvrent aucune famille voisine : le raccordement est nommé
    dans la table des architectures électriques comme un ORGANE, et ici comme
    un CONTRAT. Un contrôle de démarrage refuse qu'une famille soit
    revendiquée deux fois.
    """
    return {
        "mode_raccordement": {k: {
            "nom": v["nom"],
            "aide": ("Ce que le gestionnaire garantit — %s\n\nCe qu'il ne "
                     "garantit pas — %s\n\nCe qui fixe le délai — %s\n\nCe "
                     "que le mode impose au site — %s\n\n%s"
                     % (v["garantit"], v["ne_garantit_pas"],
                        v["ce_qui_fixe_le_delai"], v["impose_au_site"],
                        MODES_SOURCE)),
        } for k, v in MODES_RACCORDEMENT.items()},
        "levier_reseau": {k: {
            "nom": v["nom"],
            "aide": ("%s\n\nEffet sur le réseau — %s\n\nLa contrepartie — %s"
                     % (v["quoi"], v["effet_reseau"], v["contrepartie"])),
        } for k, v in LEVIERS.items()},
        "charge_flex": {k: {
            "nom": v["nom"],
            "aide": ("Peut-elle attendre — %s\n\nPeut-elle être suspendue — "
                     "%s\n\nPart reportable retenue — %.0f %% (%s)\n\n%s\n\n%s"
                     % (v["peut_attendre"], v["peut_etre_suspendue"],
                        v["part_reportable"] * 100, v["nature"],
                        v["reserve"], CHARGES_SOURCE)),
        } for k, v in CHARGES.items()},
        "btm": {k: {
            "nom": v["nom"],
            "aide": ("%s\n\nTient-il pendant un effacement — %s\n\nDélai "
                     "d'obtention — %s\n\nEmprise — %s\n\nÀ savoir — %s"
                     % (v["quoi"],
                        "oui" if v["ferme"] is True else
                        "non" if v["ferme"] is False else
                        "ce n'est pas une source, c'est ce qui la rend "
                        "possible",
                        v["delai"], v["emprise"], v["attention"])),
        } for k, v in BTM.items()},
    }


def referentiel():
    """Les tables, sans calcul — pour la page et la documentation."""
    return {
        "version": VERSION,
        "reserve": RESERVE,
        "modes": modes(),
        "modes_source": MODES_SOURCE,
        "leviers": LEVIERS,
        "grid_positif": GRID_POSITIF,
        "charges": CHARGES,
        "charges_source": CHARGES_SOURCE,
        "mecanismes": MECANISMES_FLEX,
        "btm": BTM,
        "facteurs": FACTEURS_DIMENSIONNANTS,
        "carbone_second_ordre": CARBONE_SECOND_ORDRE,
        "implantations": IMPLANTATIONS,
        "champs": CHAMPS,
        "glossaire": glossaire(),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  LES CONTRÔLES DE COHÉRENCE
# ═══════════════════════════════════════════════════════════════════════════

def _verifier():
    """Les fautes de structure, ou une liste vide.

    LES DEUX VÉRIFICATIONS QUI COMPTENT sont des RENVOIS, parce que ce sont
    les seules fautes que la relecture ne voit pas :

      · une rubrique d'installation classée citée par un actif de production
        doit exister dans la nomenclature criblée — sinon l'actif annonce une
        conséquence administrative qui ne sera jamais criblée ;
      · un repère de marché cité par un mode de raccordement doit exister dans
        l'état de l'art — sinon le mode s'affiche sans son ordre de grandeur,
        en silence, et le lecteur conclut qu'il n'y en a pas.
    """
    fautes = []
    for k, v in MODES_RACCORDEMENT.items():
        for champ in ("nom", "garantit", "ne_garantit_pas",
                      "ce_qui_fixe_le_delai", "impose_au_site"):
            if not (v.get(champ) or "").strip():
                fautes.append("mode %s : champ « %s » vide" % (k, champ))
    for k, v in LEVIERS.items():
        for champ in ("nom", "quoi", "effet_reseau", "contrepartie"):
            if not (v.get(champ) or "").strip():
                fautes.append("levier %s : champ « %s » vide" % (k, champ))
    for k, v in CHARGES.items():
        for champ in ("nom", "peut_attendre", "peut_etre_suspendue",
                      "horizon", "nature", "reserve"):
            if not (v.get(champ) or "").strip():
                fautes.append("charge %s : champ « %s » vide" % (k, champ))
        p = v.get("part_reportable")
        if not isinstance(p, (int, float)) or not (0.0 <= p <= 1.0):
            fautes.append("charge %s : part reportable hors de [0 ; 1] (%s)"
                          % (k, p))
    for k, v in MECANISMES_FLEX.items():
        for champ in ("nom", "quoi", "maturite", "obstacle"):
            if not (v.get(champ) or "").strip():
                fautes.append("mécanisme %s : champ « %s » vide" % (k, champ))
    for k, v in BTM.items():
        for champ in ("nom", "axe", "quoi", "delai", "emprise", "attention"):
            if not (v.get(champ) or "").strip():
                fautes.append("actif %s : champ « %s » vide" % (k, champ))
        if v.get("axe") not in ("production", "stockage", "liaison"):
            fautes.append("actif %s : axe inconnu (%s)" % (k, v.get("axe")))
        if v.get("ferme") not in (True, False, None):
            fautes.append("actif %s : la fermeté n'est ni oui, ni non, ni "
                          "sans objet" % k)
    # Au moins un actif de chaque axe : une table qui perdrait son axe de
    # liaison laisserait croire qu'une turbine se pose sans amenée de gaz.
    for axe in ("production", "stockage", "liaison"):
        if not any(v.get("axe") == axe for v in BTM.values()):
            fautes.append("aucun actif sur l'axe « %s »" % axe)
    # Et au moins un actif NON ferme : c'est la distinction que la table
    # existe pour porter, et une table dont tout serait ferme la perdrait.
    if not any(v.get("ferme") is False for v in BTM.values()):
        fautes.append("aucun actif intermittent déclaré : la distinction "
                      "entre ce qui tient un effacement et ce qui ne le tient "
                      "pas disparaîtrait de la table")
    vus = set()
    for x in FACTEURS_DIMENSIONNANTS:
        if x["cle"] in vus:
            fautes.append("facteur en double : %s" % x["cle"])
        vus.add(x["cle"])
        for champ in ("nom", "quoi", "qui_le_detient"):
            if not (x.get(champ) or "").strip():
                fautes.append("facteur %s : champ « %s » vide"
                              % (x["cle"], champ))
    for k, v in IMPLANTATIONS.items():
        for champ in ("nom", "quoi", "ce_qui_le_rend_possible", "risque"):
            if not (v.get(champ) or "").strip():
                fautes.append("implantation %s : champ « %s » vide" % (k, champ))
    ids = [c["id"] for c in CHAMPS]
    if len(set(ids)) != len(ids):
        fautes.append("identifiant de champ dupliqué")
    for c in CHAMPS:
        if "defaut" in c:
            fautes.append("champ %s : une valeur par défaut masquerait une "
                          "donnée manquante" % c["id"])

    # ── Les renvois ────────────────────────────────────────────────────────
    try:
        import icpe_dc
        for k, v in BTM.items():
            r = v.get("icpe")
            if r and r not in icpe_dc.RUBRIQUES:
                fautes.append("actif %s : rubrique inconnue %s" % (k, r))
    except ImportError:                                  # pragma: no cover
        pass
    try:
        import etat_art
        cles = {f["cle"] for f in etat_art.FAITS}
        for k, v in MODES_RACCORDEMENT.items():
            r = v.get("repere_delai")
            if r and r not in cles:
                fautes.append("mode %s : repère de marché inconnu %s" % (k, r))
    except ImportError:                                  # pragma: no cover
        pass
    return fautes


_FAUTES = _verifier()
if _FAUTES:                                              # pragma: no cover
    raise RuntimeError("reseau_dc : table incohérente — " + " ; ".join(_FAUTES))
