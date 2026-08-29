"""L'organisation de la phase travaux d'un centre de données.

CE QUE CE MODULE ORGANISE. La période qui va du démarrage du chantier à la fin
de la garantie de parfait achèvement : le suivi, le contrôle, le
commissioning, la réception, et la coordination de tous ceux qui y
interviennent — maîtrise d'œuvre (architecte, bureaux d'études, consultants
externes, bureau d'études environnement), entreprises, et les trois tiers que
personne ne commande et que tout le monde subit : le commissioning agent, le
contrôleur technique et le coordonnateur SPS.

POURQUOI IL EXISTE SÉPARÉMENT DU CADRE DES PHASES. Le cadre des phases dit
QUELLES PIÈCES sont dues à chaque phase. Il ne dit pas qui fait quoi pendant le
chantier, dans quel ordre, ni ce qui bloque quoi. Or la phase travaux n'échoue
presque jamais sur une pièce manquante : elle échoue sur une opération faite
trop tard, un point d'arrêt franchi sans le contrôleur, un essai intégré
découvert la semaine de la réception. Ce sont des fautes d'ORDONNANCEMENT, pas
de contenu.

LA CONTRAINTE QUE CE MODULE SERT. Faire respecter les termes du dossier marché
et de l'appel d'offres client. Cela ne se fait pas par la fermeté en réunion :
cela se fait par un dispositif — des points d'arrêt écrits au marché, un
programme d'essais contractualisé, un circuit de visa daté, et un registre qui
rend l'écart visible avant qu'il ne coûte. Les solutions techniques et
managériales qui tiennent cette contrainte sont dans SOLUTIONS, plus bas, et
chacune dit CE QU'ELLE COÛTE — une solution dont le prix n'est pas dit ne se
décide pas.

CE QU'IL NE FAIT PAS. Il ne remplace ni le planning d'entreprise, ni le plan
de contrôle du contrôleur technique, ni le programme du commissioning agent.
Il donne la structure sur laquelle ces trois documents se raccordent, et
signale les endroits où ils se contredisent habituellement.
"""

VERSION = "2026-08-a"


# ═══════════════════════════════════════════════════════════════════════════
#  1. QUI INTERVIENT, ET À QUEL TITRE
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE LA TABLE SÉPARE. Trois natures de présence sur un chantier, qu'on
# confond en parlant d'« intervenants » :
#
#   · ceux que la maîtrise d'ouvrage COMMANDE et qui lui doivent un résultat
#     (maîtrise d'œuvre, entreprises) ;
#   · ceux qu'elle commande mais qui ne lui doivent pas d'obéissance
#     (contrôleur technique, coordonnateur SPS : leur avis est réglementé) ;
#   · ceux qui n'ont aucun lien contractuel avec elle et qui contraignent
#     quand même (concessionnaires, autorités, exploitant futur).
#
# LA CONSÉQUENCE PRATIQUE. On ne pilote pas les trois de la même façon. Donner
# une instruction à un contrôleur technique n'a pas d'effet ; l'informer trop
# tard en a un, et il est coûteux.

