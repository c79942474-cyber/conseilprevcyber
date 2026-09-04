# -*- coding: utf-8 -*-
"""Qui finance une enveloppe de centre de données, et ce que chacun exige.

CE QUE CE MODULE AJOUTE À L'ENVELOPPE. `econome_dc` chiffre ce que l'opération
COÛTE. Il ne dit rien de ce qu'elle coûte À PORTER, ni de ce que le porteur
devra produire pour qu'on la lui finance. Or les deux décident autant l'un que
l'autre : une enveloppe tenable devient intenable si le seul financement
disponible exige un rendement que le contrat d'hébergement ne servira pas, et
un dossier techniquement irréprochable se fait refuser pour des pièces qu'on
n'a pas su qu'il fallait produire.

POURQUOI MAINTENANT. Les centres de données ont changé de classe d'actif. Ils
n'étaient financés que par leurs exploitants sur bilan ; ils le sont désormais
par des fonds d'infrastructure, de la dette privée, des fonds de pension, des
fonds souverains et jusqu'à des fonds immobiliers — et, en France, par des
institutions publiques d'investissement. Chacune de ces familles ne cherche pas
la même chose, ne tient pas le même horizon et n'exige pas le même dossier.
Traiter « le financement » comme une seule chose fait préparer un dossier pour
un interlocuteur qu'on n'aura pas.

CE QUE CE MODULE NE FAIT PAS, ET C'EST L'ESSENTIEL.

  · IL N'EMBARQUE AUCUN TAUX. Ni coût de la dette, ni rendement attendu des
    fonds propres, ni marge. Ces valeurs se négocient, elles se relèvent sur un
    term sheet, et elles changent tous les trimestres. Un taux écrit ici serait
    faux six mois plus tard et servirait quand même de base à une décision.
    Sans taux déclaré, le calcul rend « indéterminé » en NOMMANT ce qui manque.

  · IL NE RECOMMANDE AUCUN FINANCEUR. Il décrit des FAMILLES par ce qu'elles
    cherchent et ce qu'elles imposent. Le choix se fait sur un projet, un
    porteur et un marché, pas sur une table.

  · IL NE CITE AUCUN PROGRAMME NI AUCUN DISPOSITIF NOMMÉ. Les guichets, leurs
    critères et leurs enveloppes changent plus vite qu'un référentiel ne se met
    à jour ; ce qui est décrit ici est la NATURE des institutions, qui, elle,
    est stable. Ce qui relève du dispositif se vérifie auprès de l'institution,
    et le module le dit à chaque fois.

  · IL N'EST PAS UN CONSEIL FINANCIER. Il prépare une conversation d'ingénieur
    avec un financier : de quoi savoir ce qu'on va vous demander et pourquoi.
"""

VERSION = "2026-09-a"


# ═══════════════════════════════════════════════════════════════════════════
#  1. LES FAMILLES DE FINANCEMENT
# ═══════════════════════════════════════════════════════════════════════════
# SIX CHAMPS PAR FAMILLE, ET CHACUN RÉPOND À UNE QUESTION QU'ON POSE TROP TARD :
#
#   · cherche       — ce que l'argent vient chercher. C'est ce qui explique
#                     tout le reste, et c'est ce qu'on oublie de demander.
#   · apporte       — la nature de l'apport : dette, fonds propres, quasi.
#   · horizon       — la durée qu'elle tient. Un horizon plus court que la vie
#                     de l'actif n'est pas un défaut : c'est une SORTIE à
#                     préparer dès le montage, et ne pas la préparer est la
#                     faute la plus fréquente.
#   · exige         — ce qu'il faut produire. C'est la partie utile à un
#                     ingénieur : la moitié de ces pièces sont des livrables
#                     techniques, et elles se commandent en phase d'étude ou
#                     pas du tout.
#   · change        — ce que sa présence change au projet lui-même.
#   · ne_fera_pas   — la limite. Une famille présentée sans limite laisse
#                     croire qu'on peut tout lui demander.

