# -*- coding: utf-8 -*-
"""L'ingénierie de la durabilité et la décarbonation d'un centre de données.

CE QUE CE MODULE FAIT, ET POURQUOI IL EXISTE À CÔTÉ DU RESTE

`datacenter.py` calcule une énergie, une eau, un carbone. `ingenierie_dc.py`
dit à quel moment d'un PROJET ces chiffres deviennent recevables. Il manquait
la troisième question, et c'est celle que pose un directeur de la durabilité :
**dans quel ordre décarbone-t-on, et qu'a-t-on le droit d'en dire ?**

Ce sont deux exercices distincts, et les confondre est l'erreur la plus commune
du domaine :

  · COMPTER ET DÉCLARER. Périmètre, année de référence, inventaire, indicateurs
    normalisés, déclaration réglementaire, vérification. Cette voie produit des
    CHIFFRES OPPOSABLES. Elle ne réduit rien.

  · RÉDUIRE. Diagnostic, cible, puis la hiérarchie d'atténuation dans son ordre :
    éviter, réduire, substituer, et seulement ensuite traiter le résiduel. Cette
    voie produit des TONNES ÉVITÉES. Elle ne prouve rien tant que la première
    n'a pas posé la référence.

Un plan de décarbonation sans inventaire vérifié est une intention. Un
inventaire sans trajectoire est un constat. Les deux voies sont donc décrites
côte à côte, avec leurs points de rendez-vous obligés.

LA RÈGLE QUI GOUVERNE CE FICHIER

**La compensation n'est pas une réduction.** La hiérarchie d'atténuation est
codée, pas illustrée : un levier de rang « compenser » ne peut déclarer aucun
paramètre du moteur, et le module refuse de se charger s'il en déclare un. La
raison est concrète : si la compensation portait un paramètre, la page
afficherait un « résultat » de compensation au même rang qu'un gain
d'efficacité, et le lecteur additionnerait les deux. C'est précisément
l'addition que les autorités de la publicité sanctionnent.

CE QUE CE MODULE NE FAIT PAS

Il ne décerne aucune conformité, aucune neutralité, aucun label. Ces
qualifications se constatent sur dossier complet par un vérificateur
accrédité, jamais par un formulaire. Il ne recopie pas non plus les
incertitudes du moteur : elles sont LUES dans `ingenierie_dc.POSTES`, qui les
lit lui-même dans `datacenter.py`. Une valeur retapée ici aurait divergé au
premier ajustement du référentiel.
"""

import datacenter as D
import ingenierie_dc as G
import profil_dc as P

VERSION = "2026-08-a"


# ═══════════════════════════════════════════════════════════════════════════
#  1. LES DEUX VOIES
# ═══════════════════════════════════════════════════════════════════════════