INTERVENANTS = {
    "moa": {
        "nom": "Maîtrise d'ouvrage",
        "lien": "commande",
        "role": "Décide, finance, signe les marchés et prononce la réception. "
                "C'est elle qui arbitre tout écart au programme.",
        "produit": "Les décisions, tracées. Un arbitrage non écrit n'existe "
                   "pas trois mois plus tard.",
        "quand": "Présente aux jalons de décision, aux constats et à la "
                 "réception.",
        "interface": "Le délai de décision de la maîtrise d'ouvrage est une "
                     "durée de planning au même titre qu'une tâche "
                     "d'entreprise. Ne pas l'y faire figurer est la cause la "
                     "plus banale d'un retard imputé au chantier.",
    },
    "amo": {
        "nom": "Assistance à maîtrise d'ouvrage",
        "lien": "commande",
        "role": "Prépare les décisions du maître d'ouvrage, contrôle la "
                "maîtrise d'œuvre et les entreprises pour son compte, et "
                "tient le dossier marché.",
        "produit": "Les analyses préalables aux arbitrages, les revues de "
                   "conformité au programme, le suivi des engagements du "
                   "marché.",
        "quand": "De la programmation à la fin de la garantie de parfait "
                 "achèvement.",
        "interface": "L'AMO et la MOE ne se recouvrent que si la répartition "
                     "des tâches n'a pas été écrite. Le tableau de "
                     "répartition MOE/AMO est une pièce du marché, pas un "
                     "document interne — et il se relit à chaque phase.",
    },
    # POURQUOI LA MAÎTRISE D'ŒUVRE FIGURE EN TANT QUE TELLE, à côté de
    # l'architecte et des bureaux d'études qui la composent. Parce que c'est
    # ELLE, et non l'un de ses membres, qui dirige l'exécution, vise, constate
    # et propose la réception : ces actes sont contractuellement portés par le
    # groupement, sous la signature de son mandataire. Citer « le BET fluides »
    # là où le marché dit « le maître d'œuvre » désignerait un responsable qui
    # n'en est pas un.
    "moe": {
        "nom": "Maîtrise d'œuvre (le groupement, sous son mandataire)",
        "lien": "commande",
        "role": "Dirige l'exécution des travaux, vise les études "
                "d'exécution, constate, propose la réception et suit la "
                "levée des réserves. Elle engage le groupement entier, quel "
                "que soit celui de ses membres qui a instruit le point.",
        "produit": "Comptes rendus, visas, constats, ordres de service "
                   "préparés pour la maîtrise d'ouvrage, propositions de "
                   "réception.",
        "quand": "De la conception à la fin de la garantie de parfait "
                 "achèvement.",
        "interface": "Le mandataire est l'interlocuteur unique du maître "
                     "d'ouvrage. Quand chaque cotraitant répond directement, "
                     "les réponses se contredisent et la maîtrise d'ouvrage "
                     "arbitre à la place du groupement — c'est le premier "
                     "symptôme d'un groupement mal constitué.",
    },
    "architecte": {
        "nom": "Architecte",
        "lien": "commande",
        "role": "Conception architecturale, insertion, permis, et suivi de la "
                "conformité de l'ouvrage à son projet.",
        "produit": "Plans, prescriptions architecturales, avis sur les "
                   "propositions d'entreprise touchant à l'aspect et aux "
                   "volumes.",
        "quand": "De l'esquisse à la réception.",
        "interface": "Sur un centre de données, l'architecture SUIT la "
                     "technique plus qu'elle ne la précède : les locaux "
                     "techniques, les gaines et les accès de maintenance "
                     "commandent le plan. Un projet dessiné avant que les "
                     "puissances soient arrêtées se redessine.",
    },
    "bet": {
        "nom": "Bureaux d'études techniques",
        "lien": "commande",
        "role": "Conception des lots techniques — électricité, CVC, fluides, "
                "courants faibles, structure — et suivi de leur exécution.",
        "produit": "Notes de calcul, spécifications, plans, visas des "
                   "documents d'exécution des entreprises.",
        "quand": "De l'avant-projet à la réception, avec un pic au visa.",
        "interface": "Le visa des études d'exécution est une opération à "
                     "DURÉE : dix jours ouvrés par document est un ordre de "
                     "grandeur courant. Un planning qui ne les compte pas "
                     "fabrique un retard structurel dès la première semaine.",
    },
    "be_environnement": {
        "nom": "Bureau d'études environnement",
        "lien": "commande",
        "role": "Dossier d'installations classées, bilan énergie-eau-carbone, "
                "suivi des engagements environnementaux du marché.",
        "produit": "Le dossier ICPE, les pièces de conformité "
                   "environnementale, et les éléments de rapportage.",
        "quand": "Très en amont pour le dossier, puis ponctuellement au "
                 "chantier pour les constats et les mesures.",
        "interface": "Ses données d'entrée viennent des lots techniques — "
                     "puissances, volumes, fluides. Un équipement changé en "
                     "exécution sans l'en informer peut invalider une pièce "
                     "déjà déposée.",
    },
    "consultants": {
        "nom": "Consultants externes",
        "lien": "commande",
        "role": "Expertises ponctuelles — acoustique, sûreté, incendie, "
                "essais spécifiques — commandées pour un point précis.",
        "produit": "Un avis daté, sur un périmètre défini.",
        "quand": "À la demande, souvent aux jalons de conception et aux "
                 "essais.",
        "interface": "Un avis d'expert non intégré au dossier d'exécution "
                     "reste une note dans un dossier. Chaque avis doit se "
                     "traduire en prescription au CCTP ou en point d'arrêt, "
                     "sinon il n'a pas d'effet.",
    },
    "entreprises": {
        "nom": "Entreprises et sous-traitants",
        "lien": "commande",
        "role": "Exécutent les travaux, établissent les études d'exécution, "
                "réalisent les essais qui leur incombent.",
        "produit": "Études d'exécution, plans de fabrication, procès-verbaux "
                   "d'essais, dossiers des ouvrages exécutés.",
        "quand": "Du démarrage à la levée des réserves.",
        "interface": "La sous-traitance est le point aveugle du suivi : les "
                     "essais d'un sous-traitant de rang deux n'arrivent au "
                     "dossier que si le marché l'exige nommément.",
    },
    "commissioning": {
        "nom": "Commissioning agent",
        "lien": "tiers_commande",
        "role": "Établit et conduit le programme d'essais — des essais en "
                "usine jusqu'aux essais intégrés en charge — et prouve que "
                "l'installation fait ce qu'elle promet.",
        "produit": "Plan de commissioning, listes de vérification "
                   "pré-fonctionnelles, procès-verbaux d'essais fonctionnels "
                   "et intégrés, rapport final.",
        "quand": "Dès l'avant-projet pour la revue de conception ; le gros de "
                 "sa charge est en fin de chantier.",
        "interface": "C'est la mission qui distingue un centre de données "
                     "d'un entrepôt : sans elle, la disponibilité annoncée "
                     "n'est jamais démontrée. Son programme doit être "
                     "CONTRACTUALISÉ dans les marchés de travaux — un "
                     "commissioning agent sans point d'arrêt opposable ne "
                     "peut qu'observer.",
    },
    "controle_technique": {
        "nom": "Contrôleur technique",
        "lien": "tiers_reglemente",
        "role": "Donne un avis sur la solidité des ouvrages et la sécurité "
                "des personnes. Son avis n'est pas une instruction : c'est "
                "une position qui engage sa responsabilité.",
        "produit": "Rapport initial, avis sur les documents de conception et "
                   "d'exécution, rapport final avant réception.",
        "quand": "De la conception à la réception.",
        "interface": "Ses avis défavorables non levés bloquent la réception "
                     "et l'assurance. Les traiter au fil de l'eau coûte "
                     "beaucoup moins que de les découvrir groupés au rapport "
                     "final.",
    },
    "csps": {
        "nom": "Coordonnateur SPS",
        "lien": "tiers_reglemente",
        "role": "Coordonne la sécurité et la protection de la santé des "
                "travailleurs dès lors que plusieurs entreprises "
                "interviennent — ce qui est le cas de tout centre de données.",
        "produit": "Plan général de coordination, journal de coordination, "
                   "dossier d'intervention ultérieure sur l'ouvrage.",
        "quand": "De la conception à la réception, et sa mission de "
                 "conception commence AVANT le chantier.",
        "interface": "Le dossier d'intervention ultérieure sur l'ouvrage se "
                     "construit pendant le chantier. Reconstitué après coup, "
                     "il est faux — et c'est l'exploitant qui le découvrira, "
                     "en intervenant.",
    },
    "concessionnaires": {
        "nom": "Concessionnaires et autorités",
        "lien": "hors_contrat",
        "role": "Gestionnaire du réseau électrique, service de l'eau, "
                "services d'incendie et de secours, inspection des "
                "installations classées, autorité d'urbanisme.",
        "produit": "Autorisations, mises en service, avis, visites de "
                   "conformité.",
        "quand": "Aux jalons administratifs et à la mise en service.",
        "interface": "Aucun de ces délais ne se négocie et aucun ne dépend du "
                     "chantier. Ils se demandent tôt et se suivent comme des "
                     "tâches — la mise en service du raccordement électrique "
                     "est le premier délai du projet et le dernier qu'on "
                     "regarde.",
    },
    "exploitant": {
        "nom": "Exploitant et équipes de conduite",
        "lien": "hors_contrat",
        "role": "Reprend l'ouvrage et le conduit. Il n'est pas partie au "
                "marché de travaux, et hérite pourtant de tout ce qu'il "
                "contient.",
        "produit": "Les réserves d'exploitabilité, si on les lui demande "
                   "assez tôt pour qu'elles servent.",
        "quand": "À associer dès les essais fonctionnels, pas à la remise des "
                 "clés.",
        "interface": "Conditionner la réception à la remise des données "
                     "d'exploitation — DOE, paramétrages, comptes, plans de "
                     "comptage — est le seul moment où on a un moyen de "
                     "pression. Après, il n'y en a plus.",
    },
}