SOURCES = {
    "fonds_infrastructure": {
        "nom": "Fonds d'infrastructure",
        "cherche": "Un actif qui produit un revenu contractuel, long et peu "
                   "corrélé au cycle économique. Pour un centre de données, "
                   "ce revenu est le bail ou le contrat d'hébergement : c'est "
                   "LUI qui est financé, pas le bâtiment.",
        "apporte": "Fonds propres et quasi-fonds propres, souvent en position "
                   "majoritaire, avec une gouvernance qui vient avec.",
        "horizon_ans": (7, 15),
        # Les exigences sont DÉSIGNÉES au catalogue, jamais
        # rédigées ici : c'est ce qui permet de les rapprocher
        # d'un financeur à l'autre.
        "exige": [
            "revenus_contractes",
            "modele_financier",
            "diligence_technique",
            "regime_administratif",
            "raccordement",
        ],
        "change": "La gouvernance change de main. Les arbitrages techniques "
                  "qui touchent au revenu — densité admise, engagements de "
                  "disponibilité, pénalités — cessent d'être des décisions "
                  "d'ingénieur et deviennent des décisions d'actionnaire.",
        "ne_fera_pas": "Financer un actif sans visibilité sur son remplissage. "
                       "Le risque commercial n'est pas celui qu'il achète.",
    },
    "dette_privee": {
        "nom": "Dette privée (non bancaire)",
        "cherche": "Un service de la dette couvert par des flux prévisibles, "
                   "avec des sûretés. Elle accepte des structures qu'une "
                   "banque refuse, et le paie en taux.",
        "apporte": "De la dette senior ou junior, souvent plus rapide à "
                   "mettre en place qu'un financement bancaire syndiqué et "
                   "plus souple sur les covenants.",
        "horizon_ans": (5, 12),
        # Les exigences sont DÉSIGNÉES au catalogue, jamais
        # rédigées ici : c'est ce qui permet de les rapprocher
        # d'un financeur à l'autre.
        "exige": [
            "couverture_service_dette",
            "suretes",
            "budget_fige",
            "modele_financier",
        ],
        "change": "Les covenants deviennent des contraintes d'exploitation : "
                  "un ratio à tenir chaque trimestre limite ce qu'on peut "
                  "décider en cours de vie — y compris des investissements "
                  "techniques qu'on croyait libres.",
        "ne_fera_pas": "Prendre du risque de construction nu. Le risque de "
                       "réalisation se transfère à l'entreprise par un marché "
                       "à prix et délai fermes, ou il ne se finance pas.",
    },
    "fonds_pension": {
        "nom": "Fonds de pension",
        "cherche": "Un rendement régulier et prévisible sur très longue "
                   "durée, adossé à des engagements de retraite. La "
                   "RÉGULARITÉ prime sur le niveau.",
        "apporte": "Des fonds propres patients, en position minoritaire le "
                   "plus souvent, ou de la dette longue.",
        "horizon_ans": (15, 30),
        # Les exigences sont DÉSIGNÉES au catalogue, jamais
        # rédigées ici : c'est ce qui permet de les rapprocher
        # d'un financeur à l'autre.
        "exige": [
            "trajectoire_revenus",
            "plan_renouvellement",
            "empreinte_mesuree",
            "diligence_technique",
        ],
        "change": "L'horizon long rend le COÛT COMPLET décisif, pas "
                  "l'investissement initial. Un choix technique moins cher à "
                  "construire et plus cher à exploiter devient un mauvais "
                  "choix — ce qui inverse plusieurs arbitrages d'avant-projet.",
        "ne_fera_pas": "Accepter une sortie contrainte à court terme, ni un "
                       "actif dont la valeur résiduelle dépend d'une "
                       "technologie dont la durée de vie est incertaine.",
    },
    "fonds_souverain": {
        "nom": "Fonds souverain",
        "cherche": "Une exposition à une infrastructure stratégique, avec un "
                   "horizon très long et parfois un objectif qui n'est pas "
                   "seulement financier.",
        "apporte": "Des fonds propres de grande taille, capables de porter "
                   "seuls un projet que d'autres devraient syndiquer.",
        "horizon_ans": (10, 30),
        # Les exigences sont DÉSIGNÉES au catalogue, jamais
        # rédigées ici : c'est ce qui permet de les rapprocher
        # d'un financeur à l'autre.
        "exige": [
            "taille_operation",
            "localisation_donnees",
            "diligence_technique",
            "modele_financier",
        ],
        "change": "L'entrée d'un investisseur étranger dans une "
                  "infrastructure peut relever d'un contrôle des "
                  "investissements étrangers. Ce n'est pas un obstacle, c'est "
                  "un JALON de calendrier — et il se découvre trop souvent "
                  "après la signature.",
        "ne_fera_pas": "Une opération de petite taille, ni une opération dont "
                       "le régime de contrôle n'a pas été instruit en amont.",
    },
    "fonds_immobilier": {
        "nom": "Fonds immobilier",
        "cherche": "Un actif locatif : des mètres carrés loués, une "
                   "localisation, une valeur de revente. Il analyse d'abord "
                   "le bâtiment et le bail, ensuite l'exploitation.",
        "apporte": "Des fonds propres immobiliers, éventuellement en montage "
                   "de type propriétaire / exploitant séparés.",
        "horizon_ans": (7, 15),
        # Les exigences sont DÉSIGNÉES au catalogue, jamais
        # rédigées ici : c'est ce qui permet de les rapprocher
        # d'un financeur à l'autre.
        "exige": [
            "bail_et_signature",
            "expertise_valeur",
            "capacite_evolution_bati",
            "diligence_technique",
        ],
        "change": "La séparation du mur et de l'exploitation crée une "
                  "frontière contractuelle nouvelle : qui porte le "
                  "renouvellement des installations techniques, qui porte la "
                  "mise en conformité, qui porte l'adaptation à une densité "
                  "supérieure. Cette frontière se dessine au bail, et mal "
                  "dessinée elle se paie vingt ans.",
        "ne_fera_pas": "Porter le risque d'exploitation informatique. Il "
                       "achète un immeuble et un locataire, pas un service.",
    },
    "investisseur_public_national": {
        "nom": "Investisseur public national (Bpifrance, Caisse des Dépôts)",
        "cherche": "Un effet sur l'économie et le territoire autant qu'un "
                   "rendement : souveraineté numérique, capacité de calcul "
                   "nationale, emploi et aménagement local. C'est ce qui "
                   "explique ses exigences propres.",
        "apporte": "Fonds propres, quasi-fonds propres, dette longue ou "
                   "garantie, le plus souvent AUX CÔTÉS d'investisseurs "
                   "privés dont il ne se substitue pas au rôle.",
        "horizon_ans": (10, 25),
        # Les exigences sont DÉSIGNÉES au catalogue, jamais
        # rédigées ici : c'est ce qui permet de les rapprocher
        # d'un financeur à l'autre.
        "exige": [
            "effet_recherche",
            "tour_de_table_prive",
            "empreinte_mesuree",
            "raccordement",
            "urbanisme_collectivites",
        ],
        "change": "Le projet acquiert une dimension publique : ce qui était "
                  "un arbitrage privé — implantation, consommation d'eau, "
                  "réemploi de chaleur — devient un engagement opposable, et "
                  "il faudra en rendre compte.",
        "ne_fera_pas": "Se substituer au financement privé, ni financer une "
                       "opération sans effet démontré au-delà de sa propre "
                       "rentabilité.",
        "reserve": "LES DISPOSITIFS NE SONT PAS DÉCRITS ICI, et c'est "
                   "délibéré : guichets, critères d'éligibilité et enveloppes "
                   "changent plus vite qu'un référentiel. Ce qui est décrit "
                   "est la NATURE de ces investisseurs, qui est stable. "
                   "L'éligibilité se vérifie auprès de l'institution, et elle "
                   "seule engage.",
    },
}

