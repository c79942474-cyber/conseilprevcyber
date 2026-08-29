"""Le pilotage d'un PROGRAMME multi-sites de centres de données.

CE QUE CE MODULE AJOUTE, et que rien ne portait. Tout le reste de la plateforme
raisonne PROJET : un site, un profil, une phase, un dossier. Or une direction de
programme ne dirige pas un projet — elle dirige un portefeuille de sites, chacun
à sa phase, dans plusieurs pays, avec une capacité à livrer, un budget à tenir
et un comité exécutif à qui rendre compte. Les questions qu'elle pose n'ont pas
de réponse au niveau d'un site :

  · quelle capacité informatique est engagée, et combien est déjà livrée ?
  · quel site tient le chemin critique du programme ?
  · combien coûte le kilowatt informatique, d'un site à l'autre ?
  · où en est la chaîne d'essais, et à quel prix la livraison « zéro défaut » ?
  · qui doit décider quoi, et quand cesse-t-il d'être temps de le décider ?

CE QU'IL REFUSE DE FAIRE, ET C'EST LE PLUS IMPORTANT. Consolider n'est pas
additionner. Certaines grandeurs s'additionnent — une puissance, un budget.
D'autres ne s'additionnent JAMAIS et se pondèrent — un PUE. D'autres encore ne
se consolident pas du tout, et le dire est la seule réponse honnête : un régime
ICPE ne se moyenne pas entre trois pays dont un seul connaît la nomenclature
française. Une console de programme qui affiche un nombre pour chacune de ces
trois familles ment sur deux tiers de son tableau de bord.

CE QU'IL FAIT DES DONNÉES ABSENTES. Il les compte et les nomme, il ne les
impute pas à zéro. Un CAPEX de programme calculé sur quatre sites renseignés
sur sept n'est pas le CAPEX du programme : c'est un sous-total, et le
présenter autrement est la façon la plus rapide de perdre la confiance d'un
comité exécutif — parce qu'il s'en apercevra.
"""

import math

VERSION = "2026-08-a"


# ═══════════════════════════════════════════════════════════════════════════
#  1. LA NATURE D'UN SITE — greenfield, brownfield
# ═══════════════════════════════════════════════════════════════════════════
# DEUX VOCABULAIRES POUR LA MÊME RÉALITÉ, ET ILS NE SE RECOUVRENT PAS TOUT À
# FAIT. La direction de programme dit « greenfield / brownfield » ; la maîtrise
# d'œuvre dit « neuf / fit-out / rétrofit ». Le second est plus fin, et c'est
# lui qui commande les études : un brownfield recouvre AUSSI BIEN l'aménagement
# d'une coquille reçue vide que la reprise d'une salle en exploitation, et ces
# deux-là n'ont ni le même risque, ni le même délai, ni le même prix.
#
# LA TABLE FAIT DONC LA CORRESPONDANCE au lieu de recopier des définitions. Un
# programme déclaré « brownfield » doit être redescendu en nature de travaux
# site par site — et le module le dit plutôt que de choisir à la place.

NATURES_SITE = {
    "greenfield": {
        "nom": "Greenfield — terrain nu",
        "travaux": ("neuf",),
        "ce_que_c_est": "Un site construit pour l'usage, du terrain au "
                        "bâtiment. La direction de programme y arbitre tout, "
                        "y compris l'implantation.",
        "delai_dominant": "Le raccordement au réseau électrique et "
                          "l'instruction administrative. Aucun des deux ne "
                          "dépend du chantier, et le premier est généralement "
                          "plus long que lui.",
        "risque_programme": "Le foncier et l'énergie se sécurisent AVANT le "
                            "reste. Un programme qui lance ses études sur un "
                            "terrain non maîtrisé ou une puissance non "
                            "réservée fabrique du travail à jeter.",
    },
    "brownfield": {
        "nom": "Brownfield — bâtiment ou site existant",
        "travaux": ("fit_out", "retrofit"),
        "ce_que_c_est": "Un site qui existe déjà : coquille reçue d'un "
                        "promoteur, bâtiment reconverti, ou salle en "
                        "exploitation à densifier ou remettre à niveau.",
        "delai_dominant": "Le relevé de l'existant, puis le phasage "
                          "d'exploitation quand le site tourne. C'est cette "
                          "étude, et non les plans, qui décide de la "
                          "faisabilité et donc du délai.",
        "risque_programme": "« Brownfield » recouvre deux métiers très "
                            "différents. Un programme qui ne descend pas au "
                            "niveau fit-out / rétrofit chiffre une extension "
                            "de salle en exploitation comme un aménagement de "
                            "coquille vide — et découvre l'écart en exécution.",
    },
}


def natures_travaux_de(nature_site):
    """Les natures de travaux que recouvre une nature de site, détaillées.

    Rend la table de `technique_dc` plutôt que des libellés recopiés : deux
    descriptions du même rétrofit finiraient par ne plus décrire le même.
    """
    n = NATURES_SITE.get(nature_site)
    if not n:
        return []
    try:
        import technique_dc as _t
        return [dict(_t.NATURES_TRAVAUX[c], cle=c) for c in n["travaux"]
                if c in _t.NATURES_TRAVAUX]
    except Exception:                                    # pragma: no cover
        return []


# ═══════════════════════════════════════════════════════════════════════════
#  2. LES INDICATEURS DE PROGRAMME
# ═══════════════════════════════════════════════════════════════════════════
# CE QUI DISTINGUE CES INDICATEURS DE CEUX D'UN PROJET. Ils répondent à un
# comité exécutif, pas à une réunion de chantier : ils portent sur le
# PORTEFEUILLE, ils se comparent d'un trimestre à l'autre, et chacun d'eux sera
# cité hors de son contexte dans une diapositive. C'est pourquoi chaque entrée
# porte `n_indique_pas` — la phrase qui empêche l'indicateur de dire plus qu'il
# ne sait.
#
# LA COLONNE `consolidation` EST LA PLUS UTILE, et c'est celle qu'on oublie.
# Elle dit COMMENT l'indicateur se fabrique à partir des sites :
#   · `somme`     — il s'additionne ;
#   · `pondere`   — il se pondère, et la table dit par quoi ;
#   · `extremum`  — il se prend au pire ou au meilleur, jamais au milieu ;
#   · `aucune`    — il ne se consolide pas, et l'afficher agrégé serait faux.