VOIES = {
    "inventaire": {
        "nom": "Compter et déclarer",
        "cadre": "GHG Protocol — Corporate Accounting and Reporting Standard "
                 "(WRI/WBCSD) et sa Scope 2 Guidance (2015) ; ISO 14064-1:2018 "
                 "pour la quantification à l'échelle de l'organisation ; "
                 "ISO/IEC 30134 et EN 50600-4 pour les indicateurs propres aux "
                 "centres de données ; directive (UE) 2023/1791, article 12, et "
                 "règlement délégué (UE) 2024/1364 pour la déclaration ; "
                 "directive (UE) 2022/2464 (CSRD) et norme ESRS E1 pour le "
                 "rapport de durabilité.",
        "portee": "C'est la voie de la PREUVE. Elle produit des chiffres qu'un "
                  "tiers peut vérifier et qu'un régulateur peut opposer. Elle ne "
                  "fait baisser aucune émission — c'est l'autre voie qui s'en "
                  "charge — mais sans elle aucune baisse n'est démontrable.",
        "note": "Le périmètre d'assujettissement du rapport de durabilité "
                "européen a été rouvert en 2025 par le paquet dit « omnibus » : "
                "seuils et calendrier sont en cours de révision. La STRUCTURE de "
                "l'exercice décrite ici ne change pas ; l'assujettissement de "
                "votre entité, lui, se vérifie à la date du dossier et non sur "
                "cette page.",
    },
    "trajectoire": {
        "nom": "Réduire",
        "cadre": "Hiérarchie d'atténuation : éviter, réduire, substituer, et "
                 "seulement ensuite traiter le résiduel. ISO 14068-1:2023 pour "
                 "les conditions d'une allégation de neutralité carbone ; "
                 "Science Based Targets initiative pour la cible et sa "
                 "trajectoire ; ESRS E1 pour le plan de transition.",
        "portee": "C'est la voie de l'ACTION. Elle classe les leviers dans "
                  "l'ordre où ils doivent être épuisés, et dit pour chacun ce "
                  "qu'il fait — et surtout ce qu'il ne fait pas.",
        "note": "L'ordre n'est pas une préférence morale, c'est une contrainte "
                "de méthode : un levier de rang inférieur n'est recevable que "
                "si les rangs supérieurs ont été examinés et documentés. "
                "ISO 14068-1 en fait une condition de l'allégation, pas une "
                "recommandation.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  2. LES TEXTES CITÉS, ET CE QU'ILS PÈSENT
#
#  Un référentiel volontaire et un règlement européen ne s'opposent pas de la
#  même façon. Les afficher au même rang ferait promettre à un client une
#  obligation là où il n'y a qu'un engagement de place — ou l'inverse, plus
#  grave.
# ═══════════════════════════════════════════════════════════════════════════

PORTEES = {
    "contraignant": "Texte contraignant. Son non-respect est sanctionnable.",
    "norme": "Norme volontaire. Elle n'oblige que si un contrat, un label ou un "
             "texte s'y réfère — ce qui est fréquent, et c'est alors le texte "
             "renvoyant qui oblige.",
    "auto_regulation": "Engagement de place, souscrit volontairement. Il engage "
                       "la réputation de son signataire et rien d'autre.",
    "methode": "Méthode de place, largement reprise par les vérificateurs et "
               "les investisseurs. Sans valeur réglementaire propre.",
}

# L'ORDRE DE POIDS, DÉCLARÉ — il ne se déduit pas du dictionnaire.
# `PORTEES` est écrit dans le bon ordre, mais la sérialisation JSON TRIE les
# clés : servi tel quel, le vocabulaire arrivait à la page par ordre
# ALPHABÉTIQUE — « engagement de place » avant « texte contraignant ». Une
# interface qui s'ouvrirait dessus présenterait d'abord ce qui n'oblige à rien,
# et c'est précisément l'erreur que cette section existe pour empêcher : un
# client à qui l'on promet une obligation là où il n'y a qu'un engagement de
# place prend une décision sur une contrainte qui n'existe pas.
#
# L'ordre est donc une DONNÉE, pas un effet de bord de l'itération, et un
# contrôle vérifie qu'il couvre exactement le vocabulaire.
PORTEES_ORDRE = ["contraignant", "norme", "auto_regulation", "methode"]

TEXTES = {
    "ghg_corp": {
        "nom": "GHG Protocol — Corporate Accounting and Reporting Standard",
        "portee": "methode",
        "dit": "Fixe les périmètres organisationnel (part du capital, contrôle "
               "financier, contrôle opérationnel) et opérationnel (scopes 1, 2 "
               "et 3), et la politique de recalcul de l'année de référence.",
    },
    "ghg_scope2": {
        "nom": "GHG Protocol — Scope 2 Guidance (2015)",
        "portee": "methode",
        "dit": "Impose la DOUBLE déclaration du scope 2 : une fois selon le mix "
               "physique du réseau (location-based), une fois selon les contrats "
               "d'électricité (market-based). Publier la seule seconde est la "
               "façon la plus répandue d'annoncer un zéro qui n'existe pas sur "
               "le réseau.",
    },
    "ghg_scope3": {
        "nom": "GHG Protocol — Corporate Value Chain (Scope 3) Standard",
        "portee": "methode",
        "dit": "Découpe les émissions indirectes de la chaîne de valeur en "
               "quinze catégories. Pour un centre de données, la catégorie 2 "
               "— biens d'équipement — porte le carbone incorporé des serveurs "
               "et du bâtiment, souvent le premier poste après l'électricité.",
    },
    "iso14064_1": {
        "nom": "ISO 14064-1:2018",
        "portee": "norme",
        "dit": "Quantification et déclaration des émissions à l'échelle de "
               "l'organisation. L'édition 2018 range les émissions en catégories "
               "d'émissions directes et indirectes, et non en scopes : la "
               "correspondance avec le GHG Protocol se fait, mais elle ne va "
               "pas de soi et doit être explicitée dans le rapport.",
    },
    "iso14064_3": {
        "nom": "ISO 14064-3:2019",
        "portee": "norme",
        "dit": "Conduite de la validation et de la vérification des déclarations "
               "de gaz à effet de serre — c'est le texte sur lequel travaille le "
               "vérificateur tiers, et donc celui qui décide de ce qui sera "
               "accepté comme preuve.",
    },
    "iso14068": {
        "nom": "ISO 14068-1:2023",
        "portee": "norme",
        "dit": "Conditions d'une allégation de neutralité carbone. Exige une "
               "trajectoire de réduction, l'épuisement documenté des leviers "
               "avant compensation, et des crédits répondant à des critères de "
               "qualité explicites. Remplace la PAS 2060.",
    },
    "iso50001": {
        "nom": "ISO 50001:2018",
        "portee": "norme",
        "dit": "Système de management de l'énergie. C'est la charpente qui rend "
               "une performance énergétique durable plutôt que ponctuelle — et, "
               "en France, l'une des conditions usuelles des dispositifs fiscaux "
               "attachés à l'efficacité énergétique.",
    },
    "iso30134": {
        "nom": "Série ISO/IEC 30134 — indicateurs de performance des centres de "
               "données",
        "portee": "norme",
        "dit": "Définit les indicateurs et, surtout, leurs FRONTIÈRES et leur "
               "période de mesure : PUE (partie 2), facteur d'énergie "
               "renouvelable REF (partie 3), facteur de réutilisation de "
               "l'énergie ERF (partie 6), efficacité d'usage de l'eau WUE "
               "(partie 9). Un PUE annoncé hors de ce cadre n'est pas un PUE.",
        "reserve": "La numérotation des parties évolue au fil des révisions et "
                   "des ajouts. Vérifiez le numéro de partie sur l'édition en "
                   "vigueur avant de le citer dans une pièce contractuelle.",
    },
    "en50600": {
        "nom": "Série EN 50600-4 (et série ISO/IEC 22237 pour l'infrastructure)",
        "portee": "norme",
        "dit": "Déclinaison européenne des mêmes indicateurs, très citée dans "
               "les cahiers des charges du continent. Les deux séries sont "
               "alignées sur le fond ; c'est le texte appelé par le marché qui "
               "décide de celle qu'on applique.",
    },
    "eed_art12": {
        "nom": "Directive (UE) 2023/1791 relative à l'efficacité énergétique, "
               "article 12",
        "portee": "contraignant",
        "dit": "Institue une obligation de déclaration pour les centres de "
               "données au-delà d'un seuil de puissance informatique installée, "
               "et prévoit la publication d'une partie des informations "
               "collectées.",
    },
    "reg2024_1364": {
        "nom": "Règlement délégué (UE) 2024/1364 du 14 mars 2024",
        "portee": "contraignant",
        "dit": "Première phase du dispositif européen de notation : fixe les "
               "informations à déclarer par les centres de données dont la "
               "puissance informatique installée atteint 500 kW — consommation, "
               "PUE, WUE, ERF, part d'énergie renouvelable, chaleur valorisée.",
    },
    "csrd_e1": {
        "nom": "Directive (UE) 2022/2464 (CSRD) et norme ESRS E1 « Changement "
               "climatique »",
        "portee": "contraignant",
        "dit": "Impose, pour les entités assujetties, un plan de transition, la "
               "publication des émissions brutes des scopes 1, 2 et 3 et d'une "
               "intensité rapportée au chiffre d'affaires. « Brutes » est le mot "
               "qui compte : les compensations se déclarent séparément et ne se "
               "déduisent pas.",
        "reserve": "Seuils et calendrier d'assujettissement rouverts en 2025 par "
                   "le paquet « omnibus ». À vérifier à la date du dossier.",
    },
    "taxonomie": {
        "nom": "Règlement (UE) 2020/852 et règlement délégué (UE) 2021/2139 — "
               "activité 8.1, traitement de données et hébergement",
        "portee": "contraignant",
        "dit": "Conditionne l'éligibilité de l'activité au respect des bonnes "
               "pratiques du Code de conduite européen sur l'efficacité "
               "énergétique des centres de données. C'est le texte par lequel un "
               "référentiel volontaire devient un critère d'accès au financement.",
    },
    "code_conduite": {
        "nom": "Code de conduite européen sur l'efficacité énergétique des "
               "centres de données (Commission européenne, JRC)",
        "portee": "auto_regulation",
        "dit": "Catalogue de bonnes pratiques, classées par niveau d'attente. "
               "Sans force propre — mais appelé par la taxonomie et par "
               "plusieurs dispositifs nationaux, ce qui lui en donne une.",
    },
    "cndcp": {
        "nom": "Climate Neutral Data Centre Pact (2021)",
        "portee": "auto_regulation",
        "dit": "Engagements de la profession européenne : cibles de PUE et de "
               "WUE pour les installations neuves, électricité sans carbone à "
               "100 % à l'horizon 2030, examen systématique de la valorisation "
               "de chaleur fatale.",
        "reserve": "Engagement de place, non opposable. Les valeurs cibles ont "
                   "été révisées depuis la signature : reprenez-les au texte en "
                   "vigueur plutôt qu'à une présentation.",
    },
    "sbti": {
        "nom": "Science Based Targets initiative — Corporate Net-Zero Standard",
        "portee": "methode",
        "dit": "Cadre de cible aligné sur une trajectoire climatique : "
               "réduction profonde de la valeur absolue avant toute "
               "neutralisation du résiduel. C'est la méthode que regardent les "
               "investisseurs, et celle qui refuse les cibles d'intensité seule.",
    },
    "tertiaire": {
        "nom": "Décret n° 2019-771 dit « éco-énergie tertiaire »",
        "portee": "contraignant",
        "dit": "Impose aux bâtiments tertiaires une réduction de consommation "
               "d'énergie finale de 40 % en 2030, 50 % en 2040 et 60 % en 2050 "
               "par rapport à une année de référence, ou l'atteinte d'un niveau "
               "de consommation en valeur absolue.",
        "reserve": "L'assujettissement d'un centre de données et les modalités "
                   "applicables à ses usages spécifiques doivent être vérifiés "
                   "cas par cas : ce n'est pas un bâtiment de bureaux.",
    },
    # ── QUATRE CADRES QUI MANQUAIENT ──────────────────────────────────────
    # Relevé en confrontant la table à la liste des textes que suit réellement
    # une mission de mise en conformité de centre de données. Les trois
    # premiers pèsent sur l'exploitation ou sur le choix des équipements ; le
    # quatrième ne pèse sur rien — il décide seulement si l'on peut concourir.
    "reen": {
        "nom": "Loi n° 2021-1485 du 15 novembre 2021 dite « REEN », réduction "
               "de l'empreinte environnementale du numérique",
        "portee": "contraignant",
        "dit": "Structure la politique française de sobriété numérique et "
               "porte des obligations sur les acteurs du numérique, dont des "
               "engagements attendus des exploitants de centres de données.",
        "reserve": "Le détail des obligations applicables à un exploitant "
                   "donné, et leur articulation avec les dispositifs fiscaux "
                   "associés, restent à instruire sur le texte et ses décrets "
                   "d'application.",
    },
    "ddadue": {
        "nom": "Lois portant diverses dispositions d'adaptation au droit de "
               "l'Union européenne (« DDADUE »)",
        "portee": "contraignant",
        "dit": "Véhicule par lequel les directives européennes — dont la "
               "directive efficacité énergétique — entrent en droit français. "
               "C'est là que se lisent le seuil d'assujettissement retenu en "
               "France et le calendrier réellement opposable.",
        "reserve": "Ces lois se succèdent : citer « la DDADUE » sans millésime "
                   "ne désigne rien. La version applicable à une obligation "
                   "donnée doit être identifiée avant toute conclusion.",
    },
    "fgas": {
        "nom": "Règlement (UE) 2024/573 relatif aux gaz à effet de serre "
               "fluorés",
        "portee": "contraignant",
        "dit": "Encadre l'usage des fluides frigorigènes fluorés et organise "
               "leur retrait progressif. Il pèse directement sur le choix des "
               "groupes froids d'un centre de données, et sur la durée pendant "
               "laquelle un équipement installé aujourd'hui restera "
               "maintenable.",
        "reserve": "Les échéances et les fluides concernés doivent être relevés "
                   "sur le règlement : un calendrier approximatif conduit à "
                   "spécifier une machine dont le fluide sera indisponible "
                   "avant la fin de son amortissement.",
    },
    "commande_publique": {
        "nom": "Éco-conditionnalité de la commande publique",
        "portee": "contraignant",
        "dit": "Les acheteurs publics intègrent des critères environnementaux "
               "dans leurs consultations d'hébergement et d'infrastructure : "
               "part d'énergie renouvelable, performance mesurée, réemploi des "
               "équipements. La preuve est demandée dans l'offre.",
        "reserve": "Ce cadre ne rapporte rien et n'exonère de rien — il décide "
                   "seulement de l'admissibilité à concourir. Les critères sont "
                   "propres à chaque acheteur : il n'existe pas de seuil unique "
                   "à viser.",
    },
}


def _texte(cle):
    t = TEXTES[cle]
    return {"cle": cle, "nom": t["nom"], "dit": t["dit"],
            "portee": t["portee"], "portee_texte": PORTEES[t["portee"]],
            "reserve": t.get("reserve")}


# ═══════════════════════════════════════════════════════════════════════════
#  3. LA HIÉRARCHIE D'ATTÉNUATION, ET LES LEVIERS QUI S'Y RANGENT
#
#  L'ordre est la matière même du module. Un levier ne vaut que rapporté au
#  rang qu'il occupe : substituer de l'électricité décarbonée à une charge
#  qu'on n'a pas cherché à réduire, c'est payer plus cher le même gaspillage.
# ═══════════════════════════════════════════════════════════════════════════

RANGS = [
    {"cle": "eviter", "rang": 1, "nom": "Éviter",
     "principe": "La consommation qui n'a pas lieu. C'est le seul rang dont le "
                 "gain ne se dégrade pas avec le temps, et le seul qui ne "
                 "coûte pas de carbone incorporé.",
     "preuve": "Une baisse de la demande ou de la puissance installée, "
               "constatée à service rendu constant."},
    {"cle": "reduire", "rang": 2, "nom": "Réduire",
     "principe": "La même fonction, avec moins d'énergie ou moins d'eau. C'est "
                 "le terrain de l'ingénierie, et celui où ce moteur calcule.",
     "preuve": "Un indicateur normalisé mesuré sur douze mois, pas une plage "
               "de conception."},
    {"cle": "substituer", "rang": 3, "nom": "Substituer",
     "principe": "La même consommation, moins carbonée — ou valorisée ailleurs. "
                 "Le gain est réel, mais il dépend d'un tiers : réseau, "
                 "fournisseur, preneur de chaleur.",
     "preuve": "Un contrat, et la démonstration que le gain n'est pas déjà "
               "compté par quelqu'un d'autre."},
    {"cle": "compenser", "rang": 4, "nom": "Traiter le résiduel",
     "principe": "Ce qui reste après les trois rangs précédents, et RIEN "
                 "d'autre. Ce rang ne réduit aucune émission de "
                 "l'installation : il finance une réduction ailleurs.",
     "preuve": "L'épuisement documenté des rangs supérieurs — c'est la "
               "condition, pas une formalité — puis la qualité des crédits."},
]

_RANG_ORDRE = {r["cle"]: r["rang"] for r in RANGS}

# `champ` désigne un identifiant de datacenter.CHAMPS : c'est le paramètre sur
# lequel le levier agit, et il rend le levier ÉPROUVABLE. Un levier sans champ
# n'est pas interdit — mais il doit dire pourquoi il n'en a pas.
LEVIERS = [
    # ── Éviter ────────────────────────────────────────────────────────────
    {"cle": "puissance", "rang": "eviter", "nom": "La puissance qu'on n'installe pas",
     "champ": "puissance_it_kw",
     "effet": "Toute l'étude est proportionnelle à la puissance informatique : "
              "l'énergie, l'eau, le carbone d'exploitation et une bonne part du "
              "carbone incorporé. C'est le seul paramètre qui agit sur les "
              "quatre à la fois.",
     "ne_fait_pas": "Il ne dit pas comment rendre le même service avec moins : "
                    "cela se joue dans le logiciel, le dimensionnement des "
                    "modèles et la politique d'usage, hors de ce moteur.",
     "piege": "Dimensionner sur le pic annoncé par l'exploitant. Un plateau "
              "conçu pour une charge qui n'arrive pas fait tourner des "
              "auxiliaires à vide pendant toute la durée de vie de "
              "l'installation."},
    {"cle": "charge", "rang": "eviter", "nom": "La consolidation des charges",
     "champ": "taux_charge",
     "effet": "Sous le point de conception, le PUE se dégrade : les auxiliaires "
              "consomment presque autant à charge partielle qu'à pleine charge. "
              "Consolider remonte le taux de charge sans rien construire.",
     "ne_fait_pas": "Au-delà du point de conception, elle n'améliore plus le "
                    "PUE : ce moteur cesse d'appliquer la pénalité, et le "
                    "RATIO reste plat. Le gain réel de la consolidation est "
                    "ailleurs — dans la puissance qu'on n'installe pas, donc "
                    "dans le levier précédent.",
     "piege": "Consolider les serveurs sans consolider le refroidissement. Une "
              "salle vidée à moitié mais toujours climatisée en entier n'a rien "
              "gagné."},

    # ── Réduire ───────────────────────────────────────────────────────────
    {"cle": "famille", "rang": "reduire", "nom": "La famille de refroidissement",
     "champ": "refroidissement",
     "effet": "C'est l'arbitrage structurant du projet : il fixe simultanément "
              "la plage de PUE, la consommation d'eau sur site et la "
              "possibilité de valoriser la chaleur. Les trois se décident "
              "ensemble ou pas du tout.",
     "ne_fait_pas": "Elle ne se rattrape pas en exploitation : changer de "
                    "famille après la mise en service, c'est un nouveau projet.",
     "piege": "Optimiser l'énergie seule. Une tour évaporative améliore le PUE "
              "et consomme de l'eau ; un aéroréfrigérant sec fait l'inverse. Le "
              "bon arbitrage dépend du stress hydrique du site, pas d'un "
              "classement général."},
    {"cle": "ashrae", "rang": "reduire", "nom": "La température admise en salle",
     "champ": "classe_ashrae",
     "effet": "Élargir la plage admise, c'est moins de froid à produire et "
              "davantage d'heures de refroidissement libre. Le gain est direct "
              "et ne coûte aucun équipement.",
     "ne_fait_pas": "Il ne rallonge pas la vie du matériel — il la raccourcit. "
                    "Ce moteur ne chiffre pas le carbone incorporé du "
                    "renouvellement anticipé, et l'arbitrage se fait donc hors "
                    "de lui.",
     "piege": "Retenir le gain d'énergie sans instruire la contrepartie. C'est "
              "l'arbitrage que Singapour a tranché en imposant 26 °C, et la "
              "littérature technique le décrit comme un échange, pas comme un "
              "gain net."},
    {"cle": "evaporation", "rang": "reduire", "nom": "La part rejetée par évaporation",
     "champ": "part_evaporative",
     "effet": "Elle règle directement le curseur entre l'eau et l'énergie : "
              "moins d'évaporation, moins d'eau, plus d'électricité pour la "
              "même chaleur à évacuer.",
     "ne_fait_pas": "Elle ne supprime pas la chaleur : ce qui n'est pas évaporé "
                    "est rejeté à l'air, avec le surcroît de consommation qui "
                    "va avec.",
     "piege": "Annoncer un WUE en baisse sans publier le PUE de la même année. "
              "Les deux indicateurs se déplacent en sens contraire, et n'en "
              "montrer qu'un est une présentation, pas une mesure."},
    {"cle": "cycles", "rang": "reduire", "nom": "Les cycles de concentration",
     "champ": "cycles_concentration",
     "effet": "Concentrer davantage l'eau de circuit réduit la purge, donc le "
              "prélèvement total, sans toucher au refroidissement lui-même.",
     "ne_fait_pas": "Il ne réduit pas l'évaporation, qui reste la part "
                    "dominante du prélèvement — le gain porte sur la purge "
                    "seule.",
     "piege": "Monter les cycles sans traitement d'eau adapté : entartrage, "
              "corrosion, puis un rendement d'échange dégradé qui coûte "
              "l'énergie qu'on avait économisée en eau."},

    # ── Substituer ────────────────────────────────────────────────────────
    {"cle": "pays", "rang": "substituer", "nom": "Le contenu carbone du réseau",
     "champ": "pays",
     "effet": "L'intensité carbone de l'électricité varie d'un facteur voisin "
              "de cinq d'un pays européen à l'autre. Pour un même kWh consommé, "
              "c'est le premier déterminant de l'empreinte d'exploitation.",
     "ne_fait_pas": "Il ne réduit pas la consommation d'un seul kWh, et il ne "
                    "se décide qu'une fois — au choix du site.",
     "piege": "Choisir un pays sur son mix électrique seul. Le raccordement, "
              "l'eau disponible, les moratoires locaux et les aléas climatiques "
              "à trente ans décident autant, et parfois contre le mix."},
    {"cle": "contrat", "rang": "substituer", "nom": "L'électricité contractualisée",
     "champ": "part_renouvelable",
     "effet": "Contrat d'achat direct ou garanties d'origine : c'est la voie "
              "market-based du scope 2, et celle par laquelle se déclarent la "
              "plupart des engagements d'entreprise.",
     "ne_fait_pas": "Il ne change RIEN aux électrons livrés ni au réseau "
                    "physique. La Scope 2 Guidance impose pour cette raison la "
                    "double déclaration : le chiffre market-based ne remplace "
                    "jamais le chiffre location-based, il s'ajoute à côté.",
     "piege": "Publier le seul market-based et annoncer « zéro émission "
              "électrique ». C'est la première chose que regarde un "
              "vérificateur, et la première que relèvent les autorités de la "
              "publicité."},
    {"cle": "chaleur", "rang": "substituer", "nom": "La chaleur fatale valorisée",
     "champ": "part_chaleur_reutilisee",
     "effet": "La chaleur livrée à un réseau ou à un voisin remplace une "
              "production ailleurs. Le règlement européen de déclaration en fait "
              "un indicateur à publier, et la taxonomie un critère.",
     "ne_fait_pas": "Elle ne réduit pas les émissions du centre : le gain est "
                    "réalisé par CELUI QUI REÇOIT la chaleur et cesse de la "
                    "produire. Se l'attribuer sans convention d'allocation, "
                    "c'est compter deux fois la même tonne.",
     "piege": "Bâtir le projet sur une valorisation sans preneur signé. Un "
              "réseau de chaleur se raccorde à ses conditions de température et "
              "à son calendrier, pas aux nôtres."},
    {"cle": "reseau_contrat", "rang": "substituer",
     "nom": "Le facteur d'émission contractuel",
     "champ": "intensite_reseau_g",
     "effet": "Substituer au facteur national moyen le facteur réel du contrat "
              "ou du gestionnaire de réseau pour l'année de référence.",
     "ne_fait_pas": "Il n'améliore pas la performance : il rend le chiffre "
                    "exact. C'est une substitution de DONNÉE, pas de source "
                    "d'énergie — et sans elle l'inventaire ne passe pas la "
                    "vérification.",
     "piege": "Garder la moyenne annuelle quand la charge est pilotable. "
              "L'écart entre heures creuses et heures de pointe dépasse souvent "
              "un facteur trois, et c'est là que se trouve le gain de pilotage."},

    # ── Traiter le résiduel ───────────────────────────────────────────────
    # AUCUN `champ` ici, et c'est vérifié à l'import : la compensation ne
    # produit aucune grandeur dans ce moteur, parce qu'elle ne réduit aucune
    # émission de l'installation. Lui donner un paramètre la ferait afficher au
    # même rang qu'un gain d'efficacité, et le lecteur additionnerait.
    {"cle": "credits", "rang": "compenser", "nom": "Les crédits carbone",
     "champ": None,
     "sans_champ": "Ce moteur ne calcule rien pour la compensation, et c'est "
                   "délibéré : elle ne fait baisser aucune grandeur physique de "
                   "l'installation. La faire apparaître à côté d'un gain de PUE "
                   "inviterait à les additionner.",
     "effet": "Financer une réduction ou une séquestration ailleurs, pour le "
              "résiduel qui subsiste après les trois rangs précédents.",
     "ne_fait_pas": "Elle ne réduit pas vos émissions brutes, qui restent "
                    "déclarées telles quelles sous ESRS E1. Elle n'autorise "
                    "aucune allégation de neutralité tant que les leviers "
                    "supérieurs ne sont pas documentés comme épuisés.",
     "piege": "Compenser d'abord parce que c'est le levier le plus rapide à "
              "acheter. ISO 14068-1 fait de l'ordre une condition de "
              "l'allégation : compenser avant d'avoir réduit ne rend pas "
              "l'allégation fragile, il la rend irrecevable."},
]

_LEVIER = {x["cle"]: x for x in LEVIERS}


# ═══════════════════════════════════════════════════════════════════════════
#  4. LES ÉTAPES DES DEUX VOIES
#
#  `exige` liste des identifiants de datacenter.CHAMPS qui doivent être
#  RÉELLEMENT renseignés — un champ laissé sur son pré-remplissage compte comme
#  absent, c'est la règle de profil_dc et l'assouplir ici ferait déclarer
#  franchissable une étape qui ne l'est pas.
#
#  `substitutions` liste des postes d'ingenierie_dc.POSTES dont l'ordre de
#  grandeur ne suffit plus. Ils ne sont PAS redéfinis ici : une incertitude
#  recopiée aurait divergé au premier ajustement du référentiel.
# ═══════════════════════════════════════════════════════════════════════════

ETAPES = [
    # ── Voie « compter et déclarer » ──────────────────────────────────────
    {
        "voie": "inventaire", "code": "PERIM", "rang": 1,
        "nom": "Périmètre organisationnel et opérationnel",
        "objet": "Arrêter ce qui entre dans le compte : quelles entités, selon "
                 "quelle approche de consolidation, et quelles catégories "
                 "d'émissions.",
        "decide": "L'approche de consolidation — part du capital, contrôle "
                  "financier ou contrôle opérationnel. Les sites retenus. Les "
                  "catégories du scope 3 jugées significatives.",
        "verrouille": "Le périmètre lui-même. Le modifier ensuite oblige à "
                      "recalculer l'année de référence et toutes les années "
                      "publiées depuis — c'est la reprise la plus coûteuse de "
                      "tout l'exercice.",
        "exige": ["puissance_it_kw", "pays"],
        "substitutions": [],
        "apport_moteur": "complet",
        "textes": ["ghg_corp", "iso14064_1", "ghg_scope3"],
        "preuve": "Une note de périmètre signée, opposable, qui nomme les "
                  "exclusions ET leur motif. Une exclusion non motivée est le "
                  "premier point que relève un vérificateur.",
        "livrable": [
            "Approche de consolidation retenue et justification",
            "Liste des sites et des entités inclus, avec la puissance informatique de chacun",
            "Catégories d'émissions retenues et catégories exclues, avec le motif de chaque exclusion",
            "Correspondance entre les scopes du GHG Protocol et les catégories d'ISO 14064-1",
            "Seuil de significativité appliqué au scope 3",
        ],
    },
    {
        "voie": "inventaire", "code": "REF", "rang": 2,
        "nom": "Année de référence et politique de recalcul",
        "objet": "Fixer l'année contre laquelle toute réduction future sera "
                 "mesurée, et la règle qui dira quand la recalculer.",
        "decide": "L'année de référence. Le seuil de changement structurel "
                  "au-delà duquel elle est recalculée.",
        "verrouille": "La référence de toutes les allégations à venir. Une "
                      "année de référence choisie sur un exercice atypique — "
                      "une année de sous-charge, par exemple — produit des "
                      "réductions faciles la première année et un mur ensuite.",
        "exige": ["puissance_it_kw", "pays", "taux_charge"],
        "substitutions": [],
        "apport_moteur": "complet",
        "textes": ["ghg_corp", "iso14064_1"],
        "preuve": "Le taux de charge RÉEL de l'année retenue. Une référence "
                  "établie sur le taux par défaut d'un formulaire n'est pas une "
                  "référence : elle est fictive, et toute réduction mesurée "
                  "contre elle l'est aussi.",
        "livrable": [
            "Année de référence retenue et motif du choix",
            "Conditions d'exploitation de cette année — puissance appelée, taux de charge réel, indisponibilités",
            "Politique de recalcul : seuil de changement structurel, périmètre du recalcul",
            "Traitement des acquisitions, cessions et externalisations",
        ],
    },
    {
        "voie": "inventaire", "code": "INV", "rang": 3,
        "nom": "Inventaire des émissions",
        "objet": "Quantifier les scopes 1, 2 et 3, avec la double déclaration du "
                 "scope 2 et les facteurs d'émission réels.",
        "decide": "Les données d'activité et les facteurs retenus. La frontière "
                  "entre ce qui est mesuré et ce qui est estimé.",
        "verrouille": "Les chiffres publiés. Ils seront comparés d'une année sur "
                      "l'autre, et une méthode changée en cours de route casse "
                      "la comparaison qu'elle prétendait servir.",
        "exige": ["puissance_it_kw", "pays", "refroidissement", "taux_charge",
                  "part_renouvelable"],
        "substitutions": ["intensite"],
        "apport_moteur": "partiel",
        "textes": ["ghg_corp", "ghg_scope2", "ghg_scope3", "iso14064_1"],
        "preuve": "Le facteur d'émission du fournisseur ou du gestionnaire de "
                  "réseau pour l'année déclarée — pas une moyenne nationale "
                  "d'un référentiel général.",
        "livrable": [
            "Scope 1 — combustion des groupes électrogènes, fuites de fluides frigorigènes",
            "Scope 2 location-based — mix physique du réseau de l'année",
            "Scope 2 market-based — contrats et garanties d'origine, avec leur périmètre",
            "Scope 3 — carbone incorporé des équipements et du bâtiment, catégorie 2",
            "Facteurs d'émission retenus, leur source et leur millésime",
            "Part mesurée et part estimée, poste par poste",
        ],
    },
    {
        "voie": "inventaire", "code": "KPI", "rang": 4,
        "nom": "Indicateurs normalisés du centre de données",
        "objet": "Établir PUE, WUE, ERF et part d'énergie renouvelable selon les "
                 "définitions normatives, avec leurs frontières de mesure et "
                 "leur période.",
        "decide": "Le protocole de mesure : points de comptage, période, "
                  "traitement des périodes d'indisponibilité.",
        "verrouille": "Ce que l'installation pourra déclarer. Un point de "
                      "comptage mal placé se corrige, mais l'année déclarée "
                      "avec, elle, est perdue.",
        "exige": ["puissance_it_kw", "pays", "refroidissement", "taux_charge",
                  "part_evaporative", "cycles_concentration"],
        "substitutions": ["pue", "ewif"],
        "apport_moteur": "cadre_seul",
        "textes": ["iso30134", "en50600", "commande_publique"],
        "preuve": "Douze mois de mesure. Un PUE issu d'une plage de conception "
                  "n'est pas un PUE au sens d'ISO/IEC 30134-2 : c'est une "
                  "hypothèse de dimensionnement, et la déclarer comme un "
                  "indicateur est une faute de méthode avant d'être une faute "
                  "de chiffre.",
        "livrable": [
            "Frontières de mesure retenues pour chaque indicateur, et schéma de comptage",
            "Période de mesure et traitement des indisponibilités",
            "PUE mesuré, et écart à la plage de conception de la famille retenue",
            "WUE sur site et WUE source, avec le facteur eau amont utilisé",
            "ERF et convention d'allocation de la chaleur exportée",
            "Facteur d'énergie renouvelable, et méthode de son établissement",
        ],
    },
    {
        "voie": "inventaire", "code": "DECL", "rang": 5,
        "nom": "Déclaration réglementaire européenne",
        "objet": "Produire les informations exigées des centres de données "
                 "au-delà du seuil de puissance informatique installée.",
        "decide": "Rien : à ce stade tout est décidé. L'étape constate et "
                  "transmet.",
        "verrouille": "La publication. Une partie des informations transmises "
                      "devient accessible, et sert de base de comparaison "
                      "publique entre installations.",
        "exige": ["puissance_it_kw", "pays", "refroidissement", "taux_charge",
                  "part_evaporative", "part_renouvelable",
                  "part_chaleur_reutilisee"],
        "substitutions": ["pue", "ewif", "intensite"],
        "apport_moteur": "cadre_seul",
        "textes": ["eed_art12", "reg2024_1364", "taxonomie", "ddadue"],
        "preuve": "Les mêmes indicateurs que l'étape précédente, mais issus de "
                  "la mesure et non du calcul. Le moteur ne fournit ici que la "
                  "structure de la déclaration.",
        "livrable": [
            "Vérification du seuil d'assujettissement — puissance informatique installée",
            "Consommation d'électricité de la période",
            "PUE, WUE, ERF et part d'énergie renouvelable mesurés",
            "Chaleur valorisée et destination",
            "Éléments de conformité aux bonnes pratiques du Code de conduite européen",
        ],
    },
    {
        "voie": "inventaire", "code": "VERIF", "rang": 6,
        "nom": "Vérification et publication",
        "objet": "Faire éprouver l'inventaire par un tiers, puis publier ce qui "
                 "doit l'être — émissions brutes, intensité, plan de transition.",
        "decide": "Rien de technique. Le niveau d'assurance demandé, et lui "
                  "seul.",
        "verrouille": "Tout. Ce qui est publié et vérifié ne se reprend qu'en "
                      "publiant une correction.",
        "exige": ["puissance_it_kw", "pays", "refroidissement", "taux_charge",
                  "part_evaporative", "part_renouvelable",
                  "part_chaleur_reutilisee", "intensite_reseau_g"],
        "substitutions": ["pue", "ewif", "intensite", "incorpore"],
        "apport_moteur": "cadre_seul",
        "textes": ["iso14064_3", "csrd_e1"],
        "preuve": "La piste d'audit : chaque chiffre publié doit se remonter "
                  "jusqu'à une donnée d'activité et un facteur, tous deux "
                  "datés et sourcés.",
        "livrable": [
            "Dossier de preuve — données d'activité, facteurs, calculs, journal des corrections",
            "Réponses aux constats du vérificateur",
            "Émissions brutes des scopes 1, 2 et 3, publiées sans déduction de compensations",
            "Intensité rapportée à l'unité d'activité retenue",
            "Plan de transition et cohérence avec la trajectoire annoncée",
        ],
    },

    # ── Voie « réduire » ──────────────────────────────────────────────────
    {
        "voie": "trajectoire", "code": "DIAG", "rang": 1,
        "nom": "Diagnostic et postes dominants",
        "objet": "Établir où se trouve la masse, avant toute idée de solution.",
        "decide": "L'ordre de grandeur de chaque poste, et donc là où il vaut "
                  "la peine de travailler.",
        "verrouille": "Rien — et c'est la seule étape dont c'est vrai. C'est "
                      "aussi pourquoi elle est la moins chère à faire "
                      "sérieusement.",
        "exige": ["puissance_it_kw", "pays", "refroidissement"],
        "substitutions": [],
        "apport_moteur": "complet",
        "textes": ["ghg_corp"],
        "preuve": "Un classement des postes par masse, avec l'incertitude de "
                  "chacun. Un poste dominant tenu par une incertitude de ±50 % "
                  "n'est pas un poste dominant établi.",
        "livrable": [
            "Bilan énergie, eau et carbone de l'installation dans sa configuration actuelle",
            "Classement des postes par masse, avec l'incertitude de chacun",
            "Comparaison des familles de refroidissement à installation constante",
            "Sensibilité au pays et au taux de charge",
            "Postes dominants dont l'incertitude interdit de conclure à ce stade",
        ],
    },
    {
        "voie": "trajectoire", "code": "CIBLE", "rang": 2,
        "nom": "Cible et trajectoire",
        "objet": "Poser une cible datée, sur un périmètre nommé, et la "
                 "trajectoire qui y conduit.",
        "decide": "La valeur visée, sa date, son périmètre, et si elle porte "
                  "sur la valeur absolue ou sur une intensité.",
        "verrouille": "L'engagement public. Une cible d'intensité annoncée "
                      "pendant que la valeur absolue croît est la façon la plus "
                      "courante de tenir sa promesse en manquant son objet.",
        "exige": ["puissance_it_kw", "pays", "refroidissement", "taux_charge"],
        "substitutions": ["intensite"],
        "apport_moteur": "partiel",
        "textes": ["sbti", "csrd_e1", "tertiaire", "reen"],
        "preuve": "Une cible en valeur ABSOLUE, ou une cible d'intensité "
                  "accompagnée de la trajectoire absolue qu'elle implique. La "
                  "seconde sans la première ne dit rien.",
        "livrable": [
            "Cible retenue : grandeur, valeur, date, périmètre",
            "Trajectoire annuelle jusqu'à la cible, en valeur absolue",
            "Hypothèses de croissance de la charge informatique sur la période",
            "Point de passage réglementaire applicable au bâtiment, le cas échéant",
            "Ce que la cible ne couvre pas, et pourquoi",
        ],
    },
    {
        "voie": "trajectoire", "code": "EVIT", "rang": 3,
        "leviers": ["puissance", "charge"],
        "nom": "Éviter — la demande et la puissance installée",
        "objet": "Épuiser le premier rang de la hiérarchie : la consommation "
                 "qui n'a pas lieu.",
        "decide": "La puissance réellement installée et le taux de charge visé.",
        "verrouille": "Le dimensionnement. Une salle surdimensionnée porte son "
                      "surcoût énergétique et son carbone incorporé pendant "
                      "toute sa vie, sans recours.",
        "exige": ["puissance_it_kw", "taux_charge"],
        "substitutions": [],
        "apport_moteur": "complet",
        "textes": ["code_conduite"],
        "preuve": "Une baisse constatée à service rendu constant. Sans la "
                  "seconde moitié de la phrase, une baisse de consommation peut "
                  "n'être qu'une baisse d'activité.",
        "livrable": [
            "Puissance informatique nécessaire, établie sur la charge utile et non sur le pic annoncé",
            "Effet du taux de charge sur le PUE et sur l'énergie annuelle",
            "Gains de consolidation chiffrés",
            "Ce qui relève du logiciel et de la politique d'usage, hors périmètre de ce moteur",
        ],
    },
    {
        "voie": "trajectoire", "code": "REDUI", "rang": 4,
        "leviers": ["famille", "ashrae", "evaporation", "cycles"],
        "nom": "Réduire — l'efficacité de l'installation",
        "objet": "Obtenir la même fonction avec moins d'énergie et moins d'eau, "
                 "en arbitrant explicitement entre les deux.",
        "decide": "La famille de refroidissement, la classe de température "
                  "admise, la part rejetée par évaporation, les cycles de "
                  "concentration.",
        "verrouille": "Les équipements. Après commande, c'est leur courbe qui "
                      "fait foi, et non la plage de conception de la famille.",
        "exige": ["puissance_it_kw", "pays", "refroidissement", "taux_charge",
                  "classe_ashrae", "part_evaporative", "cycles_concentration"],
        "substitutions": ["pue"],
        "apport_moteur": "partiel",
        "textes": ["iso30134", "code_conduite", "cndcp", "iso50001", "fgas"],
        "preuve": "L'arbitrage eau / énergie rendu explicite : les deux "
                  "indicateurs se déplacent en sens contraire, et n'en publier "
                  "qu'un revient à choisir sa mesure après avoir vu le résultat.",
        "livrable": [
            "Familles de refroidissement comparées sur l'énergie ET sur l'eau",
            "Arbitrage retenu, au regard du stress hydrique du site",
            "Effet de la classe de température admise, et contrepartie sur la durée de vie du matériel",
            "Traitement d'eau et cycles de concentration retenus",
            "Écart entre la plage de conception et la performance à engager",
        ],
    },
    {
        "voie": "trajectoire", "code": "SUBST", "rang": 5,
        "leviers": ["pays", "contrat", "chaleur", "reseau_contrat"],
        "nom": "Substituer — l'énergie et la chaleur",
        "objet": "Décarboner ce qui reste à consommer, et valoriser ce qui est "
                 "rejeté.",
        "decide": "Le contrat d'électricité et sa nature. Le preneur de chaleur "
                  "et la convention d'allocation.",
        "verrouille": "Des engagements contractuels longs — un contrat d'achat "
                      "direct ou un raccordement à un réseau de chaleur se "
                      "négocient sur une décennie.",
        "exige": ["puissance_it_kw", "pays", "refroidissement", "taux_charge",
                  "part_renouvelable", "part_chaleur_reutilisee",
                  "intensite_reseau_g"],
        "substitutions": ["intensite"],
        "apport_moteur": "partiel",
        "textes": ["ghg_scope2", "reg2024_1364", "taxonomie", "cndcp"],
        "preuve": "Pour l'électricité : les deux déclarations du scope 2, "
                  "côte à côte. Pour la chaleur : la convention qui dit qui "
                  "compte la tonne évitée, sans quoi elle est comptée deux fois.",
        "livrable": [
            "Nature du contrat d'électricité et périmètre exact de sa couverture",
            "Scope 2 selon les deux méthodes, présentées ensemble",
            "Chaleur valorisée : preneur, température de livraison, saisonnalité",
            "Convention d'allocation du gain de la chaleur exportée",
            "Effet du pilotage de charge sur l'intensité horaire, si la charge est pilotable",
        ],
    },
    {
        "voie": "trajectoire", "code": "RESID", "rang": 6,
        "leviers": ["credits"],
        "nom": "Résiduel et allégations",
        "objet": "Établir ce qui reste, ce qu'on en fait, et ce qu'on a le droit "
                 "d'en dire.",
        "decide": "Le traitement du résiduel, et la formulation publique.",
        "verrouille": "La parole donnée. Une allégation de neutralité "
                      "insuffisamment étayée engage au-delà du rapport : elle "
                      "relève du droit de la publicité et des pratiques "
                      "commerciales.",
        "exige": ["puissance_it_kw", "pays", "refroidissement", "taux_charge",
                  "part_evaporative", "part_renouvelable",
                  "part_chaleur_reutilisee", "intensite_reseau_g"],
        "substitutions": ["intensite", "incorpore", "pue"],
        "apport_moteur": "cadre_seul",
        "textes": ["iso14068", "csrd_e1", "sbti"],
        "preuve": "L'épuisement DOCUMENTÉ des trois rangs précédents. C'est une "
                  "condition de recevabilité de l'allégation, pas une bonne "
                  "pratique : sans elle, la compensation ne rend pas "
                  "l'allégation fragile, elle la rend irrecevable.",
        "livrable": [
            "Émissions résiduelles après épuisement des leviers, poste par poste",
            "Dossier d'épuisement des rangs éviter, réduire et substituer",
            "Traitement du résiduel retenu, et critères de qualité des crédits le cas échéant",
            "Formulation publique proposée, et ce qu'elle ne dit délibérément pas",
            "Émissions brutes maintenues à l'affichage, sans déduction",
        ],
    },
]

_PAR_CODE = {e["code"]: e for e in ETAPES}


# Les points de rendez-vous entre les deux voies. Ce ne sont pas des
# équivalences : ce sont des dépendances. La voie de gauche produit ce dont
# celle de droite a besoin, et l'ignorer fait travailler en parallèle deux
# équipes dont l'une attend l'autre sans le savoir.
RENDEZ_VOUS = [
    {"inventaire": "PERIM", "trajectoire": "DIAG",
     "lien": "Le diagnostic ne vaut que sur le périmètre arrêté. Diagnostiquer "
             "d'abord, c'est risquer d'avoir travaillé sur un ensemble qui ne "
             "sera pas celui du compte."},
    {"inventaire": "REF", "trajectoire": "CIBLE",
     "lien": "Une cible se pose CONTRE une année de référence. Annoncer « -40 % » "
             "sans avoir arrêté l'année, c'est annoncer un pourcentage sans "
             "dénominateur."},
    {"inventaire": "INV", "trajectoire": "EVIT",
     "lien": "L'inventaire dit où est la masse ; les leviers d'évitement s'y "
             "appliquent en premier. L'ordre inverse fait optimiser un poste "
             "mineur avec application."},
    {"inventaire": "KPI", "trajectoire": "REDUI",
     "lien": "Les gains d'efficacité se prouvent par les indicateurs "
             "normalisés, et par eux seuls. Sans protocole de mesure arrêté, "
             "une amélioration de PUE n'est pas démontrable."},
    {"inventaire": "DECL", "trajectoire": "SUBST",
     "lien": "La déclaration européenne publie la part renouvelable et la "
             "chaleur valorisée : ce sont exactement les deux leviers de "
             "substitution. Ce qui est annoncé ici sera lu là."},
    {"inventaire": "VERIF", "trajectoire": "RESID",
     "lien": "L'allégation sur le résiduel ne tient que si l'inventaire qui la "
             "porte est vérifié. C'est le point de jonction final des deux "
             "voies, et le seul qui soit opposable."},
]


# CE QUE LE FORMULAIRE SUFFIT À SATISFAIRE.
#
# Un poste de substitution dit « allez chercher une donnée réelle ». Pour deux
# d'entre eux, le formulaire est précisément l'endroit où on la saisit : le
# moteur cesse alors d'employer sa valeur générique et emploie celle du
# dossier. Les compter malgré tout comme non faits rendait le parcours
# INFRANCHISSABLE quoi qu'on saisisse — et une frise où rien ne peut passer au
# vert n'apprend rien à personne. C'est la contrepartie exacte de la règle
# « un champ par défaut n'est pas un champ renseigné » : une valeur réellement
# choisie doit compter, sans quoi la sévérité cesse d'être de la rigueur.
#
# Les autres postes — l'eau amont, le carbone incorporé — n'ont aucun champ :
# leur donnée réelle vient d'un fournisseur ou d'une FDES, hors de ce
# formulaire. Ils restent ouverts, et c'est exact.
SATISFAIT_PAR = {
    "intensite": "intensite_reseau_g",
    "pue": "pue_cible",
}


# Quelles grandeurs du moteur chaque poste de substitution engage. Sert à dire
# « cette grandeur n'est plus recevable ICI, et voici pourquoi » plutôt que de
# laisser un chiffre juste à côté d'un avertissement général.
_ENGAGE = {
    # Le PUE vient de la plage de conception de la famille : c'est ce poste-là
    # qui cesse de suffire, et lui seul.
    "pue": ("pue",),
    # L'énergie annuelle est le produit de la puissance par le PUE. Elle ne
    # dépend PAS du contenu carbone du réseau — l'y rattacher, comme je l'avais
    # fait, faisait déclarer « à remplacer » une grandeur que rien ne bloquait,
    # et taisait le poste qui la bloquait vraiment.
    "energie": ("pue",),
    "eau_site": ("evaporation",),
    "eau_source": ("ewif",),
    "carbone": ("intensite", "incorpore"),
    # La chaleur valorisée est une part saisie, pas une grandeur estimée : rien
    # ne la « remplace », elle se mesure au compteur du preneur.
    "chaleur": (),
}


# ═══════════════════════════════════════════════════════════════════════════
#  5. CONTRÔLES D'INTÉGRITÉ — au chargement, pas à l'exécution
# ═══════════════════════════════════════════════════════════════════════════

def _verifier():
    fautes = []
    champs = {c["id"] for c in D.CHAMPS}

    # L'ORDRE DE POIDS COUVRE EXACTEMENT LE VOCABULAIRE. Une portee ajoutee
    # sans etre classee sortirait en fin de liste par hasard, ou n'en sortirait
    # pas du tout — et une interface qui s'ouvre sur la premiere entree
    # presenterait alors autre chose que le texte qui oblige.
    if sorted(PORTEES_ORDRE) != sorted(PORTEES):
        fautes.append("l'ordre de poids des portees ne couvre pas le "
                      "vocabulaire : %s vs %s"
                      % (sorted(PORTEES_ORDRE), sorted(PORTEES)))
    if PORTEES_ORDRE and PORTEES_ORDRE[0] != "contraignant":
        fautes.append("l'ordre de poids ne commence pas par ce qui oblige")

    # LA règle du module : la compensation ne porte aucun paramètre du moteur.
    for lv in LEVIERS:
        if lv["rang"] not in _RANG_ORDRE:
            fautes.append("levier %s : rang inconnu %s" % (lv["cle"], lv["rang"]))
        if lv["rang"] == "compenser" and lv.get("champ"):
            fautes.append(
                "levier %s : un levier de compensation ne peut porter un "
                "paramètre du moteur (%s) — il ne réduit rien qui se calcule "
                "ici, et l'afficher au même rang qu'un gain d'efficacité "
                "inviterait à les additionner." % (lv["cle"], lv["champ"]))
        if lv.get("champ") and lv["champ"] not in champs:
            fautes.append("levier %s : champ inconnu du moteur %s"
                          % (lv["cle"], lv["champ"]))
        # Un levier sans champ doit DIRE pourquoi. Sans cela, l'absence se lit
        # comme un oubli, et un oubli se « corrige » en inventant un champ.
        if not lv.get("champ") and not lv.get("sans_champ"):
            fautes.append("levier %s : sans paramètre et sans explication"
                          % lv["cle"])
        for k in ("effet", "ne_fait_pas", "piege"):
            if not (lv.get(k) or "").strip():
                fautes.append("levier %s : %s manquant" % (lv["cle"], k))

    cles = [lv["cle"] for lv in LEVIERS]
    if len(set(cles)) != len(cles):
        fautes.append("clé de levier dupliquée")

    # Les quatre rangs doivent tous être servis : un rang vide donnerait une
    # hiérarchie amputée sans que rien ne le signale.
    servis = {lv["rang"] for lv in LEVIERS}
    for r in RANGS:
        if r["cle"] not in servis:
            fautes.append("rang %s : aucun levier" % r["cle"])

    for e in ETAPES:
        if e["voie"] not in VOIES:
            fautes.append("étape %s : voie inconnue %s" % (e["code"], e["voie"]))
        for cid in e["exige"]:
            if cid not in champs:
                fautes.append("étape %s : champ inconnu du moteur %s"
                              % (e["code"], cid))
        for s in e["substitutions"]:
            if s not in G.POSTES:
                fautes.append("étape %s : poste de substitution inconnu %s"
                              % (e["code"], s))
        for t in e["textes"]:
            if t not in TEXTES:
                fautes.append("étape %s : texte inconnu %s" % (e["code"], t))
        if e["apport_moteur"] not in G.APPORT:
            fautes.append("étape %s : apport inconnu %s"
                          % (e["code"], e["apport_moteur"]))

    codes = [e["code"] for e in ETAPES]
    if len(set(codes)) != len(codes):
        fautes.append("code d'étape dupliqué")

    # AUCUNE ÉTAPE FANTÔME. Une étape qui n'ajoute ni entrée, ni substitution,
    # ni texte applicable par rapport à celles qui la précèdent dans sa voie ne
    # fait rien avancer : elle allonge la frise et donne le sentiment d'un
    # travail là où il n'y en a pas.
    for v in VOIES:
        suite = sorted([e for e in ETAPES if e["voie"] == v],
                       key=lambda x: x["rang"])
        vus_e, vus_s, vus_t = set(), set(), set()
        for e in suite:
            neuf = ((set(e["exige"]) - vus_e) | (set(e["substitutions"]) - vus_s)
                    | (set(e["textes"]) - vus_t))
            if not neuf:
                fautes.append("étape %s : n'ajoute rien à ce que %s exigeait déjà"
                              % (e["code"], v))
            vus_e |= set(e["exige"])
            vus_s |= set(e["substitutions"])
            vus_t |= set(e["textes"])

    # LA HIÉRARCHIE D'ATTÉNUATION EST LA COLONNE DE LA VOIE « RÉDUIRE ».
    # Chaque levier appartient à exactement une étape, et les rangs se suivent
    # dans l'ordre le long de la voie. Un levier de substitution attaché à
    # l'étape « éviter » ferait lire la page à l'envers — et c'est précisément
    # l'inversion que l'on reproche aux plans de décarbonation.
    declares = []
    for e in ETAPES:
        for cle in e.get("leviers", []):
            if cle not in _LEVIER:
                fautes.append("étape %s : levier inconnu %s" % (e["code"], cle))
                continue
            declares.append(cle)
    if len(set(declares)) != len(declares):
        fautes.append("levier rattaché à plusieurs étapes")
    orphelins_lv = [lv["cle"] for lv in LEVIERS if lv["cle"] not in set(declares)]
    if orphelins_lv:
        fautes.append("levier rattaché à aucune étape : %s"
                      % ", ".join(orphelins_lv))

    dernier = 0
    for e in sorted([x for x in ETAPES if x["voie"] == "trajectoire"],
                    key=lambda x: x["rang"]):
        rangs = [_RANG_ORDRE[_LEVIER[c]["rang"]] for c in e.get("leviers", [])
                 if c in _LEVIER]
        if not rangs:
            continue
        if len(set(rangs)) > 1:
            fautes.append("étape %s : mélange plusieurs rangs de la hiérarchie"
                          % e["code"])
        if min(rangs) < dernier:
            fautes.append("étape %s : revient à un rang déjà dépassé (%d après %d)"
                          % (e["code"], min(rangs), dernier))
        dernier = max(rangs)

    # Un levier qui porte un paramètre du moteur doit voir ce paramètre exigé
    # quelque part dans la voie « réduire » : sinon la page conseille d'agir
    # sur une grandeur que le parcours ne demande jamais de renseigner.
    exiges_traj = set()
    for e in ETAPES:
        if e["voie"] == "trajectoire":
            exiges_traj |= set(e["exige"])
    for lv in LEVIERS:
        if lv.get("champ") and lv["champ"] not in exiges_traj:
            fautes.append("levier %s : agit sur %s, qu'aucune étape de la voie "
                          "« réduire » n'exige" % (lv["cle"], lv["champ"]))

    for r in RENDEZ_VOUS:
        for v, c in r.items():
            if v == "lien":
                continue
            if c not in _PAR_CODE or _PAR_CODE[c]["voie"] != v:
                fautes.append("rendez-vous : %s n'est pas une étape de %s" % (c, v))

    # Chaque texte cité doit servir. Un texte listé et jamais appelé gonfle la
    # bibliographie sans rien apporter — le même défaut que dans etat_art.
    appeles = {t for e in ETAPES for t in e["textes"]}
    orphelins = [t for t in TEXTES if t not in appeles]
    if orphelins:
        fautes.append("texte cité par aucune étape : %s" % ", ".join(orphelins))

    for t, v in TEXTES.items():
        if v["portee"] not in PORTEES:
            fautes.append("texte %s : portée inconnue %s" % (t, v["portee"]))

    # Les postes qui BLOQUENT une grandeur doivent exister au registre. Une clé
    # inventée ici ne lève rien : elle ne correspond simplement à aucune
    # substitution, la grandeur reste « recevable » quoi qu'il arrive, et
    # l'avertissement qu'on croyait avoir posé n'est jamais affiché.
    for g, postes in _ENGAGE.items():
        for cle in postes:
            if cle not in G.POSTES:
                fautes.append("grandeur %s : poste bloquant inconnu %s" % (g, cle))

    # Une substitution declaree satisfaite par un champ qui n'existe pas
    # resterait ouverte pour toujours, sans erreur ; l'inverse — un poste
    # inconnu — laisserait croire qu'on a prevu une sortie qui n'existe pas.
    for cle, cid in SATISFAIT_PAR.items():
        if cle not in G.POSTES:
            fautes.append("satisfaction : poste inconnu %s" % cle)
        if cid not in champs:
            fautes.append("satisfaction de %s : champ inconnu du moteur %s"
                          % (cle, cid))

    return fautes


_FAUTES = _verifier()
if _FAUTES:
    raise RuntimeError("decarbonation — référentiel incohérent : "
                       + " ; ".join(_FAUTES))


# ═══════════════════════════════════════════════════════════════════════════
#  6. L'APTITUDE D'UNE ÉTAPE
# ═══════════════════════════════════════════════════════════════════════════

def exigences(code):
    """Ce que l'étape demande, en propre et par héritage.

    Une étape hérite de tout ce que les précédentes de sa voie exigeaient :
    l'inventaire ne se recommence pas à chaque étape, il s'accumule. Distinguer
    les deux permet de dire au lecteur si le point ouvert est de sa
    responsabilité présente ou une dette laissée derrière.
    """
    e = _PAR_CODE.get(code)
    if not e:
        return {"connu": False}
    avant = [x for x in ETAPES
             if x["voie"] == e["voie"] and x["rang"] < e["rang"]]
    herit_e, herit_s = set(), set()
    for x in avant:
        herit_e |= set(x["exige"])
        herit_s |= set(x["substitutions"])
    return {
        "connu": True,
        "entrees": sorted(set(e["exige"]) | herit_e),
        "substitutions": sorted(set(e["substitutions"]) | herit_s),
        "en_propre": {"entrees": sorted(set(e["exige"]) - herit_e),
                      "substitutions": sorted(set(e["substitutions"]) - herit_s)},
    }


def _verdict(manques, subs):
    if not manques and not subs:
        return ("Rien ne manque du côté du moteur pour cette étape. Ce qui reste "
                "à produire relève de la mesure, du contrat ou de la "
                "gouvernance — pas du calcul.")
    bouts = []
    if manques:
        bouts.append("%d entrée%s à renseigner (%s)"
                     % (len(manques), "s" if len(manques) > 1 else "",
                        ", ".join(m["label"] for m in manques)))
    if subs:
        bouts.append("%d facteur%s dont l'ordre de grandeur ne suffit plus à ce "
                     "stade (%s)"
                     % (len(subs), "s" if len(subs) > 1 else "",
                        ", ".join(s["nom"] for s in subs)))
    return "Étape non franchissable en l'état : " + " ; ".join(bouts) + "."


def aptitude(profil, code):
    """Ce qui manque pour franchir l'étape, sans complaisance.

    Même règle que dans le cadre de phases : un champ laissé sur sa valeur par
    défaut compte comme non renseigné. Une année de référence établie sur le
    taux de charge par défaut d'un formulaire n'est pas une référence, et toute
    réduction mesurée contre elle serait fictive.
    """
    e = _PAR_CODE.get(code)
    if not e:
        return {"connu": False, "motif": "Étape inconnue : %s" % code}

    profil = dict(profil or {})
    champs = {c["id"]: c for c in D.CHAMPS}
    ex = exigences(code)
    propres = set(ex["en_propre"]["entrees"])

    manques = []
    for cid in ex["entrees"]:
        c = champs.get(cid)
        if not c:
            continue
        etat = P._etat(profil, c)
        if etat != P.SAISI:
            manques.append({
                "id": cid, "label": c["label"], "unite": c.get("unite", ""),
                "etat": etat,
                "origine": "propre" if cid in propres else "heritee",
                "pourquoi": ("laissé sur la valeur par défaut du formulaire"
                             if etat == P.DEFAUT else "non précisé"),
            })

    subs, faites = [], []
    for cle in ex["substitutions"]:
        po = G.POSTES.get(cle) or {}
        cid = SATISFAIT_PAR.get(cle)
        # « Faite » veut dire : le champ porte une valeur RÉELLEMENT choisie,
        # au sens de profil_dc. Un pré-remplissage ne satisfait rien.
        est_faite = bool(cid) and cid in champs and P._etat(profil, champs[cid]) == P.SAISI
        ligne = {
            "cle": cle,
            "nom": po.get("nom", cle),
            "nature": po.get("nature", ""),
            "incertitude": po.get("incertitude", ""),
            "incertitude_absente": bool(po.get("incertitude_absente")),
            "remplacer_par": po.get("remplacer_par") or "",
            "devient_insuffisant": po.get("devient_insuffisant") or "",
            "satisfait_par": cid,
        }
        (faites if est_faite else subs).append(ligne)

    return {
        "connu": True,
        "code": e["code"], "nom": e["nom"], "voie": e["voie"],
        "apport_moteur": e["apport_moteur"],
        "apport_texte": G.APPORT[e["apport_moteur"]],
        "entrees_manquantes": manques,
        "substitutions_a_faire": subs,
        # Rendues aussi : ce qui a été remplacé est une information du dossier,
        # pas un détail d'affichage. Une note qui tait la substitution faite
        # laisse le relecteur croire que le chiffre vient encore du générique.
        "substitutions_faites": faites,
        "franchissable": not manques and not subs,
        "verdict": _verdict(manques, subs),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  7. LE PARCOURS D'UNE VOIE
# ═══════════════════════════════════════════════════════════════════════════

def parcours(profil, voie):
    """Toute la voie d'un coup : où l'on passe, où l'on bute.

    Le premier point de blocage commande le travail à engager ; les étapes
    suivantes servent à voir venir, pas à travailler en parallèle.
    """
    if voie not in VOIES:
        return {"connu": False, "motif": "Voie inconnue : %s" % voie}
    et = sorted([e for e in ETAPES if e["voie"] == voie], key=lambda x: x["rang"])
    etapes, premier_blocage = [], None
    for e in et:
        a = aptitude(profil, e["code"])
        etapes.append({
            "code": e["code"], "nom": e["nom"], "rang": e["rang"],
            "objet": e["objet"], "decide": e["decide"],
            "verrouille": e["verrouille"], "preuve": e["preuve"],
            "livrable": e["livrable"],
            "apport_moteur": e["apport_moteur"],
            "textes": [_texte(t) for t in e["textes"]],
            "franchissable": a["franchissable"],
            "n_manques": len(a["entrees_manquantes"]),
            "n_substitutions": len(a["substitutions_a_faire"]),
            "aptitude": a,
        })
        if premier_blocage is None and not a["franchissable"]:
            premier_blocage = e["code"]
    return {
        "connu": True,
        "voie": voie,
        "cadre": VOIES[voie],
        "etapes": etapes,
        "premier_blocage": premier_blocage,
        "n_franchissables": sum(1 for x in etapes if x["franchissable"]),
        "n_total": len(etapes),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  8. LE DOSSIER D'UNE ÉTAPE
# ═══════════════════════════════════════════════════════════════════════════

def dossier(profil, code, inputs=None):
    """Le plan de l'étude pour cette étape, avec les valeurs du moteur là où
    elles sont recevables — et la mention explicite de ce qui reste à produire.

    C'est le point du module : un plan de document qui porte, section par
    section, ce qui est déjà calculé et ce qui doit venir d'ailleurs. Un
    sommaire sans cette distinction se remplit de chiffres provisoires que
    personne ne remplace.
    """
    e = _PAR_CODE.get(code)
    if not e:
        return {"connu": False, "motif": "Étape inconnue : %s" % code}
    profil = dict(profil or {})
    if not profil.get("puissance_it_kw"):
        return {"connu": True, "disponible": False,
                "motif": "La puissance informatique installée est nécessaire."}

    a = aptitude(profil, code)
    etude = D.etude(profil)

    grandeurs = []
    for cle, sec, champ in [("pue", "energie", "pue"),
                            ("energie", "energie", "energie_totale_MWh"),
                            ("eau_site", "eau", "wue_site"),
                            ("eau_source", "eau", "wue_source"),
                            ("carbone", "carbone", "empreinte_totale_t"),
                            ("chaleur", "chaleur", "erf")]:
        v = (etude.get(sec) or {}).get(champ)
        if not v:
            continue
        touche = _ENGAGE.get(cle, ())
        bloquants = [s for s in a["substitutions_a_faire"] if s["cle"] in touche]
        grandeurs.append({
            "cle": cle,
            "nom": v["nom"], "valeur": v["valeur"], "unite": v["unite"],
            "incertitude": v.get("incertitude", ""),
            "statut": "a_remplacer" if bloquants else "recevable",
            "postes_bloquants": [s["nom"] for s in bloquants],
        })

    # Les leviers que CETTE étape met en jeu, DÉCLARÉS et non déduits. Les
    # déduire des paramètres exigés remontait les leviers d'évitement dans
    # l'étape d'efficacité — qui exige les mêmes champs pour d'autres raisons —
    # et faisait lire la hiérarchie à l'envers.
    engages = [_levier_public(_LEVIER[c]) for c in e.get("leviers", [])]

    return {
        "connu": True, "disponible": True,
        "code": e["code"], "nom": e["nom"],
        "voie": e["voie"], "voie_nom": VOIES[e["voie"]]["nom"],
        "objet": e["objet"], "decide": e["decide"],
        "verrouille": e["verrouille"], "preuve": e["preuve"],
        "sections": e["livrable"],
        "textes": [_texte(t) for t in e["textes"]],
        "apport_moteur": e["apport_moteur"],
        "apport_texte": G.APPORT[e["apport_moteur"]],
        "grandeurs": grandeurs,
        "leviers_engages": engages,
        "aptitude": a,
        "rendez_vous": [r for r in RENDEZ_VOUS if r.get(e["voie"]) == e["code"]],
        "version_moteur": D.VERSION,
    }


def _levier_public(lv):
    r = next(x for x in RANGS if x["cle"] == lv["rang"])
    champ = None
    if lv.get("champ"):
        c = next((x for x in D.CHAMPS if x["id"] == lv["champ"]), None)
        if c:
            champ = {"id": c["id"], "label": c["label"], "unite": c.get("unite", "")}
    return {
        "cle": lv["cle"], "nom": lv["nom"],
        "rang": lv["rang"], "rang_nom": r["nom"], "rang_ordre": r["rang"],
        "champ": champ, "sans_champ": lv.get("sans_champ"),
        "effet": lv["effet"], "ne_fait_pas": lv["ne_fait_pas"],
        "piege": lv["piege"],
    }


def hierarchie():
    """Les quatre rangs et leurs leviers, dans l'ordre — jamais autrement.

    L'ordre EST l'information. Une page qui trierait les leviers par gain
    attendu ferait remonter la compensation, qui est le plus rapide à acheter
    et le seul qui ne réduise rien.
    """
    out = []
    for r in sorted(RANGS, key=lambda x: x["rang"]):
        out.append({
            "cle": r["cle"], "nom": r["nom"], "rang": r["rang"],
            "principe": r["principe"], "preuve": r["preuve"],
            "leviers": [_levier_public(lv) for lv in LEVIERS
                        if lv["rang"] == r["cle"]],
        })
    return out


def referentiel():
    """Le cadre complet, sans profil : les voies, les rangs, les textes."""
    return {
        "version": VERSION,
        "version_moteur": D.VERSION,
        "voies": VOIES,
        "rangs": RANGS,
        "hierarchie": hierarchie(),
        "textes": [_texte(t) for t in sorted(
            TEXTES, key=lambda k: (PORTEES_ORDRE.index(TEXTES[k]["portee"]),
                                   TEXTES[k]["nom"]))],
        "portees": PORTEES,
        # SERVI COMME UNE LISTE, et c'est le seul moyen de tenir l'ordre : la
        # serialisation JSON trie les cles d'un dictionnaire, et le vocabulaire
        # arrivait a la page par ordre alphabetique — « engagement de place »
        # avant « texte contraignant ».
        "portees_ordre": [{"cle": k, "texte": PORTEES[k]} for k in PORTEES_ORDRE],
        "rendez_vous": RENDEZ_VOUS,
        "etapes": [{"voie": e["voie"], "code": e["code"], "rang": e["rang"],
                    "nom": e["nom"], "objet": e["objet"]} for e in ETAPES],
        "avertissement":
            "Ce cadre ne décerne aucune conformité, aucune neutralité et aucun "
            "label : ces qualifications se constatent sur dossier complet par "
            "un vérificateur accrédité, jamais par un formulaire. Il ne "
            "remplace pas davantage la vérification de l'assujettissement de "
            "votre entité aux textes cités, qui se fait à la date du dossier.",
    }


def sante():
    par_rang = {}
    for lv in LEVIERS:
        par_rang[lv["rang"]] = par_rang.get(lv["rang"], 0) + 1
    return {"module": "decarbonation", "version": VERSION,
            "voies": len(VOIES), "etapes": len(ETAPES),
            "leviers": len(LEVIERS), "leviers_par_rang": par_rang,
            "leviers_relies_au_moteur": sum(1 for lv in LEVIERS if lv.get("champ")),
            "textes": len(TEXTES),
            "rendez_vous": len(RENDEZ_VOUS),
            "problemes": _verifier()}