# L'ORDRE VA DE LA DETTE AUX FONDS PROPRES LES PLUS PATIENTS. Il porte la
# gradation de ce que chacun demande en contrepartie, et sert à composer un
# tour de table lisible plutôt qu'une liste alphabétique.
ORDRE_SOURCES = ["dette_privee", "fonds_infrastructure", "fonds_immobilier",
                 "fonds_pension", "fonds_souverain",
                 "investisseur_public_national"]

SOURCES_SOURCE = (
    "CADRAGE DE PLACE, PAS UN CONSEIL FINANCIER. Ces familles sont décrites "
    "par ce qu'elles cherchent et ce qu'elles imposent, telles qu'un maître "
    "d'ouvrage les rencontre. Aucun taux, aucun rendement et aucun dispositif "
    "nommé ne figure ici : ces valeurs se négocient, se relèvent sur un "
    "document d'offre, et changent plus vite qu'un référentiel. Ce module "
    "prépare une conversation ; il ne la remplace pas et n'engage personne.")


# ═══════════════════════════════════════════════════════════════════════════
#  2. CE QU'IL FAUT PRODUIRE — un catalogue, pas des phrases par financeur
# ═══════════════════════════════════════════════════════════════════════════
# POURQUOI UN CATALOGUE, ET PAS UNE LISTE DE PHRASES DANS CHAQUE FAMILLE. La
# première version écrivait les exigences en toutes lettres, famille par
# famille. Elles étaient justes et le résultat annonçait pourtant « exigences
# communes : 0 » — parce que le rapprochement se faisait sur le TEXTE, et
# qu'aucune formulation n'était identique à une autre. La fonction la plus
# utile du module ne se déclenchait jamais, sans rien signaler.
#
# Les exigences portent donc un NOM, les familles désignent ce nom, et le
# rapprochement se fait dessus. C'est ce qui permet de dire « la diligence
# technique est demandée par trois de vos quatre interlocuteurs » — la seule
# phrase qui décide de l'ordre dans lequel on produit les pièces.
#
# `nature` sépare ce qui relève de l'INGÉNIERIE du reste. C'est la partie utile
# ici : ces pièces-là se commandent en phase d'étude ou ne se produisent pas.
EXIGENCES = {
    "revenus_contractes": {
        "intitule": "Contrats de revenus signés ou fermement engagés, avec "
                    "durée, indexation et qualité de signature",
        "nature": "financiere",
        "pourquoi": "C'est le revenu qui est financé, pas le bâtiment. Un "
                    "actif sans preneur n'est pas une infrastructure : c'est "
                    "une opération de promotion, qui ne se finance pas de la "
                    "même façon ni au même prix.",
    },
    "modele_financier": {
        "intitule": "Modèle financier complet, avec ses sensibilités",
        "nature": "financiere",
        "pourquoi": "Sans sensibilités, un modèle ne dit pas ce qui le casse. "
                    "C'est la première chose qu'un analyste refait, et mieux "
                    "vaut avoir trouvé la variable critique avant lui.",
    },
    "diligence_technique": {
        "intitule": "Diligence technique par un tiers : capacité réelle, état "
                    "des installations, conformité, plan de renouvellement",
        "nature": "technique",
        "pourquoi": "L'investisseur n'achète pas la capacité annoncée mais la "
                    "capacité constatée. Une diligence se PRÉPARE : elle "
                    "suppose un dossier d'ouvrages exécutés à jour, des "
                    "essais tracés et des relevés d'exploitation.",
    },
    "regime_administratif": {
        "intitule": "Régime administratif purgé, ou son calendrier "
                    "d'obtention avec les délais d'instruction",
        "nature": "administrative",
        "pourquoi": "Un délai d'instruction est un jalon de calendrier, donc "
                    "un coût de portage. Il ne se découvre pas en fin de "
                    "montage.",
    },
    "raccordement": {
        "intitule": "Convention de raccordement, sa puissance et sa fermeté",
        "nature": "technique",
        "pourquoi": "La puissance raccordable borne le revenu. Une convention "
                    "assortie d'un effacement ne vaut pas une convention "
                    "ferme, et l'écart se chiffre.",
    },
    "couverture_service_dette": {
        "intitule": "Ratio de couverture du service de la dette démontré, et "
                    "les hypothèses qui le produisent",
        "nature": "financiere",
        "pourquoi": "C'est le ratio qui déclenche les covenants. Le démontrer "
                    "sur des hypothèses qu'on n'assume pas revient à signer "
                    "une contrainte qu'on ne tiendra pas.",
    },
    "suretes": {
        "intitule": "Sûretés : nantissement de titres, hypothèque, cession "
                    "des créances d'hébergement",
        "nature": "juridique",
        "pourquoi": "Elles décident du taux autant que le risque lui-même, et "
                    "certaines se heurtent aux clauses des contrats "
                    "d'hébergement déjà signés.",
    },
    "budget_fige": {
        "intitule": "Budget d'investissement figé, provision pour aléas "
                    "DÉCLARÉE et calendrier de tirage aligné sur l'avancement",
        "nature": "financiere",
        "pourquoi": "Un budget sans provision se lit comme un budget faux. La "
                    "déclarer n'affaiblit pas le dossier — c'est la cacher qui "
                    "l'affaiblit, parce qu'elle sera trouvée.",
    },
    "trajectoire_revenus": {
        "intitule": "Trajectoire de revenus sur toute la durée de détention, "
                    "au-delà du premier contrat",
        "nature": "financiere",
        "pourquoi": "Le premier contrat couvre rarement l'horizon d'un "
                    "investisseur long. Ce qui se passe après est précisément "
                    "ce qu'il achète.",
    },
    "plan_renouvellement": {
        "intitule": "Plan de renouvellement des installations techniques, "
                    "chiffré sur la durée de détention",
        "nature": "technique",
        "pourquoi": "Sur vingt ans, le froid et l'électricité se remplacent au "
                    "moins une fois : c'est un investissement, pas de "
                    "l'entretien, et il ne figure dans aucun budget "
                    "d'exploitation.",
    },
    "empreinte_mesuree": {
        "intitule": "Empreinte énergie, eau et carbone MESURÉE, et la "
                    "trajectoire documentée qui va avec",
        "nature": "technique",
        "pourquoi": "Elle alimente le reporting extra-financier de "
                    "l'investisseur, qui en répond lui-même. Une valeur "
                    "estimée n'y suffit pas : c'est une donnée d'instrument "
                    "qu'on demande, avec son périmètre.",
    },
    "taille_operation": {
        "intitule": "Une taille d'opération qui justifie l'instruction",
        "nature": "financiere",
        "pourquoi": "En deçà d'un certain montant, le coût d'analyse ne se "
                    "rentabilise pas — et le dossier n'est pas refusé, il "
                    "n'est pas instruit.",
    },
    "localisation_donnees": {
        "intitule": "Clarté sur la localisation des données et des "
                    "équipements, et sur les régimes juridiques applicables",
        "nature": "juridique",
        "pourquoi": "Elle décide de l'éligibilité de certains investisseurs et "
                    "du régime de contrôle applicable à leur entrée.",
    },
    "bail_et_signature": {
        "intitule": "Bail de longue durée et qualité de signature du preneur",
        "nature": "juridique",
        "pourquoi": "L'investisseur immobilier achète un immeuble ET un "
                    "locataire. La durée résiduelle du bail pèse autant que "
                    "la localisation.",
    },
    "expertise_valeur": {
        "intitule": "Valeur d'expertise du bien, avec ses hypothèses de "
                    "rendement et de valeur terminale",
        "nature": "financiere",
        "pourquoi": "La valeur terminale porte souvent la moitié du rendement. "
                    "Les hypothèses qui la produisent valent donc autant que "
                    "le chiffre.",
    },
    "capacite_evolution_bati": {
        "intitule": "État technique du bâti et sa CAPACITÉ D'ÉVOLUTION — "
                    "capacité portante des planchers et puissance disponible",
        "nature": "technique",
        "pourquoi": "C'est ce qui décide de ce qu'on pourra mettre dans le "
                    "bâtiment demain. À densité multipliée par vingt en une "
                    "génération de matériel, un bâtiment qui ne peut pas "
                    "évoluer perd sa valeur terminale — et c'est exactement "
                    "ce que le calcul de densité de ce site mesure.",
    },
    "effet_recherche": {
        "intitule": "Démonstration de l'effet recherché sur le territoire ou "
                    "la capacité nationale, et de ce qui ne se ferait pas sans",
        "nature": "administrative",
        "pourquoi": "C'est le critère propre de l'investisseur public : il "
                    "n'est pas un investisseur privé de plus, et un dossier "
                    "qui ne le traite pas ne se distingue en rien.",
    },
    "tour_de_table_prive": {
        "intitule": "Tour de table privé constitué ou en voie de l'être",
        "nature": "financiere",
        "pourquoi": "Ces institutions co-investissent ; elles ne remplacent "
                    "pas le marché, et un dossier qui n'a qu'elles est un "
                    "dossier que le marché a écarté.",
    },
    "urbanisme_collectivites": {
        "intitule": "Inscription dans les documents d'urbanisme et accord des "
                    "collectivités concernées",
        "nature": "administrative",
        "pourquoi": "L'implantation d'un centre de données est devenue un "
                    "sujet local. L'accord se construit, il ne se constate "
                    "pas au dépôt du permis.",
    },
}