KPI = {
    "capacite_engagee": {
        "nom": "Capacité informatique engagée",
        "unite": "kW",
        "consolidation": "somme",
        "definition": "Somme des puissances informatiques installées ou "
                      "prévues de tous les sites du programme, quel que soit "
                      "leur avancement.",
        "n_indique_pas": "Ce qui est LIVRÉ. Un programme peut engager cent "
                         "mégawatts et n'en exploiter aucun ; c'est la "
                         "capacité livrée qui produit du revenu, et les deux "
                         "se présentent ensemble ou pas du tout.",
        "pourquoi": "C'est la grandeur de référence du programme : le budget, "
                    "le carbone et les effectifs s'y rapportent tous.",
    },
    "capacite_livree": {
        "nom": "Capacité informatique livrée",
        "unite": "kW",
        "consolidation": "somme",
        "definition": "Somme des puissances des sites dont la réception est "
                      "prononcée. Un site réceptionné avec réserves compte : "
                      "il est livré, et ses réserves se suivent à part.",
        "n_indique_pas": "La capacité VENDABLE. Une salle réceptionnée sans "
                         "raccordement définitif, sans exploitant formé ou "
                         "sans autorisation d'exploiter n'accueille aucun "
                         "client.",
        "pourquoi": "C'est le seul chiffre que le comité exécutif retient, et "
                    "celui sur lequel le programme est jugé.",
    },
    "capex_par_kw": {
        "nom": "CAPEX par kilowatt informatique",
        "unite": "€/kW",
        "consolidation": "pondere",
        "pondere_par": "puissance informatique",
        "definition": "Investissement total rapporté à la capacité "
                      "informatique. Sur un centre de données, c'est le ratio "
                      "de référence — le coût au mètre carré n'y veut rien "
                      "dire, parce que le lot technique pèse l'essentiel de "
                      "l'enveloppe.",
        "n_indique_pas": "La comparabilité entre sites. Un greenfield avec "
                         "terrain et raccordement, un fit-out en coquille "
                         "reçue et un rétrofit en exploitation ne portent pas "
                         "le même périmètre : les comparer sans le dire fait "
                         "conclure à une performance là où il n'y a qu'un "
                         "périmètre différent.",
        "pourquoi": "Il arbitre entre sites, entre niveaux de redondance et "
                    "entre modes de refroidissement mieux qu'aucun total.",
    },
    "opex_par_kw_an": {
        "nom": "OPEX annuel par kilowatt informatique",
        "unite": "€/kW/an",
        "consolidation": "pondere",
        "pondere_par": "puissance informatique",
        "definition": "Charges d'exploitation annuelles rapportées à la "
                      "capacité informatique — énergie, maintenance, "
                      "exploitation, redevances.",
        "n_indique_pas": "Le coût complet. L'amortissement de "
                         "l'investissement n'y est pas, et c'est lui qui "
                         "décide de l'arbitrage entre un PUE bas payé cher et "
                         "un PUE moyen payé peu.",
        "pourquoi": "C'est la moitié du coût total de possession, et celle "
                    "que les décisions de conception fixent pour vingt ans.",
    },
    "pue_programme": {
        "nom": "PUE moyen du programme",
        "unite": "—",
        "consolidation": "pondere",
        "pondere_par": "énergie informatique",
        "definition": "Rapport entre l'énergie totale et l'énergie "
                      "informatique de TOUS les sites cumulés. Il se pondère "
                      "par l'énergie informatique de chaque site.",
        "n_indique_pas": "La performance d'un site donné. Un programme à 1,25 "
                         "peut abriter un site à 1,6 rendu invisible par un "
                         "gros site efficace — et c'est le site à 1,6 qui "
                         "coûte.",
        "pourquoi": "C'est le chiffre déclaré à l'extérieur, et celui qu'un "
                    "évaluateur recalcule.",
        "piege": "La moyenne ARITHMÉTIQUE des PUE de site est fausse, et elle "
                 "est ce qu'on calcule spontanément. Un site de 10 MW à 1,5 et "
                 "un site de 100 kW à 1,1 ne pèsent pas pareil ; leur moyenne "
                 "arithmétique, 1,3, ne correspond à aucune réalité "
                 "physique.",
    },
    "derive_planning": {
        "nom": "Dérive de planning",
        "unite": "mois",
        "consolidation": "extremum",
        "extremum": "le plus tardif",
        "definition": "Écart entre la mise en service prévue au budget de "
                      "référence et la mise en service attendue aujourd'hui, "
                      "pris sur le site le PLUS EN RETARD.",
        "n_indique_pas": "La dérive moyenne, qui n'a pas de sens : un "
                         "programme livre quand son dernier site livre, et une "
                         "moyenne masque précisément celui qui commande la "
                         "date.",
        "pourquoi": "C'est la seule dérive qui compte pour un client qui "
                    "attend une capacité.",
    },
    "derive_capex": {
        "nom": "Dérive budgétaire",
        "unite": "%",
        "consolidation": "somme",
        "definition": "Écart entre l'investissement prévu au budget de "
                      "référence et l'investissement attendu aujourd'hui, sur "
                      "l'ensemble du programme.",
        "n_indique_pas": "D'où vient l'écart. Une dérive nette de zéro peut "
                         "recouvrir un site en dépassement de trente pour "
                         "cent et un autre en économie équivalente — deux "
                         "situations qui n'appellent pas la même décision.",
        "pourquoi": "C'est l'indicateur que le comité exécutif regarde en "
                    "premier, et il faut pouvoir le décomposer en séance.",
    },
    "reserves": {
        "nom": "Réserves ouvertes à la réception",
        "unite": "nombre",
        "consolidation": "somme",
        "definition": "Réserves constatées aux opérations préalables à la "
                      "réception et non encore levées, tous sites confondus.",
        "n_indique_pas": "La gravité. Dix réserves de finition et une réserve "
                         "sur une bascule de chaîne électrique donnent le même "
                         "nombre, et la seconde interdit l'exploitation.",
        "pourquoi": "C'est la mesure de la promesse « zéro défaut », et la "
                    "seule qui se vérifie contradictoirement.",
    },
    "commissioning": {
        "nom": "Avancement de la chaîne d'essais",
        "unite": "%",
        "consolidation": "pondere",
        "pondere_par": "puissance informatique",
        "definition": "Part des sites ayant franchi les essais intégrés en "
                      "charge, pondérée par leur capacité.",
        "n_indique_pas": "La qualité des essais. Un essai intégré conduit sans "
                         "banc de charge ni scénario approuvé se déclare fait "
                         "et ne démontre rien.",
        "pourquoi": "C'est l'essai intégré, et lui seul, qui démontre la "
                    "disponibilité annoncée au client.",
    },
    "tier_portefeuille": {
        "nom": "Niveau de disponibilité du portefeuille",
        "unite": "—",
        "consolidation": "extremum",
        "extremum": "le plus bas",
        "definition": "Le niveau le plus BAS atteint parmi les sites du "
                      "programme. La même règle que pour un site, appliquée "
                      "un cran plus haut : un site vaut son sous-système le "
                      "plus faible, un portefeuille vaut son site le plus "
                      "faible.",
        "n_indique_pas": "Ce que vaut chaque site. Un programme annoncé au "
                         "niveau III dont un site est au niveau I n'a pas "
                         "« presque » tenu son engagement : c'est ce site-là "
                         "que le client mettra en avant, et c'est lui qui "
                         "s'exploitera.",
        "pourquoi": "C'est l'engagement pris devant le client, et il ne se "
                    "tient pas en moyenne.",
        "piege": "La moyenne des niveaux n'existe pas. Il n'y a pas de niveau "
                 "fractionnaire, ni pour un site ni pour un portefeuille — "
                 "« nous sommes globalement en III » ne veut rien dire.",
    },
    "delai_energisation": {
        "nom": "Mise sous tension du portefeuille",
        "unite": "date",
        "consolidation": "extremum",
        "extremum": "la plus tardive",
        "definition": "La date à laquelle le DERNIER site du programme "
                      "dispose de sa puissance définitive. Elle précède la "
                      "mise en service et la commande : une salle achevée "
                      "sans puissance ne se met pas en service, et aucune "
                      "accélération de chantier ne rattrape un raccordement.",
        "n_indique_pas": "La date de LIVRAISON. Entre la mise sous tension et "
                         "la réception restent les essais, dont l'essai "
                         "intégré. Les deux dates se suivent ensemble ; "
                         "présenter la première pour la seconde est la façon "
                         "la plus courante d'annoncer un programme en avance "
                         "sur ce qu'il est.",
        "pourquoi": "C'est le poste le plus long du programme et celui sur "
                    "lequel le maître d'ouvrage a le moins de prise. Le "
                    "suivre à part du calendrier de travaux est la seule "
                    "façon de voir qu'il commande.",
        "piege": "Prendre la moyenne des dates, ou la date du site le plus "
                 "avancé. Un programme est sous tension quand son dernier "
                 "site l'est ; une moyenne masque précisément celui qui "
                 "commande la date.",
    },
    "regime_icpe": {
        "nom": "Régime administratif des sites",
        "unite": "—",
        "consolidation": "aucune",
        "definition": "Le régime applicable à chaque site, selon la "
                      "réglementation de SON pays.",
        "n_indique_pas": "Rien au niveau du programme, et c'est le point : la "
                         "nomenclature des installations classées est "
                         "française. Un programme à trois pays a trois cadres "
                         "administratifs, et un chiffre unique en tiendrait "
                         "lieu à tort.",
        "pourquoi": "Le régime décide du délai d'instruction, donc du chemin "
                    "critique — site par site.",
    },
}