LIENS = {
    "commande": {
        "nom": "Sous contrat de la maîtrise d'ouvrage",
        "aide": "Doit un résultat et reçoit des instructions. Le pilotage "
                "passe par le marché.",
    },
    "tiers_commande": {
        "nom": "Commandé, mais tiers au marché de travaux",
        "aide": "Payé par la maîtrise d'ouvrage, sans pouvoir sur les "
                "entreprises. Son efficacité vient de ce que le marché de "
                "travaux lui donne — points d'arrêt, essais opposables — et "
                "de rien d'autre.",
    },
    "tiers_reglemente": {
        "nom": "Tiers dont l'avis est réglementé",
        "aide": "Ne reçoit pas d'instruction : son avis engage sa propre "
                "responsabilité. On l'informe tôt, on ne le dirige pas.",
    },
    "hors_contrat": {
        "nom": "Sans lien contractuel",
        "aide": "Contraint le projet sans lui devoir quoi que ce soit. Ses "
                "délais se subissent et se planifient donc en premier.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  2. LES OPÉRATIONS DE LA PHASE TRAVAUX
# ═══════════════════════════════════════════════════════════════════════════
# L'ORDRE EST CELUI DU CHANTIER, et il n'est pas négociable : chaque opération
# a un PRÉALABLE, et le franchir sans lui produit un travail à refaire, pas un
# gain de temps. C'est ce que la colonne `prealable` dit.
#
# CHAQUE OPÉRATION PORTE SON POINT D'ARRÊT, quand il y en a un. Un point
# d'arrêt est une étape que l'entreprise ne peut pas franchir sans un accord
# écrit — c'est le seul outil qui donne prise sur un chantier, et il n'existe
# que s'il est écrit AU MARCHÉ. Ajouté en cours de chantier, il se négocie.

OPERATIONS = [
    {
        "cle": "prep",
        "nom": "Période de préparation",
        "famille": "suivi",
        "phase": "EXE-VISA",
        "objet": "Installer le dispositif : plannings détaillés, plans "
                 "d'installation de chantier, procédures, circuits de visa, "
                 "liste des points d'arrêt, plan de commissioning et plan de "
                 "contrôle. Rien ne se construit pendant cette période, et "
                 "c'est elle qui décide du reste.",
        "prealable": "Marchés notifiés et ordre de service.",
        "produit": ["Planning détaillé d'exécution", "Plan d'installation de "
                    "chantier", "Liste des points d'arrêt validée",
                    "Circuit et délais de visa", "Plan de commissioning",
                    "Plan général de coordination SPS"],
        "acteurs": ["moe", "entreprises", "csps", "commissioning",
                    "controle_technique"],
        "point_arret": "Aucun démarrage de travaux avant validation du "
                       "planning détaillé et de la liste des points d'arrêt.",
        "faute": "La raccourcir pour « gagner du temps ». Le temps gagné "
                 "revient multiplié au moment du visa, quand personne ne sait "
                 "qui approuve quoi ni en combien de jours.",
    },
    {
        "cle": "visa",
        "nom": "Visa des études d'exécution",
        "famille": "suivi",
        "phase": "EXE-VISA",
        "objet": "Examiner les documents d'exécution des entreprises et les "
                 "viser, refuser ou viser avec observations. Le visa porte "
                 "sur la conformité au marché, pas sur la reprise de la "
                 "conception.",
        "prealable": "Circuit de visa et délais arrêtés en période de "
                     "préparation.",
        "produit": ["Registre des documents visés, par indice et par date",
                    "Observations tracées et leur reprise vérifiée"],
        "acteurs": ["bet", "architecte", "entreprises", "controle_technique"],
        "point_arret": "Aucune fabrication ni commande d'équipement avant "
                       "visa du document correspondant.",
        "faute": "Viser sans registre. Trois mois plus tard, personne ne sait "
                 "quel indice a été visé, et l'entreprise a construit sur le "
                 "sien.",
    },
    {
        "cle": "fat",
        "nom": "Essais en usine (FAT)",
        "famille": "controle",
        "phase": "EXE-VISA",
        "objet": "Éprouver les équipements majeurs — groupes électrogènes, "
                 "onduleurs, groupes froid, tableaux — chez le constructeur, "
                 "avant livraison. C'est le dernier moment où un défaut se "
                 "corrige sans toucher au chantier.",
        "prealable": "Documents d'exécution visés et programme d'essais "
                     "approuvé.",
        "produit": ["Procès-verbaux d'essais en usine", "Réserves et leur "
                    "traitement avant expédition"],
        "acteurs": ["bet", "commissioning", "entreprises", "moa"],
        "point_arret": "Pas d'expédition avant procès-verbal d'essai accepté.",
        "faute": "Y envoyer quelqu'un sans le programme d'essais. Une visite "
                 "d'usine sans protocole écrit constate ce qu'on veut bien "
                 "lui montrer.",
    },
    {
        "cle": "suivi_chantier",
        "nom": "Direction de l'exécution et réunions de chantier",
        "famille": "suivi",
        "phase": "DET",
        "objet": "Diriger l'exécution : réunions périodiques, comptes rendus "
                 "opposables, constats, ordres de service, gestion des "
                 "modifications et de leur incidence sur le prix et le délai.",
        "prealable": "Période de préparation close.",
        "produit": ["Comptes rendus de chantier numérotés",
                    "Registre des modifications avec incidence chiffrée",
                    "Constats contradictoires"],
        "acteurs": ["moe", "entreprises", "moa", "amo"],
        "point_arret": None,
        "faute": "Traiter une modification en réunion sans l'inscrire au "
                 "registre avec son incidence. C'est le mécanisme par lequel "
                 "un marché dérive sans qu'aucune décision n'ait été prise.",
    },
    {
        "cle": "controle_travaux",
        "nom": "Contrôle des travaux et points d'arrêt",
        "famille": "controle",
        "phase": "DET",
        "objet": "Vérifier ce qui va être caché : fourreaux avant "
                 "remblaiement, calfeutrements avant doublage, chemins de "
                 "câbles avant plafonds, mises à la terre avant coulage. Un "
                 "ouvrage fermé ne se contrôle plus, il se rouvre.",
        "prealable": "Liste des points d'arrêt écrite au marché.",
        "produit": ["Procès-verbaux de levée de point d'arrêt",
                    "Photographies datées des ouvrages avant fermeture"],
        "acteurs": ["moe", "controle_technique", "entreprises",
                    "be_environnement"],
        "point_arret": "Aucun ouvrage caché sans levée écrite du point "
                       "d'arrêt correspondant.",
        "faute": "Accepter une levée a posteriori sur photographie fournie "
                 "par l'entreprise. Elle prouve qu'un ouvrage a existé, pas "
                 "qu'il est conforme.",
    },
    {
        "cle": "prefonctionnel",
        "nom": "Vérifications pré-fonctionnelles",
        "famille": "commissioning",
        "phase": "DET",
        "objet": "Vérifier équipement par équipement, avant toute mise en "
                 "route : installation conforme, raccordements faits, "
                 "réglages posés, sécurités présentes. C'est du contrôle "
                 "statique, et il conditionne tout le reste.",
        "prealable": "Équipements posés et raccordés, documents visés.",
        "produit": ["Listes de vérification pré-fonctionnelles signées, par "
                    "équipement"],
        "acteurs": ["commissioning", "entreprises", "bet"],
        "point_arret": "Pas de mise sous tension ni de mise en eau avant "
                       "liste pré-fonctionnelle close.",
        "faute": "Les faire signer en série la veille des essais "
                 "fonctionnels. Une liste signée sans avoir été faite est "
                 "pire qu'une liste absente : elle éteint l'alerte.",
    },
    {
        "cle": "sat",
        "nom": "Essais fonctionnels par système (SAT)",
        "famille": "commissioning",
        "phase": "DET",
        "objet": "Éprouver chaque système seul, dans ses modes normaux et "
                 "dégradés : démarrage, arrêt, bascule, défaut simulé, "
                 "retour. Un système à la fois, pour que la cause d'un écart "
                 "soit identifiable.",
        "prealable": "Vérifications pré-fonctionnelles closes.",
        "produit": ["Procès-verbaux d'essais fonctionnels par système",
                    "Relevés de réglages retenus"],
        "acteurs": ["commissioning", "entreprises", "bet", "exploitant"],
        "point_arret": "Pas d'essai intégré avant clôture des essais par "
                       "système.",
        "faute": "Passer aux essais intégrés avec des systèmes non clos. Un "
                 "écart en essai intégré devient alors inattribuable, et "
                 "chaque entreprise désigne l'autre.",
    },
    {
        "cle": "ist",
        "nom": "Essais intégrés en charge (IST)",
        "famille": "commissioning",
        "phase": "DET",
        "objet": "Éprouver l'installation ENTIÈRE sous charge réelle ou "
                 "simulée : coupure réseau, démarrage et reprise par les "
                 "groupes, tenue des onduleurs, bascule des chaînes, montée "
                 "en température, retour au réseau. C'est le seul essai qui "
                 "démontre la disponibilité annoncée.",
        "prealable": "Essais par système clos ; bancs de charge et "
                     "combustible approvisionnés ; scénarios approuvés par la "
                     "maîtrise d'ouvrage.",
        "produit": ["Scénarios d'essais intégrés et leurs procès-verbaux",
                    "Relevés de performance — PUE partiel, temps de reprise, "
                    "températures"],
        "acteurs": ["commissioning", "entreprises", "bet", "moa",
                    "exploitant"],
        "point_arret": "Pas d'opérations préalables à la réception avant "
                       "essais intégrés concluants.",
        "faute": "Les programmer sans réserver les bancs de charge ni le "
                 "combustible. C'est une logistique lourde, et elle décale "
                 "tout le calendrier de réception quand elle est oubliée.",
    },
    {
        "cle": "opr",
        "nom": "Opérations préalables à la réception",
        "famille": "reception",
        "phase": "AOR",
        "objet": "Parcourir l'ouvrage contradictoirement, constater ce qui "
                 "est achevé et ce qui ne l'est pas, dresser la liste des "
                 "réserves. C'est un constat, pas une négociation.",
        "prealable": "Essais intégrés concluants et dossier des ouvrages "
                     "exécutés remis.",
        "produit": ["Procès-verbal des opérations préalables à la réception",
                    "Liste des réserves, par lot et par local"],
        "acteurs": ["moe", "entreprises", "moa", "amo", "exploitant"],
        "point_arret": None,
        "faute": "Les tenir sans le dossier des ouvrages exécutés. La "
                 "réception se prononce alors sur un ouvrage dont on n'a pas "
                 "la description — et l'exploitant en héritera.",
    },
    {
        "cle": "reception",
        "nom": "Réception des travaux",
        "famille": "reception",
        "phase": "AOR",
        "objet": "Acte par lequel le maître d'ouvrage accepte l'ouvrage, avec "
                 "ou sans réserves. Elle déclenche les garanties, le "
                 "transfert de garde et le point de départ de la garantie de "
                 "parfait achèvement.",
        "prealable": "Opérations préalables tenues et rapport final du "
                     "contrôleur technique sans avis défavorable non levé.",
        "produit": ["Procès-verbal de réception", "Décompte des réserves et "
                    "délai de levée"],
        "acteurs": ["moa", "moe", "entreprises", "controle_technique"],
        "point_arret": None,
        "faute": "Prononcer la réception pour tenir une date, en reportant "
                 "sur les réserves ce qui relève de l'inachèvement. Après la "
                 "réception, le rapport de force est inversé.",
    },
    {
        "cle": "levee",
        "nom": "Levée des réserves et garantie de parfait achèvement",
        "famille": "reception",
        "phase": "AOR",
        "objet": "Suivre la reprise des réserves dans le délai fixé, puis "
                 "traiter les désordres signalés pendant l'année de garantie "
                 "de parfait achèvement.",
        "prealable": "Réception prononcée.",
        "produit": ["Procès-verbaux de levée", "Registre des désordres de la "
                    "garantie de parfait achèvement"],
        "acteurs": ["moe", "entreprises", "moa", "exploitant"],
        "point_arret": None,
        "faute": "Ne pas fixer de délai de levée au procès-verbal. Une "
                 "réserve sans délai ne se lève pas, elle se discute.",
    },
    {
        "cle": "exploitation",
        "nom": "Transfert à l'exploitation",
        "famille": "reception",
        "phase": "AOR",
        "objet": "Remettre à l'exploitant ce dont il a besoin pour conduire : "
                 "dossier des ouvrages exécutés, dossier d'intervention "
                 "ultérieure, paramétrages, comptes et droits, plan de "
                 "comptage, formation des équipes, contrats de maintenance.",
        "prealable": "Réception prononcée ; formation planifiée avant, pas "
                     "après.",
        "produit": ["Dossier des ouvrages exécutés complet et indexé",
                    "Dossier d'intervention ultérieure sur l'ouvrage",
                    "Plan de comptage et accès aux mesures",
                    "Attestations de formation des équipes"],
        "acteurs": ["moe", "entreprises", "exploitant", "csps", "moa"],
        "point_arret": None,
        "faute": "Le traiter comme une remise de documents. Un exploitant "
                 "qui découvre la GTB le jour de la remise des clés "
                 "conduira l'installation en manuel pendant six mois — et "
                 "les performances contractuelles ne seront pas tenues.",
    },
]

FAMILLES_OPERATION = {
    "suivi": {"nom": "Suivi et direction",
              "aide": "Ce qui fait avancer le chantier conformément au "
                      "marché : préparation, visa, réunions, modifications."},
    "controle": {"nom": "Contrôle",
                 "aide": "Ce qui vérifie avant qu'il soit trop tard : essais "
                         "en usine, points d'arrêt sur ouvrages cachés."},
    "commissioning": {"nom": "Commissioning",
                      "aide": "Ce qui démontre que l'installation fait ce "
                              "qu'elle promet : vérifications "
                              "pré-fonctionnelles, essais par système, essais "
                              "intégrés en charge."},
    "reception": {"nom": "Réception et transfert",
                  "aide": "Ce qui clôt : opérations préalables, réception, "
                          "levée des réserves, transfert à l'exploitation."},
}


# ═══════════════════════════════════════════════════════════════════════════
#  3. LES SOLUTIONS QUI TIENNENT LA CONTRAINTE DU MARCHÉ
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE CETTE TABLE RÉPOND. « Faire respecter les termes et contraintes du
# dossier marché » n'est pas une intention : c'est un dispositif, et un
# dispositif se choisit. Chaque solution dit ce qu'elle OBTIENT, ce qu'elle
# COÛTE, et OÙ elle doit être posée pour avoir un effet — presque toutes
# doivent l'être dans les pièces du marché, avant la consultation. Posée
# après, elle se négocie ; posée avant, elle s'applique.
#
# LA COLONNE `quand_poser` EST LA PLUS UTILE. Elle explique pourquoi un
# dispositif évident ne marche pas : parce qu'on l'a mis en place au mauvais
# moment.

SOLUTIONS = [
    {
        "cle": "points_arret",
        "nature": "technique",
        "nom": "Points d'arrêt contractuels",
        "obtient": "Un pouvoir de blocage réel : l'entreprise ne peut pas "
                   "poursuivre sans accord écrit. C'est le seul outil qui "
                   "donne prise sur un ouvrage qui va être caché.",
        "coute": "Du temps de présence sur site, et un risque de retard si "
                 "le délai de levée n'est pas encadré. Fixez-le : « levée "
                 "sous 48 heures ouvrées, faute de quoi réputé levé » "
                 "protège les deux parties.",
        "quand_poser": "Au CCAP et au CCTP, avant la consultation. La liste "
                       "se finalise en période de préparation.",
    },
    {
        "cle": "essais_contractualises",
        "nature": "technique",
        "nom": "Programme d'essais annexé au marché",
        "obtient": "Des essais opposables : scénarios, critères de réussite, "
                   "moyens à fournir par l'entreprise, et conséquence d'un "
                   "échec. Sans cela, le commissioning agent observe sans "
                   "pouvoir exiger.",
        "coute": "Un travail de rédaction en phase projet, et la fourniture "
                 "des bancs de charge et du combustible — postes à chiffrer "
                 "explicitement, faute de quoi ils manqueront.",
        "quand_poser": "Au DCE, en annexe technique. Le plan détaillé se "
                       "construit ensuite avec l'entreprise retenue.",
    },
    {
        "cle": "circuit_visa",
        "nature": "manageriale",
        "nom": "Circuit de visa daté et opposable",
        "obtient": "Un délai de visa connu de tous, donc planifiable, et une "
                   "traçabilité par indice. Il fait disparaître le débat sur "
                   "« qui attend qui ».",
        "coute": "Une discipline de la maîtrise d'œuvre : le délai qu'elle "
                 "impose aux entreprises, elle se l'impose aussi.",
        "quand_poser": "En période de préparation, sur la base de délais "
                       "déjà écrits au CCAP.",
    },
    {
        "cle": "registre_modifications",
        "nature": "manageriale",
        "nom": "Registre unique des modifications, avec incidence chiffrée",
        "obtient": "La visibilité de la dérive AVANT qu'elle soit acquise. "
                   "Une modification sans incidence chiffrée est une "
                   "modification acceptée.",
        "coute": "Un poste de travail réel — quelqu'un tient le registre — "
                 "et l'obligation de chiffrer vite, donc parfois "
                 "provisoirement. Un chiffrage provisoire annoncé comme tel "
                 "vaut mieux qu'une case vide.",
        "quand_poser": "Au CCAP, avec l'obligation pour l'entreprise de "
                       "notifier toute demande de modification par écrit "
                       "avant exécution.",
    },
    {
        "cle": "planning_jalons_tiers",
        "nature": "manageriale",
        "nom": "Planning intégrant les tiers et les délais administratifs",
        "obtient": "Le raccordement électrique, l'instruction ICPE, les "
                   "visites de conformité et les délais de décision de la "
                   "maîtrise d'ouvrage deviennent des tâches, avec des "
                   "responsables et des dates.",
        "coute": "Un planning plus long à afficher — et c'est précisément "
                 "l'information utile. Un planning qui masque ces délais ne "
                 "les supprime pas.",
        "quand_poser": "Dès le planning directeur, au programme. Les "
                       "réinsérer en phase travaux ne fait que constater le "
                       "retard.",
    },
    {
        "cle": "revue_conception_cx",
        "nature": "technique",
        "nom": "Revue de conception par le commissioning agent",
        "obtient": "Les écarts d'exploitabilité et d'essayabilité relevés "
                   "quand ils coûtent encore un trait de crayon : vannes "
                   "d'isolement manquantes, points de mesure absents, "
                   "scénarios de bascule impossibles à éprouver.",
        "coute": "Une mission de commissioning qui commence à l'avant-projet "
                 "et non au chantier — plus chère en apparence, moins chère "
                 "en réalité.",
        "quand_poser": "Au contrat de commissioning, avec une intervention "
                       "dès l'APD.",
    },
    {
        "cle": "cellule_synthese",
        "nature": "manageriale",
        "nom": "Cellule de synthèse technique",
        "obtient": "Les conflits entre lots — réservations, cheminements, "
                   "accès de maintenance — résolus sur plan avant de l'être "
                   "sur site. Sur un centre de données, où le lot technique "
                   "occupe l'essentiel du volume, c'est le poste qui évite le "
                   "plus de reprises.",
        "coute": "Une mission identifiée et rémunérée, et une maquette "
                 "tenue à jour. Confiée « à tout le monde », elle n'est "
                 "faite par personne.",
        "quand_poser": "Au marché de maîtrise d'œuvre, en désignant "
                       "nommément qui l'assure.",
    },
    {
        "cle": "reception_conditionnee",
        "nature": "manageriale",
        "nom": "Réception conditionnée à la remise du dossier d'exploitation",
        "obtient": "Le dossier des ouvrages exécutés, les paramétrages, les "
                   "comptes et la formation, remis à temps. C'est le seul "
                   "moment où il existe un moyen de pression.",
        "coute": "Une fermeté qui se prépare : la condition doit être écrite "
                 "au CCAP, sinon elle se plaide.",
        "quand_poser": "Au CCAP, en liant le paiement du solde à la remise "
                       "complète.",
    },
    {
        "cle": "phasage_exploitation",
        "nature": "technique",
        "nom": "Étude de phasage d'exploitation (rétrofit)",
        "obtient": "Sur une installation en service, la démonstration que "
                   "chaque intervention est réalisable sans indisponibilité "
                   "— ce qui se coupe, quand, avec quel repli et quel retour "
                   "arrière.",
        "coute": "Une étude à part entière, et des travaux plus lents parce "
                 "que séquencés. C'est le prix de la continuité de service, "
                 "et il se chiffre au marché.",
        "quand_poser": "En phase projet, comme pièce du DCE : elle décide de "
                       "la faisabilité et donc du prix.",
    },
    {
        "cle": "relevé_existant",
        "nature": "technique",
        "nom": "Relevé de l'existant et provision pour découvertes (fit-out "
               "et rétrofit)",
        "obtient": "Des données d'entrée fiables là où les plans d'origine "
                   "ne le sont plus : charges admissibles, réservations, "
                   "puissances disponibles, cheminements réels.",
        "coute": "Un relevé, et une provision affichée. La provision n'est "
                 "pas de la prudence : c'est du chiffrage, et la masquer "
                 "revient à la reporter sur les avenants.",
        "quand_poser": "Avant le chiffrage, au plus tard en phase projet.",
    },
]

NATURES_SOLUTION = {
    "technique": "Se pose dans les pièces techniques et se démontre par un "
                 "document ou un essai.",
    "manageriale": "Se pose dans l'organisation et les pièces "
                   "administratives, et tient par la discipline de ceux qui "
                   "l'appliquent.",
}


# ═══════════════════════════════════════════════════════════════════════════
#  LE PLAN DE LA PHASE TRAVAUX
# ═══════════════════════════════════════════════════════════════════════════

def _acteurs(cles):
    return [{"cle": c, "nom": INTERVENANTS[c]["nom"],
             "lien": INTERVENANTS[c]["lien"],
             "lien_nom": LIENS[INTERVENANTS[c]["lien"]]["nom"]}
            for c in cles if c in INTERVENANTS]


def plan(nature_travaux=None, avec_commissioning=True):
    """La séquence des opérations de la phase travaux, adaptée au projet.

    DEUX RÉGLAGES, ET ILS CHANGENT LE PLAN POUR DE BON :

      · `nature_travaux` — un rétrofit ajoute l'étude de phasage
        d'exploitation en tête de séquence et la rend bloquante ; un fit-out
        ajoute le relevé de l'existant. Les ajouter en solution facultative
        reviendrait à dire qu'on peut s'en passer, ce qui est faux ;

      · `avec_commissioning` — quand la mission n'est pas commandée, les
        opérations correspondantes ne DISPARAISSENT PAS : elles restent, avec
        la mention de qui devra les assumer. Retirer une opération parce que
        personne n'est payé pour la faire est exactement ce qui produit une
        réception sans essais intégrés.
    """
    ops = []
    for o in OPERATIONS:
        e = dict(o)
        e["acteurs"] = _acteurs(o["acteurs"])
        e["famille_nom"] = FAMILLES_OPERATION[o["famille"]]["nom"]
        if o["famille"] == "commissioning" and not avec_commissioning:
            e["sans_titulaire"] = (
                "Aucune mission de commissioning n'est commandée. Cette "
                "opération reste due : à défaut de commissioning agent, elle "
                "retombe sur la maîtrise d'œuvre et les entreprises, qui ne "
                "sont ni missionnées ni rémunérées pour la conduire. C'est un "
                "risque à porter au registre, pas une économie.")
        ops.append(e)

    prealables = []
    if nature_travaux == "retrofit":
        prealables.append({
            "cle": "phasage",
            "nom": "Étude de phasage d'exploitation",
            "famille": "suivi",
            "pourquoi": "Le site fonctionne et doit continuer à fonctionner. "
                        "C'est cette étude — ce qui se coupe, quand, avec "
                        "quel repli — et non les plans, qui décide de la "
                        "faisabilité et du délai.",
            "bloquant": True,
        })
    if nature_travaux in ("fit_out", "retrofit"):
        prealables.append({
            "cle": "releve",
            "nom": "Relevé de l'existant",
            "famille": "controle",
            "pourquoi": "Les plans d'origine ne correspondent plus et les "
                        "modifications successives ne sont pas tracées. Le "
                        "relevé sur site est la seule donnée fiable, et la "
                        "provision pour découvertes qui l'accompagne est du "
                        "chiffrage, pas de la prudence.",
            "bloquant": True,
        })

    return {
        "version": VERSION,
        "nature_travaux": nature_travaux,
        "prealables": prealables,
        "operations": ops,
        "familles": FAMILLES_OPERATION,
        "intervenants": {k: dict(v, lien_nom=LIENS[v["lien"]]["nom"])
                         for k, v in INTERVENANTS.items()},
        "liens": LIENS,
        "solutions": solutions_pour(nature_travaux, avec_commissioning),
        "points_arret": [{"operation": o["nom"], "exigence": o["point_arret"]}
                         for o in OPERATIONS if o.get("point_arret")],
        "note": NOTE_PLAN,
    }


NOTE_PLAN = (
    "CE PLAN EST UNE STRUCTURE, PAS UN PLANNING. Il donne l'ordre des "
    "opérations et ce que chacune exige avant de commencer ; il ne porte "
    "aucune durée, parce qu'une durée dépend de la taille du site, du nombre "
    "de lots et du nombre de salles à mettre en service. Il se raccorde au "
    "planning d'entreprise, au plan de contrôle du contrôleur technique et au "
    "programme du commissioning agent — trois documents qui se contredisent "
    "habituellement sur les mêmes points : la date des essais intégrés, la "
    "disponibilité des bancs de charge, et le moment où l'exploitant est "
    "associé.")


def solutions_pour(nature_travaux=None, avec_commissioning=True):
    """Les solutions à mettre en place, avec celles que le projet impose.

    UNE SOLUTION RENDUE OBLIGATOIRE PAR LA NATURE DES TRAVAUX le dit : le
    phasage d'exploitation sur un rétrofit et le relevé de l'existant sur un
    fit-out ne sont pas des bonnes pratiques, ce sont des conditions de
    faisabilité. Les afficher au même rang que les autres laisserait croire
    qu'on peut les arbitrer.
    """
    out = []
    for s in SOLUTIONS:
        e = dict(s)
        e["nature_nom"] = NATURES_SOLUTION[s["nature"]]
        if s["cle"] == "phasage_exploitation":
            e["impose"] = nature_travaux == "retrofit"
        elif s["cle"] == "relevé_existant":
            e["impose"] = nature_travaux in ("fit_out", "retrofit")
        elif s["cle"] in ("essais_contractualises", "revue_conception_cx"):
            e["impose"] = bool(avec_commissioning)
        else:
            e["impose"] = False
        out.append(e)
    out.sort(key=lambda s: (not s["impose"], s["nom"]))
    return out


def referentiel():
    """Les tables, sans calcul — pour la page et la documentation."""
    return {
        "version": VERSION,
        "intervenants": INTERVENANTS,
        "liens": LIENS,
        "operations": OPERATIONS,
        "familles": FAMILLES_OPERATION,
        "solutions": SOLUTIONS,
        "natures_solution": NATURES_SOLUTION,
        "note": NOTE_PLAN,
        "glossaire": glossaire(),
    }


def glossaire():
    """Les familles d'infobulles servies par ce module."""
    return {
        "intervenant": {k: {
            "nom": v["nom"],
            "aide": ("%s\n\nLien avec la maîtrise d'ouvrage — %s\n\nCe qu'il "
                     "produit — %s\n\nQuand — %s\n\nL'interface qui coince — %s"
                     % (v["role"], LIENS[v["lien"]]["aide"], v["produit"],
                        v["quand"], v["interface"])),
        } for k, v in INTERVENANTS.items()},
        "operation": {o["cle"]: {
            "nom": o["nom"],
            "aide": ("%s\n\nCe qu'il faut avant — %s%s\n\nLa faute classique "
                     "— %s"
                     % (o["objet"], o["prealable"],
                        ("\n\nPoint d'arrêt — " + o["point_arret"])
                        if o.get("point_arret") else "",
                        o["faute"])),
        } for o in OPERATIONS},
        "solution": {s["cle"]: {
            "nom": s["nom"],
            "aide": ("Ce que ça obtient — %s\n\nCe que ça coûte — %s\n\nOù et "
                     "quand la poser — %s"
                     % (s["obtient"], s["coute"], s["quand_poser"])),
        } for s in SOLUTIONS},
    }


# ═══════════════════════════════════════════════════════════════════════════
#  LES CONTRÔLES DE COHÉRENCE
# ═══════════════════════════════════════════════════════════════════════════

def _verifier():
    """Les fautes de structure, ou une liste vide.

    LA VÉRIFICATION QUI COMPTE porte sur les acteurs : une opération qui cite
    un intervenant absent de la table produirait une ligne sans nom dans le
    plan, et une ligne sans nom se lit comme une ligne sans responsable.
    """
    fautes = []
    vus = set()
    for o in OPERATIONS:
        if o["cle"] in vus:
            fautes.append("opération en double : %s" % o["cle"])
        vus.add(o["cle"])
        if o["famille"] not in FAMILLES_OPERATION:
            fautes.append("opération %s : famille inconnue (%s)"
                          % (o["cle"], o["famille"]))
        if not o["acteurs"]:
            fautes.append("opération %s : aucun acteur" % o["cle"])
        for a in o["acteurs"]:
            if a not in INTERVENANTS:
                fautes.append("opération %s : intervenant inconnu (%s)"
                              % (o["cle"], a))
        for champ in ("nom", "objet", "prealable", "faute"):
            if not (o.get(champ) or "").strip():
                fautes.append("opération %s : champ « %s » vide"
                              % (o["cle"], champ))
    for k, v in INTERVENANTS.items():
        if v["lien"] not in LIENS:
            fautes.append("intervenant %s : lien inconnu (%s)" % (k, v["lien"]))
        for champ in ("nom", "role", "produit", "quand", "interface"):
            if not (v.get(champ) or "").strip():
                fautes.append("intervenant %s : champ « %s » vide" % (k, champ))
    for f in FAMILLES_OPERATION:
        if not any(o["famille"] == f for o in OPERATIONS):
            fautes.append("famille sans opération : %s" % f)
    vues = set()
    for s in SOLUTIONS:
        if s["cle"] in vues:
            fautes.append("solution en double : %s" % s["cle"])
        vues.add(s["cle"])
        if s["nature"] not in NATURES_SOLUTION:
            fautes.append("solution %s : nature inconnue (%s)"
                          % (s["cle"], s["nature"]))
        for champ in ("nom", "obtient", "coute", "quand_poser"):
            if not (s.get(champ) or "").strip():
                fautes.append("solution %s : champ « %s » vide"
                              % (s["cle"], champ))
    # Les phases citées doivent exister au cadre : une opération rattachée à
    # une phase inconnue ne se retrouverait nulle part dans le dossier.
    try:
        import ingenierie_dc as _g
        connues = {p["code"] for p in _g.PHASES}
    except Exception:                                    # pragma: no cover
        connues = None
    if connues is not None:
        for o in OPERATIONS:
            if o.get("phase") and o["phase"] not in connues:
                fautes.append("opération %s : phase inconnue du cadre (%s)"
                              % (o["cle"], o["phase"]))
    return fautes


_FAUTES = _verifier()
if _FAUTES:
    raise RuntimeError("travaux_dc — table incohérente : " + " ; ".join(_FAUTES))