NATURES_EXIGENCE = {
    "technique": "Livrable d'ingénierie — il se commande en phase d'étude, ou "
                 "il ne se produit pas à temps.",
    "financiere": "Pièce de modélisation ou de comptabilité.",
    "juridique": "Acte ou clause — il engage, et se négocie avec les contrats "
                 "déjà signés.",
    "administrative": "Autorisation ou accord d'un tiers public — il porte un "
                      "délai d'instruction, donc un jalon.",
}


# ═══════════════════════════════════════════════════════════════════════════
#  3. CE QUE L'ENVELOPPE COÛTE À PORTER — sur des taux DÉCLARÉS, jamais devinés
# ═══════════════════════════════════════════════════════════════════════════

def _annuite(capital, taux, annees):
    """L'annuité constante d'un emprunt. Un taux nul se rembourse en parts
    égales — la formule générale divise alors par zéro, et l'écrire ici évite
    qu'un projet financé à taux nul fasse tomber tout le calcul."""
    if annees <= 0:
        return None
    if taux == 0:
        return capital / float(annees)
    return capital * taux / (1.0 - (1.0 + taux) ** (-annees))


def portage(enveloppe_eur=None, part_dette=None, taux_dette=None,
            duree_dette_ans=None, rendement_fonds_propres=None,
            puissance_it_kw=None):
    """Ce que l'enveloppe coûte par an, sur les seules valeurs déclarées.

    AUCUN TAUX N'EST EMBARQUÉ, et c'est la règle qui tient tout le module. Un
    coût de la dette écrit ici serait faux au trimestre suivant et servirait
    quand même de base à une décision — parce qu'un formulaire déjà rempli ne
    se conteste pas. Ce qui manque est NOMMÉ.

    LES DEUX MONTANTS NE SONT PAS DE MÊME NATURE, et le résultat le dit plutôt
    que de les additionner en silence : l'annuité de la dette est un décaissement
    exigible, le rendement des fonds propres est une exigence de rémunération.
    Les sommer donne un ordre de grandeur utile — le coût annuel du capital —,
    à condition de savoir que la seconde moitié ne se paie pas à date fixe.
    """
    manques = []
    if not enveloppe_eur:
        manques.append("le montant de l'enveloppe")
    if part_dette is None:
        manques.append("la part financée par dette")
    if taux_dette is None:
        manques.append("le taux de la dette (relevé sur une offre, pas supposé)")
    if not duree_dette_ans:
        manques.append("la durée d'amortissement de la dette")
    if rendement_fonds_propres is None:
        manques.append("le rendement attendu des fonds propres")
    if manques:
        return {"ok": False, "verdict": "indetermine", "manques": manques,
                "message": "Le coût de portage ne peut pas être établi : il "
                           "manque " + ", ".join(manques) + ". Aucune de ces "
                           "valeurs n'est supposée ici — une valeur par défaut "
                           "deviendrait la réponse."}
    if not (0.0 <= part_dette <= 1.0):
        raise ValueError("La part de dette est une fraction entre 0 et 1.")

    dette = enveloppe_eur * part_dette
    fonds_propres = enveloppe_eur - dette
    annuite = _annuite(dette, taux_dette, duree_dette_ans)
    exigence_fp = fonds_propres * rendement_fonds_propres
    cout_annuel = annuite + exigence_fp
    cmpc = part_dette * taux_dette + (1.0 - part_dette) * rendement_fonds_propres

    return {
        "ok": True, "verdict": "etabli",
        "enveloppe_eur": round(enveloppe_eur, 2),
        "dette_eur": round(dette, 2),
        "fonds_propres_eur": round(fonds_propres, 2),
        "annuite_dette_eur": round(annuite, 2),
        "interets_premiere_annee_eur": round(dette * taux_dette, 2),
        "exigence_fonds_propres_eur": round(exigence_fp, 2),
        "cout_annuel_capital_eur": round(cout_annuel, 2),
        "cout_total_dette_eur": round(annuite * duree_dette_ans, 2),
        "surcout_dette_eur": round(annuite * duree_dette_ans - dette, 2),
        "cmpc": round(cmpc, 6),
        "cout_annuel_par_kw": (round(cout_annuel / puissance_it_kw, 2)
                               if puissance_it_kw else None),
        "hypotheses": {
            "part_dette": part_dette, "taux_dette": taux_dette,
            "duree_dette_ans": duree_dette_ans,
            "rendement_fonds_propres": rendement_fonds_propres,
            "puissance_it_kw": puissance_it_kw,
        },
        "reserves": [
            "LES DEUX MOITIÉS NE SE PAIENT PAS PAREIL. L'annuité de dette est "
            "exigible à date ; le rendement des fonds propres est une "
            "exigence de rémunération, servie par les résultats. Leur somme "
            "est un ordre de grandeur du coût du capital, pas un échéancier.",
            "LE COÛT MOYEN PONDÉRÉ EST AVANT IMPÔT. La déductibilité des "
            "intérêts abaisse le coût réel de la dette ; l'appliquer ici "
            "supposerait un taux d'imposition, un résultat imposable et un "
            "régime de déductibilité — trois hypothèses fiscales que ce "
            "module ne porte pas.",
            "L'ENVELOPPE N'EST PAS LE BESOIN DE FINANCEMENT. S'y ajoutent les "
            "intérêts pendant la construction, les frais de mise en place, "
            "les honoraires et le fonds de roulement de démarrage. Un plan "
            "de financement bâti sur la seule enveloppe de travaux est court "
            "de plusieurs pour cent.",
        ],
    }