CONSOLIDATIONS = {
    "somme": "S'additionne d'un site à l'autre.",
    "pondere": "Se pondère : la moyenne simple des sites serait fausse.",
    "extremum": "Se prend au pire, jamais au milieu — un programme livre "
                "quand son dernier site livre.",
    "aucune": "Ne se consolide pas. Un chiffre unique tiendrait lieu de "
              "plusieurs réalités qui ne se comparent pas.",
}


# ═══════════════════════════════════════════════════════════════════════════
#  3. LES PARTIES PRENANTES D'UN PROGRAMME
# ═══════════════════════════════════════════════════════════════════════════
# ELLES NE SONT PAS LES INTERVENANTS DU CHANTIER, et les confondre est la faute
# la plus coûteuse d'une direction de programme. Les intervenants exécutent
# sous contrat ; les parties prenantes DÉCIDENT ou BLOQUENT, et la plupart
# n'ont aucun lien contractuel avec le programme.
#
# CHAQUE ENTRÉE PORTE SA FENÊTRE : le moment après lequel sa décision coûte
# cher. C'est l'information qui manque le plus souvent, parce qu'elle ne figure
# dans aucun organigramme.

PARTIES_PRENANTES = {
    "it": {
        "nom": "Direction informatique / métier",
        "decide": "La densité par baie, la classe de température admise, le "
                  "calendrier de charge, la tolérance à l'indisponibilité.",
        "a_besoin_de": "Une date de disponibilité ferme et une capacité "
                       "chiffrée en kilowatts, pas en mètres carrés.",
        "fenetre": "La densité et la classe ASHRAE se décident à l'esquisse. "
                   "Après l'avant-projet définitif, les changer rouvre "
                   "l'aéraulique et la distribution électrique.",
        "quand_ca_coince": "Un besoin exprimé en surface plutôt qu'en "
                           "puissance. La surface ne dimensionne rien sur un "
                           "centre de données, et la conversion faite à la "
                           "place du demandeur se révèle fausse en exécution.",
    },
    "energie": {
        "nom": "Direction énergie / achats d'électricité",
        "decide": "La puissance souscrite, le contrat de fourniture, la part "
                  "d'énergie sans carbone contractualisée, l'éventuelle "
                  "production sur site.",
        "a_besoin_de": "Un profil de charge dans le temps, pas une puissance "
                       "de pointe seule.",
        "fenetre": "La demande de raccordement se dépose le plus tôt "
                   "possible : c'est le délai le plus long du programme, et "
                   "il ne se rattrape par aucun moyen technique.",
        "quand_ca_coince": "Deux arrivées négociées depuis le même poste "
                           "source. Elles se paient comme deux et tombent "
                           "comme une seule. Et, depuis que les files "
                           "d'attente s'allongent, l'acceptation d'un "
                           "raccordement EFFAÇABLE prise pour une simple "
                           "clause tarifaire : elle engage la capacité à "
                           "servir le client, donc le contrat commercial, et "
                           "elle se chiffre avant d'être signée.",
    },
    "immobilier": {
        "nom": "Direction immobilière / foncier",
        "decide": "Le site, le bail ou l'acquisition, les capacités du "
                  "bâtiment reçu en brownfield, les servitudes.",
        "a_besoin_de": "Les contraintes physiques du programme : charge au "
                       "plancher, hauteur libre, accès poids lourds, surfaces "
                       "techniques, distances d'éloignement.",
        "fenetre": "Avant toute étude. Un programme qui lance sa conception "
                   "sur un foncier non maîtrisé produit un dossier à jeter.",
        "quand_ca_coince": "Une annexe technique de bail qui plafonne la "
                           "charge au plancher ou interdit les groupes en "
                           "toiture. Elle se lit avant de signer, pas au "
                           "moment de l'implantation.",
    },
    "exploitation": {
        "nom": "Exploitation et conduite",
        "decide": "Les modes de conduite, le plan de maintenance, les "
                  "effectifs et les astreintes.",
        "a_besoin_de": "Le dossier des ouvrages exécutés, les paramétrages, "
                       "un plan de comptage et une formation avant la remise "
                       "des clés.",
        "fenetre": "À associer dès les essais fonctionnels. Après la "
                   "réception, il n'existe plus aucun moyen de pression pour "
                   "obtenir ce qui manque.",
        "quand_ca_coince": "Une exploitation découverte le jour de la remise "
                           "des clés conduit l'installation en manuel pendant "
                           "six mois — et les performances contractuelles ne "
                           "sont pas tenues.",
    },
    "finance": {
        "nom": "Direction financière et contrôle de gestion",
        "decide": "L'enveloppe, le découpage en tranches, les critères de "
                  "décision d'investissement, la devise de référence.",
        "a_besoin_de": "Un CAPEX et un OPEX séparés, une classe de précision "
                       "déclarée, et l'écart au budget de référence expliqué "
                       "site par site.",
        "fenetre": "La décision finale d'investissement se prend sur le "
                   "dossier de fin d'études amont. Ce qui n'y figure pas "
                   "devient un avenant.",
        "quand_ca_coince": "Une estimation présentée sans sa classe de "
                           "précision. Un ordre de grandeur pris pour un "
                           "engagement produit une dérive qui n'en est pas "
                           "une.",
    },
    "achats": {
        "nom": "Achats et juridique",
        "decide": "La stratégie contractuelle, l'allotissement, les pièces du "
                  "marché, les pénalités et les garanties.",
        "a_besoin_de": "Un besoin technique stabilisé et des exigences "
                       "MESURABLES : une performance sans méthode de preuve "
                       "n'est pas contractualisable.",
        "fenetre": "Avant la consultation. Un point d'arrêt, un programme "
                   "d'essais ou une condition de réception ajoutés après se "
                   "négocient ; posés avant, ils s'appliquent.",
        "quand_ca_coince": "Un PUE engagé au marché sans plan de comptage. La "
                           "clause est invérifiable, donc inopposable — et "
                           "c'est le titulaire qui en profite.",
    },
    "autorites": {
        "nom": "Autorités et concessionnaires",
        "decide": "Les autorisations d'urbanisme et d'exploiter, les "
                  "raccordements, les conditions de rejet et de prélèvement.",
        "a_besoin_de": "Des dossiers complets et des données stabilisées. "
                       "Toute modification substantielle relance "
                       "l'instruction.",
        "fenetre": "Les délais d'instruction sont des jalons fixes, pas des "
                   "tâches à durée ajustable. Ils se placent au planning "
                   "directeur.",
        "quand_ca_coince": "Un équipement ajouté en cours de projet qui fait "
                           "franchir un seuil réglementaire. Le régime change, "
                           "et avec lui le calendrier de tout le programme.",
    },
    "rse": {
        "nom": "Direction RSE et rapportage extra-financier",
        "decide": "Les engagements publics, le périmètre de rapportage, les "
                  "objectifs de trajectoire carbone.",
        "a_besoin_de": "Des données MESURÉES et un périmètre stable — pas des "
                       "ordres de grandeur de conception reconduits d'année "
                       "en année.",
        "fenetre": "Le plan de comptage se conçoit avec l'installation. "
                   "Ajouté après, il mesure ce qu'on a bien voulu instrumenter.",
        "quand_ca_coince": "Un engagement public pris sur une valeur de "
                           "conception. Elle sera comparée à une valeur "
                           "mesurée, et l'écart sera public.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  4. CE QUE L'INTERNATIONAL CHANGE
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE LA TABLE EXISTE POUR EMPÊCHER. Un programme qui réplique son dossier
# français dans trois pays produit trois fois le même document, faux deux fois.
# Chaque ligne nomme une chose qui ne se réplique PAS, et ce qu'il faut faire à
# la place.

INTERNATIONAL = [
    {
        "cle": "reglementaire",
        "sujet": "Le cadre réglementaire ne se transpose pas",
        "detail": "La nomenclature des installations classées est française. "
                  "Le régime, les seuils, les délais d'instruction et l'autorité "
                  "compétente changent à chaque frontière — y compris dans "
                  "l'Union, où les directives sont transposées différemment.",
        "a_faire": "Un criblage réglementaire par pays, mené avec un conseil "
                   "local, et un jalon d'instruction propre à chaque site au "
                   "planning directeur.",
    },
    {
        "cle": "carbone",
        "sujet": "L'intensité carbone du réseau varie d'un facteur cinq",
        "detail": "Le même site, à conception identique, émet cinq fois plus "
                  "dans un pays à mix fossile que dans un pays décarboné. Un "
                  "bilan de programme calculé avec un facteur unique est faux "
                  "pour tous les sites sauf un.",
        "a_faire": "Le facteur du pays pour chaque site, et le facteur du "
                   "CONTRAT quand il existe — les deux se déclarent séparément "
                   "au titre de la double comptabilisation.",
    },
    {
        "cle": "eau",
        "sujet": "La contrainte en eau est locale, pas nationale",
        "detail": "Le facteur eau de la production électrique dépend du pays ; "
                  "la disponibilité de la ressource dépend du bassin. Deux "
                  "sites d'un même pays peuvent relever de régimes de "
                  "restriction opposés.",
        "a_faire": "Une étude de stress hydrique par site, et un mode de "
                   "refroidissement arbitré site par site plutôt qu'un "
                   "standard de programme.",
    },
    {
        "cle": "normes",
        "sujet": "Les référentiels d'installation sont nationaux",
        "detail": "Les normes d'installation électrique, de sécurité incendie "
                  "et de construction diffèrent, même quand les référentiels "
                  "de conception — Uptime, EN 50600, ASHRAE — sont communs.",
        "a_faire": "Un socle technique commun de programme, et une couche "
                   "d'adaptation nationale explicitement identifiée dans "
                   "chaque spécification.",
    },
    {
        "cle": "marche",
        "sujet": "Le droit du marché et la langue contractuelle",
        "detail": "La forme des pièces, le régime des pénalités, la réception "
                  "et les garanties relèvent du droit du lieu d'exécution. La "
                  "langue du contrat décide de la version qui fait foi.",
        "a_faire": "Une trame contractuelle de programme, déclinée par un "
                   "conseil local, avec la langue faisant foi désignée dans "
                   "chaque marché.",
    },
    {
        "cle": "equipes",
        "sujet": "Les équipes projet ne partagent ni fuseau ni vocabulaire",
        "detail": "Les mêmes sigles désignent des choses différentes d'un pays "
                  "à l'autre, et les phases n'ont pas les mêmes frontières — "
                  "la maîtrise d'œuvre à la française n'a pas d'équivalent "
                  "exact dans une organisation EPC.",
        "a_faire": "Un glossaire de programme et une correspondance de phases "
                   "écrites une fois, servies à tous. Une correspondance "
                   "supposée se découvre au moment d'un jalon manqué.",
    },
    {
        "cle": "devise",
        "sujet": "Un budget multi-devises n'est pas un budget",
        "detail": "Consolider des montants en devises différentes sans dire "
                  "à quel cours et à quelle date produit une dérive "
                  "budgétaire qui n'est qu'un mouvement de change.",
        "a_faire": "Une devise de référence, un cours de budget figé à la "
                   "décision d'investissement, et l'effet de change isolé de "
                   "la dérive réelle.",
    },
]


# ═══════════════════════════════════════════════════════════════════════════
#  5. LA LIVRAISON « ZÉRO DÉFAUT »
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE L'EXPRESSION VEUT DIRE, ET CE QU'ELLE NE PEUT PAS VOULOIR DIRE. « Zéro
# défaut » ne signifie pas qu'aucun écart ne sera constaté : sur un ouvrage de
# cette taille, une réception sans aucune réserve signale une réception mal
# faite, pas un ouvrage parfait. Elle signifie qu'AUCUN défaut ne subsiste au
# transfert à l'exploitation — ce qui est une exigence de PROCESSUS, pas de
# perfection.
#
# LA DIFFÉRENCE EST OPÉRATIONNELLE : la première promesse ne se tient jamais et
# fait mentir les procès-verbaux ; la seconde se tient, et elle se planifie.

ZERO_DEFAUT = {
    "definition": "Aucun défaut subsistant au transfert à l'exploitation : "
                  "les écarts sont constatés, tracés, corrigés et vérifiés "
                  "AVANT la remise, et non reportés sur une liste de réserves "
                  "que l'exploitant héritera.",
    "n_est_pas": "Une réception sans réserve. Sur un ouvrage de cette taille, "
                 "zéro réserve au procès-verbal signale une visite trop "
                 "rapide, pas un ouvrage parfait — et les défauts non "
                 "constatés se paient en exploitation, sans recours.",
    "conditions": [
        "Un programme d'essais contractualisé au marché, avec ses critères de "
        "réussite et les moyens à fournir : bancs de charge, combustible, "
        "disponibilité des équipes.",
        "Des points d'arrêt écrits AVANT la consultation sur tout ouvrage "
        "destiné à être caché — un ouvrage fermé ne se contrôle plus, il se "
        "rouvre.",
        "Des essais par système clos avant tout essai intégré : un écart en "
        "essai intégré sur des systèmes non clos devient inattribuable, et "
        "chaque entreprise désigne l'autre.",
        "L'exploitant associé dès les essais fonctionnels, et non convoqué à "
        "la remise des clés.",
        "La réception conditionnée à la remise du dossier d'exploitation "
        "complet, avec le solde lié — c'est le seul moment où un moyen de "
        "pression existe.",
        "Un délai de levée écrit au procès-verbal : une réserve sans délai ne "
        "se lève pas, elle se discute.",
    ],
    "mesure": "Le taux de levée des réserves à la date de transfert, et le "
              "nombre de réserves BLOQUANTES restantes — les deux ensemble. "
              "Un taux de levée de 95 % dont les 5 % restants portent sur une "
              "bascule de chaîne électrique interdit l'exploitation.",
    "cout": "Une mission de commissioning commencée à l'avant-projet et non "
            "au chantier, des bancs de charge et du combustible chiffrés au "
            "marché, et un calendrier de fin de chantier qui réserve du temps "
            "aux essais plutôt que de les comprimer. C'est ce que coûte la "
            "promesse, et l'annoncer sans le chiffrer revient à ne pas la "
            "faire.",
}


# ═══════════════════════════════════════════════════════════════════════════
#  LA CONSOLIDATION
# ═══════════════════════════════════════════════════════════════════════════

def _nombre(v):
    """Une valeur numérique utilisable, ou None.

    Les non finies sont écartées comme absentes : un NaN qui traverse une somme
    la rend NaN tout entière, et un total NaN s'affiche « NaN » dans une
    diapositive de comité exécutif — ou casse la sérialisation JSON avant.
    """
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _agreger(sites, champ):
    """Somme d'un champ, avec le compte de ce qui manque.

    LE COMPTE DES ABSENTS VOYAGE AVEC LA SOMME, toujours. Un CAPEX de programme
    calculé sur quatre sites renseignés sur sept n'est pas le CAPEX du
    programme : c'est un sous-total, et le présenter autrement est la façon la
    plus rapide de perdre la confiance d'un comité — parce qu'il s'en
    apercevra.
    """
    valeurs, absents = [], []
    for s in sites:
        v = _nombre(s.get(champ))
        if v is None:
            absents.append(s.get("nom") or "site sans nom")
        else:
            valeurs.append(v)
    return {"valeur": sum(valeurs) if valeurs else None,
            "sites_comptes": len(valeurs), "sites_absents": absents,
            "complet": not absents}


def _pondere(sites, champ, poids):
    """Moyenne pondérée d'un champ, ou None.

    POURQUOI ELLE EXISTE PLUTÔT QU'UNE MOYENNE SIMPLE. La moyenne arithmétique
    des PUE de site est ce qu'on calcule spontanément, et elle est fausse : un
    site de dix mégawatts à 1,5 et un site de cent kilowatts à 1,1 ne pèsent
    pas pareil, et leur moyenne — 1,3 — ne correspond à aucune réalité
    physique. On pondère donc par la grandeur qui porte le sens.
    """
    num = den = 0.0
    comptes, absents = 0, []
    for s in sites:
        v, p = _nombre(s.get(champ)), _nombre(s.get(poids))
        if v is None or p is None or p <= 0:
            absents.append(s.get("nom") or "site sans nom")
            continue
        num += v * p
        den += p
        comptes += 1
    return {"valeur": (num / den) if den else None,
            "sites_comptes": comptes, "sites_absents": absents,
            "complet": not absents, "pondere_par": poids}


def consolider(sites):
    """La vue de programme : ce qui s'additionne, ce qui se pondère, ce qui ne
    se consolide pas.

    `sites` : une liste de dicts. Les clés reconnues sont celles de CHAMPS_SITE.
    Aucune n'est obligatoire — un site connu par son seul nom compte dans
    l'effectif et figure dans les absents de tout le reste, ce qui est
    exactement l'information utile en début de programme.
    """
    sites = [s for s in (sites or []) if isinstance(s, dict)]
    if not sites:
        return {"version": VERSION, "sites": 0, "vide": True,
                "note": ("Aucun site déclaré. Un programme se pilote sur ses "
                         "sites : sans eux, il n'y a rien à consolider — et "
                         "surtout rien à conclure."),
                "reserve": RESERVE}

    livres = [s for s in sites if s.get("receptionne")]
    capacite = _agreger(sites, "puissance_it_kw")
    capacite_livree = _agreger(livres, "puissance_it_kw")
    capex = _agreger(sites, "capex_eur")
    opex = _agreger(sites, "opex_eur_an")

    # L'énergie informatique sert de poids au PUE. Elle se déduit de la
    # puissance et du taux de charge quand il est là ; à défaut, la puissance
    # seule pondère — imparfait, et dit.
    enrichis = []
    for s in sites:
        p = _nombre(s.get("puissance_it_kw"))
        t = _nombre(s.get("taux_charge"))
        enrichis.append(dict(s, _poids_energie=(p * t if (p and t) else p)))
    pue = _pondere(enrichis, "pue", "_poids_energie")

    out = {
        "version": VERSION,
        "sites": len(sites),
        "sites_livres": len(livres),
        "capacite_engagee_kw": capacite,
        "capacite_livree_kw": capacite_livree,
        "capex_eur": capex,
        "opex_eur_an": opex,
        "pue_programme": pue,
        "capex_par_kw": _ratio(capex, capacite, "€/kW"),
        "opex_par_kw_an": _ratio(opex, capacite, "€/kW/an"),
        "par_nature": _par_nature(sites),
        "par_phase": _par_phase(sites),
        "par_pays": _par_pays(sites),
        "chemin_critique": _chemin_critique(sites),
        "energisation": _energisation(sites),
        "zero_defaut": _etat_zero_defaut(sites),
        "non_consolidables": _non_consolidables(sites),
        "reserve": RESERVE,
    }
    out["lecture"] = _lecture(out)
    return out


def _ratio(haut, bas, unite):
    """Un ratio, ou l'explication de son absence.

    UN RATIO CALCULÉ SUR DEUX SOUS-TOTAUX DIFFÉRENTS N'EST PAS UN RATIO. Si le
    CAPEX est connu sur quatre sites et la puissance sur sept, leur quotient ne
    décrit aucun ensemble. Il n'est donc rendu que sur le périmètre COMMUN, et
    le périmètre est dit.
    """
    if not haut["valeur"] or not bas["valeur"]:
        return {"valeur": None, "unite": unite,
                "pourquoi": "Une des deux grandeurs n'est renseignée sur aucun "
                            "site."}
    if haut["sites_comptes"] != bas["sites_comptes"]:
        return {"valeur": None, "unite": unite,
                "pourquoi": ("Les deux grandeurs ne couvrent pas les mêmes "
                             "sites (%d contre %d) : leur quotient ne "
                             "décrirait aucun ensemble réel. Renseignez les "
                             "deux sur le même périmètre."
                             % (haut["sites_comptes"], bas["sites_comptes"]))}
    return {"valeur": haut["valeur"] / bas["valeur"], "unite": unite,
            "sites_comptes": haut["sites_comptes"],
            "complet": haut["complet"] and bas["complet"]}


def _par_nature(sites):
    out = {}
    for cle in NATURES_SITE:
        lot = [s for s in sites if s.get("nature") == cle]
        out[cle] = {"nom": NATURES_SITE[cle]["nom"], "sites": len(lot),
                    "capacite_kw": _agreger(lot, "puissance_it_kw")["valeur"]}
    inconnus = [s.get("nom") or "?" for s in sites
                if s.get("nature") not in NATURES_SITE]
    if inconnus:
        out["_sans_nature"] = {
            "nom": "Nature non déclarée", "sites": len(inconnus),
            "pourquoi": ("Sans nature, on ne sait pas si le site se chiffre "
                         "comme un terrain nu ou comme une reprise "
                         "d'existant — un écart qui se découvre en exécution."),
            "lesquels": inconnus}
    return out


def _par_phase(sites):
    """La répartition par phase, dans l'ordre du cadre et non alphabétique.

    L'ordre vient du référentiel : trié autrement, un programme paraîtrait
    avancer en désordre.
    """
    try:
        import ingenierie_dc as _g
        ordre = [p["code"] for p in _g.PHASES]
        noms = {p["code"]: p["nom"] for p in _g.PHASES}
    except Exception:                                    # pragma: no cover
        ordre, noms = [], {}
    compte = {}
    for s in sites:
        c = (s.get("phase") or "").upper() or "?"
        compte[c] = compte.get(c, 0) + 1
    connues = [{"code": c, "nom": noms.get(c, c), "sites": compte[c]}
               for c in ordre if c in compte]
    autres = [{"code": c, "nom": c, "sites": n, "hors_cadre": True}
              for c, n in sorted(compte.items()) if c not in ordre]
    return connues + autres


def _par_pays(sites):
    """Les sites par pays, avec ce qui ne se réplique pas d'un pays à l'autre.

    LE COMPTE SEUL NE SERT À RIEN. Ce qui sert, c'est que passer une frontière
    change le cadre réglementaire, le facteur carbone, la contrainte en eau et
    le droit du marché — et que la liste le rappelle là où elle est utile.
    """
    par = {}
    for s in sites:
        p = (s.get("pays") or "?").upper()
        par.setdefault(p, []).append(s.get("nom") or "?")
    out = [{"pays": p, "sites": len(v), "lesquels": v}
           for p, v in sorted(par.items())]
    if len(par) > 1:
        for x in out:
            x["multi_pays"] = True
    return {"pays": out, "multi_pays": len(par) > 1,
            "ce_qui_ne_se_replique_pas": (
                [dict(x) for x in INTERNATIONAL] if len(par) > 1 else [])}


def _chemin_critique(sites):
    """Le site qui commande la date de fin du programme.

    PAS UNE MOYENNE, JAMAIS. Un programme livre quand son DERNIER site livre,
    et une dérive moyenne masque précisément celui qui commande la date.
    """
    dates = [(s.get("mise_en_service"), s.get("nom") or "?")
             for s in sites if s.get("mise_en_service")]
    if not dates:
        return {"connu": False,
                "pourquoi": ("Aucune date de mise en service n'est déclarée. "
                             "Le chemin critique d'un programme est le site le "
                             "plus tardif : sans dates, il n'y a pas de "
                             "chemin critique, il y a une liste de sites.")}
    dernier = max(dates, key=lambda d: str(d[0]))
    return {"connu": True, "site": dernier[1], "date": dernier[0],
            "sites_dates": len(dates), "sites_sans_date": len(sites) - len(dates),
            "note": ("Le programme livre quand ce site livre. Les %d site(s) "
                     "sans date déclarée peuvent le déplacer."
                     % (len(sites) - len(dates))) if len(dates) < len(sites)
                    else "Le programme livre quand ce site livre."}


def _energisation(sites):
    """La date de mise sous tension du programme : la PLUS TARDIVE.

    MÊME RÈGLE QUE LE CHEMIN CRITIQUE, et pour la même raison : un programme
    est sous tension quand son dernier site l'est. La moyenne des dates
    n'existe pas, et elle masquerait le site qui commande.
    """
    dates = [(s.get("energisation"), s.get("nom") or "?")
             for s in sites if s.get("energisation")]
    if not dates:
        return {"connu": False,
                "pourquoi": ("Aucune date de mise sous tension n'est "
                             "déclarée. C'est pourtant le poste le plus long "
                             "du programme : sans lui, le calendrier annoncé "
                             "repose sur des durées de chantier, qui ne sont "
                             "pas ce qui commande.")}
    dernier = max(dates, key=lambda d: str(d[0]))
    sans = len(sites) - len(dates)
    return {"connu": True, "site": dernier[1], "date": dernier[0],
            "sites_dates": len(dates), "sites_sans_date": sans,
            "note": ("Le programme est sous tension quand ce site l'est."
                     + ("" if not sans else
                        " Les %d site(s) sans date déclarée peuvent le "
                        "déplacer, et rien ne dit qu'ils soient plus tôt."
                        % sans))}


def _etat_zero_defaut(sites):
    """L'état de la promesse « zéro défaut » sur le programme.

    DEUX CHIFFRES ENSEMBLE, jamais l'un sans l'autre : le taux de levée et le
    nombre de réserves BLOQUANTES. Un taux de 95 % dont les 5 % restants
    portent sur une bascule de chaîne électrique interdit l'exploitation, et le
    taux seul le cache.
    """
    ouvertes = _agreger(sites, "reserves_ouvertes")
    levees = _agreger(sites, "reserves_levees")
    bloquantes = _agreger(sites, "reserves_bloquantes")
    total = (ouvertes["valeur"] or 0) + (levees["valeur"] or 0)
    taux = (levees["valeur"] / total) if total else None
    return {
        "reserves_ouvertes": ouvertes,
        "reserves_levees": levees,
        "reserves_bloquantes": bloquantes,
        "taux_de_levee": taux,
        "definition": ZERO_DEFAUT["definition"],
        "n_est_pas": ZERO_DEFAUT["n_est_pas"],
        "lecture": _lecture_reserves(taux, bloquantes["valeur"]),
    }


def _lecture_reserves(taux, bloquantes):
    if taux is None:
        return ("Aucune réserve n'est déclarée. Ce n'est pas « zéro défaut » : "
                "c'est « pas encore constaté ». Sur un ouvrage de cette "
                "taille, zéro réserve au procès-verbal signale une visite "
                "trop rapide, pas un ouvrage parfait.")
    if bloquantes:
        return ("%d réserve(s) bloquante(s) subsistent malgré un taux de levée "
                "de %d %%. Le taux ne dit rien ici : une réserve bloquante "
                "interdit l'exploitation quel que soit le nombre de réserves "
                "levées à côté." % (int(bloquantes), round(taux * 100)))
    return ("Taux de levée de %d %%, sans réserve bloquante déclarée. La "
            "promesse tient si les réserves restantes ont un délai de levée "
            "écrit au procès-verbal — sans délai, une réserve ne se lève pas, "
            "elle se discute." % round(taux * 100))


def _non_consolidables(sites):
    """Ce qui ne se consolide PAS, dit explicitement.

    UNE ABSENCE SILENCIEUSE SE LIT COMME UN OUBLI. Le régime administratif est
    la grandeur qu'un comité demande le plus souvent d'agréger, et c'est
    précisément celle qui ne s'agrège pas : la nomenclature est nationale, et
    un chiffre unique tiendrait lieu de plusieurs cadres qui ne se comparent
    pas.
    """
    return [{
        "grandeur": KPI["regime_icpe"]["nom"],
        "pourquoi": KPI["regime_icpe"]["n_indique_pas"],
        "a_la_place": ("Le régime de chaque site, avec son pays et son délai "
                       "d'instruction, porté au planning directeur comme un "
                       "jalon fixe."),
        "sites": [{"nom": s.get("nom") or "?", "pays": (s.get("pays") or "?"),
                   "regime": s.get("regime_icpe") or "non criblé"}
                  for s in sites],
    }]


def _lecture(vue):
    """La phrase qu'un directeur de programme lit en premier.

    ELLE DIT D'ABORD CE QUI MANQUE. Un tableau de bord qui ouvre sur ses
    totaux fait croire à un état complet ; celui-ci ouvre sur son périmètre,
    parce que c'est lui qui décide de ce que les totaux valent.
    """
    n = vue["sites"]
    cap = vue["capacite_engagee_kw"]
    bouts = []
    if not cap["complet"]:
        bouts.append("La capacité est renseignée sur %d site(s) sur %d : tous "
                     "les totaux qui en découlent sont des SOUS-TOTAUX."
                     % (cap["sites_comptes"], n))
    if cap["valeur"]:
        livree = vue["capacite_livree_kw"]["valeur"] or 0
        bouts.append("%s kW engagés, %s kW livrés (%d %%)."
                     % (_fr(cap["valeur"]), _fr(livree),
                        round(100 * livree / cap["valeur"])))
    if vue["par_pays"]["multi_pays"]:
        bouts.append("Programme multi-pays : le cadre réglementaire, le "
                     "facteur carbone, la contrainte en eau et le droit du "
                     "marché ne se répliquent pas d'un site à l'autre.")
    if vue["pue_programme"]["valeur"]:
        bouts.append("PUE de programme pondéré par l'énergie informatique — "
                     "la moyenne simple des sites en aurait donné un autre, "
                     "et il aurait été faux.")
    return " ".join(bouts) or ("Aucune grandeur consolidable n'est encore "
                               "renseignée.")


def _fr(x):
    if x is None:
        return "—"
    return ("%d" % round(x)).replace(",", " ")


RESERVE = (
    "CETTE VUE CONSOLIDE CE QU'ON LUI DONNE, et rien d'autre. Elle ne va "
    "chercher aucune donnée, ne corrige aucune saisie et n'estime aucun site "
    "manquant : chaque total porte le nombre de sites qu'il couvre, et les "
    "sites absents sont nommés. Un ratio dont les deux termes ne portent pas "
    "sur le même périmètre n'est pas rendu — il ne décrirait aucun ensemble "
    "réel. Le régime administratif ne se consolide pas du tout, et la vue le "
    "dit plutôt que de l'omettre.")


# ═══════════════════════════════════════════════════════════════════════════
#  LES ENTRÉES
# ═══════════════════════════════════════════════════════════════════════════
# AUCUNE N'EST OBLIGATOIRE. Un site connu par son seul nom compte dans
# l'effectif et figure dans les absents de tout le reste — c'est exactement
# l'information utile au début d'un programme, quand la moitié des sites n'est
# qu'une intention.

CHAMPS_SITE = [
    {"id": "nom", "label": "Nom du site", "type": "texte"},
    {"id": "pays", "label": "Pays", "type": "texte",
     "aide": "Il commande le cadre réglementaire, le facteur carbone du "
             "réseau et le facteur eau de la production électrique."},
    {"id": "nature", "label": "Nature du site", "type": "liste",
     "options": list(NATURES_SITE),
     "aide": "Greenfield ou brownfield. Un brownfield se redescend ensuite en "
             "fit-out ou rétrofit : les deux n'ont ni le même risque ni le "
             "même prix."},
    {"id": "phase", "label": "Phase en cours", "type": "texte",
     "aide": "Le code de phase du cadre d'ingénierie — ESQ, APD, DCE, EXE…"},
    {"id": "puissance_it_kw", "label": "Puissance informatique", "unite": "kW",
     "type": "nombre",
     "aide": "La grandeur de référence du programme : budget, carbone et "
             "effectifs s'y rapportent tous."},
    {"id": "taux_charge", "label": "Taux de charge moyen", "unite": "0–1",
     "type": "nombre",
     "aide": "Sert à pondérer le PUE de programme par l'énergie réellement "
             "consommée. Sans lui, la pondération se fait sur la puissance "
             "installée — imparfait, et signalé."},
    {"id": "pue", "label": "PUE du site", "type": "nombre",
     "aide": "Mesuré si le site est en exploitation, visé sinon. Les deux ne "
             "se mélangent pas dans une même consolidation sans le dire."},
    {"id": "capex_eur", "label": "Investissement", "unite": "€", "type": "nombre",
     "aide": "Dans la devise de référence du programme. Consolider des "
             "montants en devises différentes sans dire à quel cours produit "
             "une dérive qui n'est qu'un mouvement de change."},
    {"id": "opex_eur_an", "label": "Charges d'exploitation annuelles",
     "unite": "€/an", "type": "nombre"},
    {"id": "mise_en_service", "label": "Mise en service attendue",
     "type": "texte",
     "aide": "Le site le plus tardif commande la date du programme. Format "
             "libre, mais comparable — une année, ou une date ISO."},
    {"id": "energisation", "label": "Mise sous tension attendue",
     "type": "texte",
     "aide": "La date de disponibilité de la puissance définitive, distincte "
             "de la mise en service. Sur un raccordement non ferme, c'est la "
             "date à laquelle la puissance EFFAÇABLE est disponible : "
             "précisez-le, les deux ne valent pas la même chose."},
    {"id": "receptionne", "label": "Réception prononcée", "type": "booleen",
     "aide": "Un site réceptionné avec réserves compte comme livré : ses "
             "réserves se suivent à part."},
    {"id": "reserves_ouvertes", "label": "Réserves ouvertes", "type": "nombre"},
    {"id": "reserves_levees", "label": "Réserves levées", "type": "nombre"},
    {"id": "reserves_bloquantes", "label": "Dont bloquantes", "type": "nombre",
     "aide": "Celles qui interdisent l'exploitation. Le taux de levée ne les "
             "voit pas, et c'est pourquoi les deux se présentent ensemble."},
    {"id": "regime_icpe", "label": "Régime administratif", "type": "texte",
     "aide": "Le régime du site selon la réglementation de SON pays. Il ne se "
             "consolide pas au niveau du programme."},
]


def referentiel():
    """Les tables, sans consolidation — pour la page et la documentation."""
    return {
        "version": VERSION,
        "natures_site": NATURES_SITE,
        "kpi": KPI,
        "consolidations": CONSOLIDATIONS,
        "parties_prenantes": PARTIES_PRENANTES,
        "international": INTERNATIONAL,
        "zero_defaut": ZERO_DEFAUT,
        "champs_site": CHAMPS_SITE,
        "reserve": RESERVE,
        "glossaire": glossaire(),
    }


def glossaire():
    """Les familles d'infobulles servies par ce module."""
    return {
        "nature_site": {k: {
            "nom": v["nom"],
            "aide": ("%s\n\nLe délai qui domine — %s\n\nLe risque de "
                     "programme — %s"
                     % (v["ce_que_c_est"], v["delai_dominant"],
                        v["risque_programme"])),
        } for k, v in NATURES_SITE.items()},
        "kpi": {k: {
            "nom": "%s (%s)" % (v["nom"], v["unite"]),
            "aide": ("%s\n\nCe qu'il n'indique pas — %s\n\nPourquoi il "
                     "compte — %s\n\nConsolidation — %s%s"
                     % (v["definition"], v["n_indique_pas"], v["pourquoi"],
                        CONSOLIDATIONS[v["consolidation"]],
                        ("\n\nLe piège — " + v["piege"]) if v.get("piege")
                        else "")),
        } for k, v in KPI.items()},
        "partie_prenante": {k: {
            "nom": v["nom"],
            "aide": ("Ce qu'elle décide — %s\n\nCe dont elle a besoin — %s\n\n"
                     "Sa fenêtre — %s\n\nQuand ça coince — %s"
                     % (v["decide"], v["a_besoin_de"], v["fenetre"],
                        v["quand_ca_coince"])),
        } for k, v in PARTIES_PRENANTES.items()},
    }


# ═══════════════════════════════════════════════════════════════════════════
#  LES CONTRÔLES DE COHÉRENCE
# ═══════════════════════════════════════════════════════════════════════════

def _verifier():
    """Les fautes de structure, ou une liste vide.

    LA VÉRIFICATION QUI COMPTE porte sur la CONSOLIDATION déclarée de chaque
    indicateur : un indicateur `pondere` sans dire par quoi laisserait la page
    calculer une moyenne simple, qui est le défaut que cette table existe pour
    empêcher.
    """
    fautes = []
    for k, v in KPI.items():
        for champ in ("nom", "definition", "n_indique_pas", "pourquoi"):
            if not (v.get(champ) or "").strip():
                fautes.append("indicateur %s : champ « %s » vide" % (k, champ))
        c = v.get("consolidation")
        if c not in CONSOLIDATIONS:
            fautes.append("indicateur %s : consolidation inconnue (%s)" % (k, c))
        if c == "pondere" and not v.get("pondere_par"):
            fautes.append("indicateur %s : pondéré sans dire par quoi — la "
                          "page calculerait une moyenne simple" % k)
        if c == "extremum" and not v.get("extremum"):
            fautes.append("indicateur %s : extremum sans dire lequel" % k)
    for k, v in NATURES_SITE.items():
        if not v.get("travaux"):
            fautes.append("nature de site %s : aucune nature de travaux" % k)
        for champ in ("nom", "ce_que_c_est", "delai_dominant",
                      "risque_programme"):
            if not (v.get(champ) or "").strip():
                fautes.append("nature de site %s : champ « %s » vide" % (k, champ))
    for k, v in PARTIES_PRENANTES.items():
        for champ in ("nom", "decide", "a_besoin_de", "fenetre",
                      "quand_ca_coince"):
            if not (v.get(champ) or "").strip():
                fautes.append("partie prenante %s : champ « %s » vide" % (k, champ))
    vus = set()
    for x in INTERNATIONAL:
        if x["cle"] in vus:
            fautes.append("point international en double : %s" % x["cle"])
        vus.add(x["cle"])
        for champ in ("sujet", "detail", "a_faire"):
            if not (x.get(champ) or "").strip():
                fautes.append("point international %s : champ « %s » vide"
                              % (x["cle"], champ))
    if not ZERO_DEFAUT.get("conditions"):
        fautes.append("« zéro défaut » sans condition : la promesse serait "
                      "annoncée sans son prix")
    # Les natures de travaux citées doivent exister : une nature inconnue
    # ferait rendre une liste vide là où le programme attend un métier.
    try:
        import technique_dc as _t
        connues = set(_t.NATURES_TRAVAUX)
    except Exception:                                    # pragma: no cover
        connues = None
    if connues is not None:
        citees = {c for v in NATURES_SITE.values() for c in v["travaux"]}
        for c in sorted(citees - connues):
            fautes.append("nature de travaux inconnue : %s" % c)
        for c in sorted(connues - citees):
            fautes.append("nature de travaux orpheline, rattachée à aucune "
                          "nature de site : %s" % c)
    return fautes


_FAUTES = _verifier()
if _FAUTES:
    raise RuntimeError("programme_dc — table incohérente : " + " ; ".join(_FAUTES))