def horizon_compatible(sources, duree_detention_ans=None):
    """L'horizon des financeurs retenus contre la durée du projet.

    CE QUE CETTE FONCTION ATTRAPE : un actif tenu vingt-cinq ans financé par
    des fonds propres dont l'horizon en fait sept. Ce n'est pas une faute — la
    sortie est le métier de ces fonds — mais elle DOIT être organisée au
    montage. Découverte en cours de vie, elle se règle par une vente forcée.
    """
    retenues = [s for s in (sources or []) if s in SOURCES]
    if not retenues:
        return {"ok": False, "message": "Aucune famille de financement "
                                        "retenue : rien à confronter."}
    lignes = []
    for cle in ORDRE_SOURCES:
        if cle not in retenues:
            continue
        bas, haut = SOURCES[cle]["horizon_ans"]
        ligne = {"cle": cle, "nom": SOURCES[cle]["nom"],
                 "horizon_ans": [bas, haut], "ecart": None, "dit": None}
        if duree_detention_ans:
            if haut < duree_detention_ans:
                ligne["ecart"] = "sortie_a_organiser"
                ligne["dit"] = (
                    "Horizon de %d à %d ans pour une détention de %d ans : une "
                    "sortie est à organiser AU MONTAGE — clause de liquidité, "
                    "droit de préemption, mécanisme de refinancement. Non "
                    "prévue, elle se règle par une vente forcée au moment le "
                    "moins choisi." % (bas, haut, duree_detention_ans))
            elif bas > duree_detention_ans:
                ligne["ecart"] = "horizon_plus_long_que_le_projet"
                ligne["dit"] = (
                    "Horizon de %d à %d ans pour une détention de %d ans : "
                    "cette famille cherche plus long que ce que le projet "
                    "offre, et l'instruction risque de ne pas aboutir."
                    % (bas, haut, duree_detention_ans))
            else:
                ligne["dit"] = ("Horizon compatible avec la durée de "
                                "détention annoncée.")
        lignes.append(ligne)
    return {"ok": True, "duree_detention_ans": duree_detention_ans,
            "lignes": lignes,
            "a_organiser": [l for l in lignes
                            if l["ecart"] == "sortie_a_organiser"],
            "note": ("Sans durée de détention déclarée, les horizons sont "
                     "affichés sans être confrontés : c'est la durée du "
                     "projet qui donne son sens à l'écart.")
            if not duree_detention_ans else None}


def exigences(sources):
    """Ce qu'il faudra produire, réuni et attribué à qui le demande.

    POURQUOI LA LISTE EST RÉUNIE PLUTÔT QUE RENDUE PAR FINANCEUR. Un tour de
    table se prépare une fois : produire trois dossiers parce qu'on a trois
    interlocuteurs est le meilleur moyen de les rendre incohérents. Ce qui
    compte est la LISTE UNIQUE, avec en face qui l'exige — parce qu'une pièce
    demandée par un seul se négocie, et qu'une pièce demandée par tous ne se
    négocie pas.

    LE RAPPROCHEMENT SE FAIT SUR DES CLÉS, ET C'EST UNE CORRECTION. Il se
    faisait sur le TEXTE des exigences, rédigé famille par famille : aucune
    formulation n'étant identique à une autre, le résultat annonçait
    « exigences communes : 0 » quel que soit le tour de table. La fonction la
    plus utile du module ne se déclenchait jamais, et rien ne le signalait.

    LES LIVRABLES TECHNIQUES SORTENT À PART. C'est la partie qui concerne un
    ingénieur : ces pièces-là se commandent en phase d'étude ou ne se
    produisent pas à temps.
    """
    retenues = [s for s in (sources or []) if s in SOURCES]
    par_cle = {}
    for cle in ORDRE_SOURCES:
        if cle not in retenues:
            continue
        for ex in SOURCES[cle]["exige"]:
            par_cle.setdefault(ex, []).append(SOURCES[cle]["nom"])
    liste = [{"cle": k, "intitule": EXIGENCES[k]["intitule"],
              "nature": EXIGENCES[k]["nature"],
              "nature_dit": NATURES_EXIGENCE[EXIGENCES[k]["nature"]],
              "pourquoi": EXIGENCES[k]["pourquoi"],
              "demandee_par": qui, "nombre": len(qui)}
             for k, qui in par_cle.items()]
    liste.sort(key=lambda x: (-x["nombre"], x["intitule"]))
    return {
        "ok": bool(retenues),
        "sources_retenues": [SOURCES[c]["nom"] for c in ORDRE_SOURCES
                             if c in retenues],
        "exigences": liste,
        "communes": [x for x in liste if x["nombre"] > 1],
        "livrables_techniques": [x for x in liste if x["nature"] == "technique"],
        "note": "Une pièce demandée par un seul financeur se négocie ; une "
                "pièce demandée par tous ne se négocie pas. C'est la raison "
                "pour laquelle la liste est triée par nombre de demandeurs et "
                "non par thème — et les livrables d'ingénierie sont ressortis "
                "à part, parce qu'ils se commandent en phase d'étude ou ne se "
                "produisent pas à temps.",
    }


def etude(enveloppe_eur=None, sources=None, duree_detention_ans=None,
          part_dette=None, taux_dette=None, duree_dette_ans=None,
          rendement_fonds_propres=None, puissance_it_kw=None):
    """Les trois résultats ensemble : ce que ça coûte à porter, avec qui, et
    ce qu'il faudra produire.

    ILS PARTENT ENSEMBLE parce que séparés ils se lisent chacun à l'avantage
    de la décision déjà prise. Un coût de portage sans les exigences fait
    croire qu'un financement se trouve sur un taux ; une liste d'exigences
    sans le coût fait préparer un dossier pour un montage qui ne se servira
    pas.
    """
    return {
        "version": VERSION,
        "portage": portage(enveloppe_eur, part_dette, taux_dette,
                           duree_dette_ans, rendement_fonds_propres,
                           puissance_it_kw),
        "horizons": horizon_compatible(sources, duree_detention_ans),
        "exigences": exigences(sources),
        "source": SOURCES_SOURCE,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  4. CE QUE LE MODULE SERT AUX PAGES
# ═══════════════════════════════════════════════════════════════════════════

def glossaire():
    return {
        "financement": {k: {
            "nom": v["nom"],
            "aide": ("Ce qu'il cherche — %s\n\nCe qu'il apporte — %s\n\n"
                     "Horizon : %d à %d ans.\n\nCe que sa présence change — "
                     "%s\n\nCe qu'il ne fera pas — %s%s"
                     % (v["cherche"], v["apporte"], v["horizon_ans"][0],
                        v["horizon_ans"][1], v["change"], v["ne_fera_pas"],
                        ("\n\nRéserve — " + v["reserve"]) if v.get("reserve")
                        else "")),
        } for k, v in SOURCES.items()},
    }


def referentiel():
    return {
        "version": VERSION,
        "sources": SOURCES,
        "exigences": EXIGENCES,
        "natures_exigence": NATURES_EXIGENCE,
        "ordre_sources": ORDRE_SOURCES,
        "sources_source": SOURCES_SOURCE,
        "glossaire": glossaire(),
    }
