"""Le criblage ICPE d'un projet de centre de données.

CE QUE FAIT CE MODULE. Il prend les grandeurs d'un projet — puissance des
groupes électrogènes, volume de gazole stocké, charge en fluide frigorigène,
mode de refroidissement, puissance de charge des batteries — et dit QUELLES
RUBRIQUES de la nomenclature des installations classées sont en jeu, de quel
côté du seuil le projet se trouve, et ce que le régime qui en découle coûte en
délai et en pièces à produire.

CE QU'IL NE FAIT PAS, ET C'EST ESSENTIEL. Il ne classe pas le site. Le
classement est prononcé par le préfet sur un dossier, après instruction, et il
tient compte de choses qui ne sont pas ici : l'implantation, le voisinage, les
autres activités du site, les rubriques connexes, et l'appréciation de
l'inspection. Ce module fait un CRIBLAGE — il dit quelles rubriques aller lire
et à quelle distance du seuil on se trouve. C'est ce qu'un ingénieur fait en
première réunion, et cela n'a jamais remplacé le bureau d'études qui monte le
dossier.

POURQUOI CELA VAUT QUAND MÊME D'ÊTRE FAIT TÔT. Parce que le régime décide du
PLANNING, et que le planning décide du projet. Passer d'une déclaration à un
enregistrement, ou d'un enregistrement à une autorisation, ajoute des mois
d'instruction sur le chemin critique. Une cuve agrandie de vingt mètres cubes
au moment du chiffrage, un groupe froid changé de fluide en phase d'exécution,
un groupe électrogène ajouté pour tenir une redondance : chacune de ces
décisions peut faire basculer un régime, et chacune se prend sans que personne
n'y pense.

LES SEUILS NE SONT PAS FIGÉS, ET CE MODULE LE DIT PARTOUT. La nomenclature est
annexée à l'article R. 511-9 du code de l'environnement et modifiée par décret
plusieurs fois par an. Une valeur recopiée devient fausse sans prévenir. Chaque
rubrique porte donc son numéro, son intitulé et la grandeur à mesurer — ce qui
ne change pas — et ses seuils sont donnés comme REPÈRES DE CRIBLAGE à
revalider sur le texte consolidé en vigueur à la date du dépôt.
"""

VERSION = "2026-08-a"

TEXTE_SOURCE = ("Nomenclature des installations classées — annexe à l'article "
                "R. 511-9 du code de l'environnement.")

RESERVE = (
    "CRIBLAGE, PAS CLASSEMENT. Ce résultat dit quelles rubriques de la "
    "nomenclature sont en jeu sur les grandeurs saisies et de quel côté du "
    "seuil le projet se situe. Il ne classe pas le site : le classement est "
    "prononcé par le préfet sur un dossier instruit, et il dépend aussi de "
    "l'implantation, du voisinage, des autres activités présentes et de "
    "rubriques connexes que ce module n'examine pas. Les seuils sont des "
    "repères à revalider sur le texte consolidé en vigueur à la date du "
    "dépôt — la nomenclature est modifiée par décret plusieurs fois par an. "
    "Le dossier se monte avec un bureau d'études environnement.")


# ═══════════════════════════════════════════════════════════════════════════
#  LES RÉGIMES, ET CE QU'ILS COÛTENT
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE CETTE TABLE APPORTE AU PROJET. Le régime n'est pas une étiquette
# administrative : c'est un DÉLAI et une LISTE DE PIÈCES. Les deux entrent au
# planning et au chiffrage de la maîtrise d'œuvre, et les ignorer est la cause
# la plus banale d'un dossier ICPE déposé trop tard.
#
# LES DÉLAIS SONT DONNÉS EN ORDRE DE GRANDEUR, et le disent. Le délai
# réglementaire et le délai réel ne sont pas le même nombre : toute demande de
# compléments suspend l'instruction, et une demande de compléments est la
# règle, pas l'exception.

REGIMES = {
    "hors": {
        "code": "—",
        "nom": "Non classé au titre de cette rubrique",
        "rang": 0,
        "procedure": "Aucune formalité au titre de cette rubrique. Les autres "
                     "réglementations — code du travail, code de la "
                     "construction, règlement sur les fluides frigorigènes — "
                     "s'appliquent quand même.",
        "delai": "Sans objet.",
        "pieces": "Aucune. Conservez cependant la note de calcul qui montre "
                  "que le seuil n'est pas atteint : c'est elle qu'on demandera "
                  "le jour où une installation sera ajoutée.",
    },
    "D": {
        "code": "D",
        "nom": "Déclaration",
        "rang": 1,
        "procedure": "Télédéclaration, récépissé délivré automatiquement. "
                     "L'exploitation est encadrée par les prescriptions "
                     "générales de l'arrêté ministériel applicable à la "
                     "rubrique.",
        "delai": "Immédiat sur le principe. Le travail réel est en amont : "
                 "établir la conformité aux prescriptions générales, qui sont "
                 "des exigences de conception, pas des formalités.",
        "pieces": "Dossier de déclaration : description de l'installation, "
                  "plans, capacités, et démonstration de conformité aux "
                  "prescriptions générales.",
    },
    "DC": {
        "code": "DC",
        "nom": "Déclaration avec contrôle périodique",
        "rang": 2,
        "procedure": "Même procédure que la déclaration, augmentée d'un "
                     "contrôle par un organisme agréé, à périodicité fixée par "
                     "l'arrêté de prescriptions générales.",
        "delai": "Immédiat pour la déclaration. Le premier contrôle intervient "
                 "après la mise en service, et ses non-conformités se "
                 "corrigent sur une installation en exploitation — donc plus "
                 "cher qu'en conception.",
        "pieces": "Dossier de déclaration, plus l'organisation du contrôle "
                  "périodique à prévoir au contrat d'exploitation.",
    },
    "E": {
        "code": "E",
        "nom": "Enregistrement",
        "rang": 3,
        "procedure": "Dossier déposé en préfecture, consultation du public, "
                     "avis des conseils municipaux concernés, puis arrêté "
                     "préfectoral. Le préfet peut basculer l'instruction en "
                     "autorisation s'il estime les enjeux locaux le "
                     "justifient.",
        "delai": "Plusieurs mois d'ordre de grandeur, hors demandes de "
                 "compléments qui suspendent l'instruction. À placer sur le "
                 "chemin critique dès l'esquisse, pas au dépôt du permis.",
        "pieces": "Dossier d'enregistrement : description, plans "
                  "réglementaires, justification de conformité aux "
                  "prescriptions générales, compatibilité avec les documents "
                  "d'urbanisme et les plans de gestion applicables.",
    },
    "A": {
        "code": "A",
        "nom": "Autorisation environnementale",
        "rang": 4,
        "procedure": "Procédure unique regroupant les autorisations "
                     "environnementales : dossier avec étude d'impact et étude "
                     "de dangers, avis de l'autorité environnementale, enquête "
                     "publique, puis arrêté préfectoral d'autorisation "
                     "assortie de prescriptions propres au site.",
        "delai": "De l'ordre de l'année, études préalables comprises. Les "
                 "études d'impact demandent des campagnes de mesure — bruit, "
                 "air, faune-flore sur un cycle biologique — qui ne se "
                 "compriment pas.",
        "pieces": "Étude d'impact, étude de dangers, résumés non techniques, "
                  "note de présentation non technique, plans réglementaires, "
                  "capacités techniques et financières, et le dossier de "
                  "demande lui-même.",
    },
}

_ORDRE_REGIMES = ("A", "E", "DC", "D", "hors")


def _rang(regime):
    return REGIMES.get(regime, REGIMES["hors"])["rang"]


# ═══════════════════════════════════════════════════════════════════════════
#  LES RUBRIQUES QU'UN CENTRE DE DONNÉES DÉCLENCHE
# ═══════════════════════════════════════════════════════════════════════════
# CE QUI EST DANS LA TABLE, ET POURQUOI CELLES-LÀ. Cinq rubriques couvrent la
# quasi-totalité des centres de données : les groupes électrogènes, leur
# combustible, les fluides frigorigènes, le refroidissement évaporatif et les
# batteries. Elles suffisent à savoir si le projet reste en déclaration ou
# bascule en enregistrement — c'est-à-dire à savoir si le planning tient.
#
# CE QUI N'Y EST PAS EST DIT PLUS BAS, dans RUBRIQUES_CONNEXES. Une rubrique
# absente d'une liste passe pour inexistante ; on préfère la nommer sans seuil
# que la taire.
#
# CHAQUE SEUIL EST UN TRIPLET (borne basse, borne haute, régime). La borne
# haute est None quand il n'y en a pas. Les bornes sont INCLUSIVES en bas et
# EXCLUSIVES en haut — c'est ainsi que la nomenclature est écrite, et c'est la
# convention qui décide du régime d'un projet posé exactement sur le seuil.

RUBRIQUES = {
    "2910": {
        "numero": "2910",
        "intitule": "Combustion — installations consommant des combustibles",
        "sous": "Rubrique 2910-A pour les combustibles listés, dont le gazole "
                "et le fioul domestique des groupes électrogènes de secours.",
        "declenche_par": "Les groupes électrogènes de secours, quels que "
                         "soient leurs heures de fonctionnement.",
        "grandeur": "Puissance thermique nominale totale de l'ensemble des "
                    "moteurs — l'énergie du combustible entrant, pas la "
                    "puissance électrique produite.",
        "unite": "MW",
        "seuils": [(20.0, None, "A"), (1.0, 20.0, "DC")],
        "ce_qui_surprend": "Ce sont les moteurs de SECOURS, qui ne tournent que "
                           "quelques dizaines d'heures par an, qui classent le "
                           "site. Le faible nombre d'heures allège les "
                           "exigences d'émission ; il ne retire pas la "
                           "rubrique. ET L'ALLÈGEMENT TOMBE AVEC LES HEURES : "
                           "une machine appelée pour tenir un effacement de "
                           "réseau ou pour produire derrière le compteur "
                           "fonctionne, elle ne secourt pas. Les valeurs "
                           "limites d'émission s'instruisent alors sur le "
                           "régime réel, et la puissance ajoutée fait "
                           "généralement changer de régime administratif — "
                           "c'est le point que manquent les projets qui "
                           "installent de la production sur site pour éviter "
                           "une file d'attente de raccordement.",
        "conception": "La puissance à déclarer est la puissance THERMIQUE, "
                      "environ deux fois et demie la puissance électrique "
                      "installée. Un site de 2 MW électriques de secours est "
                      "au-delà du premier seuil, ce que la lecture de la seule "
                      "plaque électrique ne laisse pas voir.",
        "moe": "Le bureau d'études environnement chiffre le dossier ; le lot "
               "courants forts fournit les puissances thermiques déclarées par "
               "le constructeur, et le lot environnement les rejets. La "
               "coordination est une interface, pas une transmission.",
        "referentiel": "iso8528",
    },
    "4734": {
        "numero": "4734",
        "intitule": "Produits pétroliers spécifiques et carburants de "
                    "substitution — stockage",
        "sous": "Le gazole ou fioul domestique des cuves de groupes "
                "électrogènes. L'alinéa applicable dépend du produit et du "
                "type de stockage — aérien, enterré, en cuvette.",
        "declenche_par": "Le volume de combustible présent sur le site, cuves "
                         "principales et nourrices comprises.",
        "grandeur": "Quantité totale susceptible d'être présente dans "
                    "l'installation.",
        "unite": "t",
        "seuils": [(1000.0, None, "A"), (100.0, 1000.0, "E"),
                   (50.0, 100.0, "DC")],
        "ce_qui_surprend": "C'est l'autonomie visée qui décide du régime. "
                           "Passer de 48 à 72 heures d'autonomie augmente le "
                           "volume de moitié, et peut faire franchir un seuil "
                           "sans qu'aucune décision « réglementaire » n'ait "
                           "été prise. Et l'autonomie n'est pas qu'un choix "
                           "commercial : le référentiel Tier en fait un "
                           "plancher — douze heures sur site à la capacité N, "
                           "à tous les niveaux. Le niveau visé décide donc du "
                           "volume, qui décide de la rubrique, qui décide du "
                           "délai d'instruction. L'autonomie n'est d'ailleurs "
                           "plus le seul paramètre du volume : une production "
                           "sur site appelée quelques centaines d'heures par "
                           "an demande un stockage sans commune mesure avec "
                           "les douze heures de secours — deux ordres de "
                           "grandeur d'écart, qui font sortir la question du "
                           "champ de cette rubrique pour l'amener sur celui "
                           "des sites à risque d'accident majeur.",
        "conception": "Le volume se convertit en tonnes par la masse "
                      "volumique du produit. Comptez les nourrices et le "
                      "volume mort : la nomenclature parle de ce qui est "
                      "SUSCEPTIBLE d'être présent, pas de ce qui est "
                      "consommé.",
        "moe": "L'implantation des cuves, la rétention et les distances "
               "d'éloignement sont des données d'entrée du plan masse. Les "
               "arbitrer après le permis oblige à reprendre le plan masse.",
    },
    "1185": {
        "numero": "1185",
        "intitule": "Gaz à effet de serre fluorés et substances appauvrissant "
                    "la couche d'ozone",
        "sous": "Emploi dans des équipements clos en exploitation — les "
                "groupes froid et les unités de climatisation.",
        "declenche_par": "La charge cumulée en fluide frigorigène des "
                         "équipements du site.",
        "grandeur": "Quantité cumulée de fluide susceptible d'être présente "
                    "dans l'installation, pour des équipements de capacité "
                    "unitaire supérieure à deux kilogrammes.",
        "unite": "kg",
        "seuils": [(300.0, None, "DC")],
        "ce_qui_surprend": "Le seuil porte sur le CUMUL du site, pas sur "
                           "l'équipement. Une dizaine de groupes froid de "
                           "quarante kilogrammes chacun franchit le seuil "
                           "alors qu'aucun ne le franchit seul.",
        "conception": "Le choix du fluide décide de deux choses à la fois : "
                      "cette rubrique, et le poids carbone des fuites au "
                      "scope 1. Les fluides à faible PRG sont souvent "
                      "inflammables, ce qui déplace le sujet vers la sécurité "
                      "incendie sans le faire disparaître.",
        "moe": "Le registre des fluides est une obligation d'exploitation "
               "qui se prépare en conception : sans plaques signalétiques "
               "relevées et charges consignées à la réception, l'exploitant "
               "hérite d'un inventaire à refaire.",
    },
    "2921": {
        "numero": "2921",
        "intitule": "Refroidissement évaporatif par dispersion d'eau dans un "
                    "flux d'air",
        "sous": "Les tours aéroréfrigérantes humides relèvent du premier "
                "alinéa ; les dispositifs adiabatiques sur circuit primaire "
                "fermé relèvent du second, à un régime plus léger.",
        "declenche_par": "Le mode de refroidissement retenu, dès qu'il "
                         "disperse de l'eau dans un flux d'air.",
        "grandeur": "Puissance thermique évacuée maximale de l'installation "
                    "de refroidissement.",
        "unite": "kW",
        "seuils": [(3000.0, None, "E"), (0.0, 3000.0, "DC")],
        "regime_circuit_ferme": "D",
        "ce_qui_surprend": "Cette rubrique n'a pas de seuil bas : une tour "
                           "évaporative classe le site quelle que soit sa "
                           "taille. Le seuil ne fait que départager "
                           "déclaration et enregistrement.",
        "conception": "L'enjeu réel est sanitaire — le risque de légionelle — "
                      "et il commande un plan d'entretien, des analyses "
                      "périodiques et une conception qui rende les surfaces "
                      "accessibles au nettoyage. Un refroidissement adiabatique "
                      "sur circuit fermé reste concerné dès lors qu'il "
                      "disperse de l'eau : le régime est plus léger, la "
                      "rubrique demeure.",
        "moe": "Le choix entre sec, adiabatique et évaporatif se fait à "
               "l'esquisse, avec le régime ICPE comme critère au même titre "
               "que le PUE et le WUE. Le reprendre en phase projet rouvre "
               "l'aéraulique et le plan masse.",
    },
    "2925": {
        "numero": "2925",
        "intitule": "Accumulateurs électriques — ateliers de charge",
        "sous": "Deux cas séparés selon que la charge dégage de l'hydrogène "
                "— accumulateurs au plomb ouverts — ou non.",
        "declenche_par": "Les batteries des onduleurs, dès que la puissance "
                         "de charge dépasse le seuil du cas applicable.",
        "grandeur": "Puissance maximale de courant continu utilisable pour "
                    "l'opération de charge.",
        "unite": "kW",
        "seuils": [(50.0, None, "D")],
        "seuils_sans_hydrogene": [(600.0, None, "D")],
        "ce_qui_surprend": "La rubrique parle d'« atelier de charge » et "
                           "s'applique pourtant à des locaux de batteries "
                           "d'onduleurs que personne n'appelle un atelier. "
                           "C'est la question ICPE la plus souvent manquée "
                           "d'un centre de données.",
        "conception": "Le seuil dépend de la technologie : les accumulateurs "
                      "qui dégagent de l'hydrogène sont pris à un seuil bien "
                      "plus bas que ceux qui n'en dégagent pas. Le choix "
                      "plomb ouvert / plomb étanche / lithium décide donc du "
                      "classement autant que de la ventilation du local.",
        "moe": "La ventilation du local batteries est dimensionnée sur le "
               "dégagement d'hydrogène par le lot CVC, sur des données du lot "
               "courants forts. C'est une interface classique, et une des "
               "premières à vérifier en synthèse.",
    },
}

RUBRIQUES_CONNEXES = (
    "D'AUTRES RUBRIQUES PEUVENT S'APPLIQUER, et ce module ne les crible pas : "
    "le stockage de gaz inflammables ou de fluides particuliers, "
    "l'installation frigorifique à l'ammoniac, les entrepôts couverts d'un "
    "site mixte, les stations de traitement d'eau, et toute activité voisine "
    "exploitée par la même personne sur le même site — car les installations "
    "d'un même exploitant sur un même site s'apprécient ensemble, et non "
    "installation par installation.")


# ═══════════════════════════════════════════════════════════════════════════
#  LA CONVERSION DES GRANDEURS DU PROJET
# ═══════════════════════════════════════════════════════════════════════════

# Rendement électrique d'un groupe électrogène diesel au régime nominal. Il
# sert UNIQUEMENT de repli quand la puissance thermique déclarée par le
# constructeur n'est pas saisie, et le résultat le dit alors explicitement.
# POURQUOI UN REPLI EST ACCEPTABLE ICI, alors qu'il ne l'est jamais sur un
# facteur d'émission : le criblage vise à savoir s'il faut aller lire la
# rubrique, et un ordre de grandeur suffit pour cela. La valeur déclarée
# remplace le repli dès qu'elle est saisie, et l'écart entre les deux est
# affiché.
RENDEMENT_GROUPE = 0.40
RENDEMENT_GROUPE_SOURCE = (
    "Repère de conception : un groupe électrogène diesel restitue de l'ordre "
    "de 40 % de l'énergie du combustible en électricité au régime nominal. "
    "Valeur d'ordre de grandeur posée pour le criblage, à ±5 points ; la "
    "puissance thermique nominale déclarée par le constructeur la remplace "
    "dès qu'elle est connue.")


def _densite_gazole():
    """La masse volumique du gazole, lue à la Base Carbone via le moteur.

    JAMAIS DE REPLI CHIFFRÉ. Sans la base, on rend None : le tonnage n'est
    alors pas calculé et la rubrique ressort « donnée manquante » au lieu de
    porter un nombre de mémoire. Une seule source pour cette valeur, partagée
    avec le calcul du scope 1 — deux littéraux recopiés auraient divergé.
    """
    try:
        import datacenter as _dc
        f = _dc._facteur_gazole()
    except Exception:                                    # pragma: no cover
        return None
    return (f or {}).get("densite")


def _regime_pour(valeur, seuils):
    """Le régime atteint par une valeur, sur une liste de seuils.

    Bornes inclusives en bas, exclusives en haut — la convention de la
    nomenclature. Une valeur posée EXACTEMENT sur un seuil relève donc du
    régime supérieur, et c'est le cas qui se plaide le plus souvent.
    """
    for bas, haut, regime in seuils:
        if valeur >= bas and (haut is None or valeur < haut):
            return regime
    return "hors"


def _marge(valeur, seuils):
    """La distance au seuil le plus proche AU-DESSUS de la valeur.

    Ce que cette information sert : « vous êtes à 12 % du seuil » se lit
    autrement que « vous êtes en déclaration ». C'est elle qui dit si une
    décision de conception encore ouverte peut faire basculer le régime.
    """
    superieurs = [b for b, _h, _r in seuils if b > valeur]
    if not superieurs:
        return None
    prochain = min(superieurs)
    return {"prochain_seuil": prochain,
            "regime_au_dela": _regime_pour(prochain, seuils),
            "marge": prochain - valeur,
            "part_du_seuil": (valeur / prochain) if prochain else None}


# ═══════════════════════════════════════════════════════════════════════════
#  LE CRIBLAGE
# ═══════════════════════════════════════════════════════════════════════════

def _entree(profil, *cles):
    """La première valeur numérique présente parmi plusieurs noms de champ.

    Rend (valeur, nom_du_champ) ou (None, None). Les valeurs non finies et les
    valeurs négatives sont écartées comme absentes : une puissance négative
    n'est pas une donnée basse, c'est une saisie fausse, et la traiter comme
    une donnée produirait un régime « hors » rassurant et faux.
    """
    import math
    for c in cles:
        v = profil.get(c)
        if v is None or v == "":
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(f) or f < 0:
            continue
        return f, c
    return None, None


def _crible_2910(profil):
    th, champ = _entree(profil, "groupes_puissance_thermique_mw")
    detail, repli = {}, False
    if th is None:
        el, champ = _entree(profil, "groupes_puissance_elec_kw")
        if el is None:
            return None, ("la puissance des groupes électrogènes — thermique "
                          "nominale de préférence, électrique à défaut"), {}
        th = (el / 1000.0) / RENDEMENT_GROUPE
        repli = True
        detail = {"puissance électrique installée (kW)": el,
                  "rendement retenu": RENDEMENT_GROUPE,
                  "conversion": "thermique = électrique / rendement"}
    else:
        detail = {"puissance thermique déclarée (MW)": th}
    return th, None, {"detail": detail, "repli": repli, "champ": champ}


def _crible_4734(profil):
    t, champ = _entree(profil, "fioul_stocke_t")
    if t is not None:
        return t, None, {"detail": {"quantité déclarée (t)": t}, "champ": champ}
    m3, champ = _entree(profil, "fioul_stocke_m3")
    if m3 is None:
        return None, ("le volume de combustible stocké sur le site, cuves et "
                      "nourrices comprises"), {}
    d = _densite_gazole()
    if not d:
        return None, ("la masse volumique du gazole : la Base Carbone n'est "
                      "pas lisible sur ce serveur, le volume ne peut pas être "
                      "converti en tonnes"), {}
    return (m3 * d / 1000.0), None, {
        "detail": {"volume stocké (m³)": m3, "masse volumique (kg/m³)": d,
                   "conversion": "tonnes = volume × masse volumique / 1000"},
        "champ": champ}


def _crible_1185(profil):
    kg, champ = _entree(profil, "charge_frigorigene_kg")
    if kg is None:
        return None, ("la charge cumulée en fluide frigorigène des groupes "
                      "froid"), {}
    return kg, None, {"detail": {"charge cumulée (kg)": kg}, "champ": champ}


def _crible_2921(profil):
    """Le refroidissement évaporatif : la rubrique dépend du MODE, pas d'un
    seuil bas.

    Trois cas distincts, et c'est le mode retenu qui les sépare :
      · évaporatif ouvert (tour) — premier alinéa, seuil à la puissance ;
      · adiabatique sur circuit fermé — second alinéa, régime plus léger ;
      · tout mode sec — rubrique écartée, et la raison est dite.
    """
    fam = (profil.get("refroidissement") or "").strip()
    ouvert = fam == "tour_evaporative"
    ferme = fam == "adiabatique"
    if not (ouvert or ferme):
        if not fam:
            return None, ("le mode de refroidissement retenu"), {}
        return None, None, {"ecarte": True, "champ": "refroidissement",
                            "pourquoi": "Le mode retenu ne disperse pas d'eau "
                                        "dans un flux d'air : la rubrique ne "
                                        "s'applique pas. Elle redeviendrait "
                                        "applicable si un appoint évaporatif "
                                        "ou adiabatique était ajouté en cours "
                                        "de projet."}
    kw, champ = _entree(profil, "puissance_evacuee_kw")
    if kw is None:
        p_it, champ = _entree(profil, "puissance_it_kw")
        if p_it is None:
            return None, ("la puissance thermique évacuée par l'installation "
                          "de refroidissement, ou à défaut la puissance "
                          "informatique installée"), {"circuit_ferme": ferme}
        kw = p_it
        return kw, None, {
            "detail": {"puissance informatique installée (kW)": p_it,
                       "hypothèse": "la chaleur évacuée est prise égale à la "
                                    "puissance informatique — repère de "
                                    "criblage : la chaleur réellement rejetée "
                                    "inclut aussi les pertes de la chaîne "
                                    "électrique et du froid lui-même, elle est "
                                    "donc SUPÉRIEURE"},
            "repli": True, "circuit_ferme": ferme, "champ": champ}
    return kw, None, {"detail": {"puissance évacuée (kW)": kw},
                      "circuit_ferme": ferme, "champ": champ}


def _crible_2925(profil):
    kw, champ = _entree(profil, "batteries_charge_kw")
    if kw is None:
        return None, ("la puissance de charge des batteries d'onduleurs, en "
                      "courant continu"), {}
    h = profil.get("batteries_hydrogene")
    return kw, None, {"detail": {"puissance de charge (kW)": kw,
                                 "dégagement d'hydrogène":
                                     "oui" if h else ("non" if h is not None
                                                      else "non précisé")},
                      "hydrogene": h, "champ": champ}


_CRIBLES = {
    "2910": _crible_2910,
    "4734": _crible_4734,
    "1185": _crible_1185,
    "2921": _crible_2921,
    "2925": _crible_2925,
}


def _seuils_applicables(code, contexte):
    """Les seuils à appliquer, quand la rubrique en a plusieurs jeux.

    Deux rubriques changent de barème selon une caractéristique du projet :
    2921 selon que le circuit est ouvert ou fermé, 2925 selon que la charge
    dégage de l'hydrogène. Choisir le mauvais jeu donnerait un régime faux
    avec la même assurance qu'un vrai — d'où cette fonction, plutôt qu'un
    accès direct à `seuils`.
    """
    r = RUBRIQUES[code]
    if code == "2921" and contexte.get("circuit_ferme"):
        return None, r.get("regime_circuit_ferme", "D")
    if code == "2925" and contexte.get("hydrogene") is False:
        return r["seuils_sans_hydrogene"], None
    return r["seuils"], None


def cribler(profil):
    """Le criblage complet d'un profil de projet.

    RENDU EN TROIS TAS, et l'ordre a un sens :
      · `declenchees` — les rubriques atteintes, du régime le plus lourd au
        plus léger, parce que c'est le plus lourd qui fixe le planning ;
      · `a_verifier` — celles dont la grandeur n'est pas saisie, avec le nom
        de ce qui manque : une donnée absente n'est pas un seuil non atteint,
        et les confondre est la faute que ce module existe pour empêcher ;
      · `ecartees` — celles qui ne s'appliquent pas, avec la raison. Une
        rubrique écartée en silence se lit comme une rubrique oubliée.
    """
    declenchees, a_verifier, ecartees = [], [], []
    for code in RUBRIQUES:
        r = RUBRIQUES[code]
        valeur, manque, ctx = _CRIBLES[code](profil)
        base = {"numero": r["numero"], "intitule": r["intitule"],
                "sous": r["sous"], "grandeur": r["grandeur"],
                "unite": r["unite"], "declenche_par": r["declenche_par"],
                "ce_qui_surprend": r["ce_qui_surprend"],
                "conception": r["conception"], "moe": r["moe"],
                "texte": TEXTE_SOURCE}
        if ctx.get("ecarte"):
            ecartees.append(dict(base, pourquoi=ctx["pourquoi"]))
            continue
        if valeur is None:
            a_verifier.append(dict(base, manque=manque))
            continue
        seuils, regime_impose = _seuils_applicables(code, ctx)
        regime = regime_impose or _regime_pour(valeur, seuils)
        ligne = dict(base, valeur=valeur, regime=regime,
                     regime_nom=REGIMES[regime]["nom"],
                     regime_code=REGIMES[regime]["code"],
                     detail=ctx.get("detail") or {},
                     estimee=bool(ctx.get("repli")),
                     seuils=[{"a_partir_de": b, "jusqu_a": h,
                              "regime": rg, "regime_nom": REGIMES[rg]["nom"]}
                             for b, h, rg in (seuils or [])])
        if seuils:
            ligne["marge"] = _marge(valeur, seuils)
        if regime == "hors":
            ecartees.append(dict(ligne, pourquoi=(
                "La grandeur mesurée reste sous le premier seuil de la "
                "rubrique. Le calcul qui le montre est à conserver : c'est "
                "lui qu'on demandera le jour où une installation sera "
                "ajoutée.")))
        else:
            declenchees.append(ligne)

    declenchees.sort(key=lambda l: (-_rang(l["regime"]), l["numero"]))
    regime_site = declenchees[0]["regime"] if declenchees else "hors"
    return {
        "version": VERSION,
        "declenchees": declenchees,
        "a_verifier": a_verifier,
        "ecartees": ecartees,
        "regime_site": regime_site,
        "regime_site_detail": dict(REGIMES[regime_site]),
        "regime_site_note": _note_regime(regime_site, declenchees, a_verifier),
        "reserve": RESERVE,
        "connexes": RUBRIQUES_CONNEXES,
        "texte": TEXTE_SOURCE,
    }


def _note_regime(regime, declenchees, a_verifier):
    """La phrase qui accompagne le régime du site.

    ELLE DIT CE QUE LE RÉSULTAT VAUT, ce qui dépend d'abord du nombre de
    rubriques encore sans donnée : un régime prononcé sur trois rubriques
    criblées et deux inconnues n'est pas le régime du site, c'est un plancher.
    """
    if a_verifier and regime == "hors":
        return ("Aucune rubrique n'est atteinte SUR LES DONNÉES SAISIES, et "
                "%d rubrique(s) restent sans donnée. Ce n'est pas « le site "
                "n'est pas classé » : c'est « on ne sait pas encore »."
                % len(a_verifier))
    if a_verifier:
        return ("Régime le plus lourd atteint sur les données saisies. Il ne "
                "peut que monter : %d rubrique(s) restent sans donnée et "
                "aucune d'elles ne peut abaisser ce résultat."
                % len(a_verifier))
    if regime == "hors":
        return ("Aucune des cinq rubriques criblées n'est atteinte. Les "
                "rubriques connexes citées plus bas n'ont pas été examinées, "
                "et les installations d'un même exploitant sur un même site "
                "s'apprécient ensemble.")
    return ("Régime le plus lourd des rubriques atteintes — c'est lui qui "
            "commande la procédure et le délai d'instruction du site.")


def rubriques_du_projet(profil):
    """Les rubriques du projet à plat, prêtes pour une liste déroulante.

    UN SEUL ORDRE, ET IL EST CELUI DE L'ACTION : ce qui bloque d'abord — les
    rubriques atteintes, du régime le plus lourd au plus léger —, ce qui
    manque ensuite, ce qui est écarté en dernier. Chaque entrée porte de quoi
    s'afficher sans que la page ait à recalculer quoi que ce soit : une page
    qui recompose un libellé recompose bientôt autre chose que ce qui a été
    criblé.
    """
    c = cribler(profil)
    out = []
    for l in c["declenchees"]:
        out.append({
            "code": l["numero"], "etat": "declenchee",
            "libelle": "%s — %s" % (l["numero"], l["intitule"]),
            "badge": l["regime_code"], "badge_nom": l["regime_nom"],
            "rang": _rang(l["regime"]),
            "resume": "%s : %s %s%s" % (
                l["grandeur"].split(" — ")[0].rstrip(".").strip(),
                _fr(l["valeur"]), l["unite"],
                " (estimée)" if l.get("estimee") else ""),
            "ligne": l})
    for l in c["a_verifier"]:
        out.append({
            "code": l["numero"], "etat": "a_verifier",
            "libelle": "%s — %s" % (l["numero"], l["intitule"]),
            "badge": "?", "badge_nom": "Donnée manquante", "rang": -1,
            "resume": "Il manque " + l["manque"], "ligne": l})
    for l in c["ecartees"]:
        out.append({
            "code": l["numero"], "etat": "ecartee",
            "libelle": "%s — %s" % (l["numero"], l["intitule"]),
            "badge": "—", "badge_nom": "Non applicable", "rang": -2,
            "resume": l.get("pourquoi", ""), "ligne": l})
    return {"rubriques": out, "criblage": c}


def _fr(x):
    """Un nombre à la française, sans décimale inutile."""
    if x is None:
        return "—"
    if abs(x - round(x)) < 0.05:
        return "%d" % round(x)
    return ("%.1f" % x).replace(".", ",")


# ═══════════════════════════════════════════════════════════════════════════
#  CE QUE LE RÉGIME CHANGE POUR LA MISSION
# ═══════════════════════════════════════════════════════════════════════════
# POURQUOI CETTE TABLE EXISTE. Le criblage dit le régime ; il ne dit pas ce
# qu'il faut FAIRE. Or c'est la seule chose qui intéresse un maître d'ouvrage
# en première réunion : qui produit le dossier, quand, et ce que cela ajoute à
# la mission de maîtrise d'œuvre ou d'assistance.

MISSION_PAR_REGIME = {
    "hors": [
        "Établir et conserver la note de criblage : elle prouve que les "
        "seuils ont été examinés, et elle sera demandée à la première "
        "extension.",
        "Inscrire au registre des modifications un point de contrôle : toute "
        "installation ajoutée en cours de projet repasse au criblage.",
    ],
    "D": [
        "Monter le dossier de déclaration et le déposer avant la mise en "
        "service.",
        "Vérifier la conformité du projet aux prescriptions générales de "
        "l'arrêté ministériel applicable — ce sont des exigences de "
        "CONCEPTION, à intégrer au CCTP et non à constater à la réception.",
        "Prévoir au dossier d'exploitation les justificatifs que la "
        "déclaration engage.",
    ],
    "DC": [
        "Monter le dossier de déclaration et le déposer avant la mise en "
        "service.",
        "Intégrer les prescriptions générales au CCTP des lots concernés.",
        "Organiser le contrôle périodique par un organisme agréé : le "
        "prévoir au contrat d'exploitation, avec la première échéance calée "
        "sur la mise en service.",
    ],
    "E": [
        "Lancer le dossier d'enregistrement dès l'esquisse : l'instruction et "
        "la consultation du public sont sur le chemin critique du projet.",
        "Confier le dossier à un bureau d'études environnement, avec une "
        "interface formalisée vers les lots courants forts, CVC et "
        "environnement pour les puissances, volumes et rejets déclarés.",
        "Vérifier la compatibilité avec les documents d'urbanisme et les "
        "plans de gestion applicables — c'est une pièce du dossier, pas une "
        "vérification de courtoisie.",
        "Prévoir au planning la possibilité d'un basculement en autorisation "
        "décidé par le préfet : c'est un risque de délai à porter au registre "
        "des risques, pas une hypothèse d'école.",
    ],
    "A": [
        "Lancer les études d'impact et de dangers AVANT les études de "
        "conception détaillée : les campagnes de mesure — bruit, air, "
        "faune-flore — se déroulent sur un cycle biologique et ne se "
        "compriment pas.",
        "Placer l'enquête publique au planning directeur comme un jalon "
        "fixe, et non comme une tâche à durée ajustable.",
        "Confier le dossier à un bureau d'études environnement dès le "
        "programme, avec une mission de coordination des données d'entrée.",
        "Traiter l'arrêté préfectoral comme une pièce contractuelle : ses "
        "prescriptions propres au site s'imposent au CCTP et peuvent "
        "contredire des choix déjà arrêtés.",
        "Prévoir la reprise du dossier à chaque modification substantielle : "
        "une modification notable se porte à connaissance du préfet.",
    ],
}


def consequences_mission(regime):
    """Ce que le régime ajoute à la mission, avec sa réserve."""
    return {
        "regime": regime,
        "regime_nom": REGIMES.get(regime, REGIMES["hors"])["nom"],
        "actions": list(MISSION_PAR_REGIME.get(regime, [])),
        "reserve": ("Ces actions décrivent ce que le régime IMPLIQUE "
                    "habituellement pour la mission. Elles ne remplacent ni "
                    "l'arrêté de prescriptions générales applicable à la "
                    "rubrique, ni les prescriptions particulières d'un arrêté "
                    "préfectoral."),
    }


def glossaire():
    """Les familles d'infobulles servies par ce module.

    La rubrique se lit en survolant son numéro : ce que la nomenclature vise,
    la grandeur à mesurer, ce qui surprend, et ce que cela change en
    conception. Le régime se lit en survolant son sigle — « DC » ne parle à
    personne hors du métier, et « E » encore moins.
    """
    return {
        "rubrique_icpe": {k: {
            "nom": "Rubrique %s — %s" % (v["numero"], v["intitule"]),
            "aide": ("%s\n\nCe qui la déclenche — %s\n\nGrandeur mesurée — %s "
                     "(%s)\n\nCe qui surprend — %s\n\nEn conception — %s\n\n"
                     "Pour la mission — %s\n\n%s"
                     % (v["sous"], v["declenche_par"], v["grandeur"],
                        v["unite"], v["ce_qui_surprend"], v["conception"],
                        v["moe"], TEXTE_SOURCE)),
        } for k, v in RUBRIQUES.items()},
        "regime_icpe": {k: {
            "nom": ("%s — %s" % (v["code"], v["nom"])) if v["code"] != "—"
                   else v["nom"],
            "aide": ("Procédure — %s\n\nDélai — %s\n\nPièces — %s"
                     % (v["procedure"], v["delai"], v["pieces"])),
        } for k, v in REGIMES.items()},
    }


def referentiel():
    """Les tables, sans criblage — pour la page et la documentation."""
    return {
        "version": VERSION,
        "glossaire": glossaire(),
        "texte": TEXTE_SOURCE,
        "reserve": RESERVE,
        "regimes": REGIMES,
        "rubriques": RUBRIQUES,
        "connexes": RUBRIQUES_CONNEXES,
        "rendement_groupe": RENDEMENT_GROUPE,
        "rendement_groupe_source": RENDEMENT_GROUPE_SOURCE,
        "mission_par_regime": MISSION_PAR_REGIME,
        "champs": CHAMPS,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  LES ENTRÉES DU CRIBLAGE
# ═══════════════════════════════════════════════════════════════════════════
# AUCUNE N'A DE VALEUR PAR DÉFAUT, et c'est délibéré. Un défaut ferait
# apparaître un régime calculé sur des chiffres que personne n'a saisis — et
# un régime a l'air d'un résultat même quand il repose sur du vide. Sans
# saisie, la rubrique ressort « donnée manquante », ce qui est la vérité.

CHAMPS = [
    {"id": "groupes_puissance_thermique_mw",
     "label": "Puissance thermique nominale totale des groupes",
     "unite": "MW", "type": "nombre", "rubrique": "2910",
     "aide": "L'énergie du combustible entrant, telle que déclarée par le "
             "constructeur — pas la puissance électrique produite. Si elle "
             "n'est pas connue, saisissez la puissance électrique ci-dessous "
             "et le criblage l'estimera en le disant."},
    {"id": "groupes_puissance_elec_kw",
     "label": "Puissance électrique installée des groupes",
     "unite": "kW", "type": "nombre", "rubrique": "2910",
     "aide": "Somme des puissances de secours des groupes. Utilisée seulement "
             "si la puissance thermique n'est pas saisie ; la conversion est "
             "alors affichée avec son rendement."},
    {"id": "fioul_stocke_m3", "label": "Combustible stocké sur le site",
     "unite": "m³", "type": "nombre", "rubrique": "4734",
     "aide": "Cuves principales ET nourrices, volume mort compris : la "
             "nomenclature parle de ce qui est SUSCEPTIBLE d'être présent."},
    {"id": "fioul_stocke_t", "label": "Combustible stocké — quantité déclarée",
     "unite": "t", "type": "nombre", "rubrique": "4734",
     "aide": "À saisir si la quantité est connue en tonnes ; elle remplace "
             "alors la conversion depuis le volume."},
    {"id": "puissance_evacuee_kw",
     "label": "Puissance thermique évacuée par le refroidissement",
     "unite": "kW", "type": "nombre", "rubrique": "2921",
     "aide": "Puissance maximale évacuée par l'installation. À défaut, le "
             "criblage prend la puissance informatique installée — un repère "
             "BAS, puisque la chaleur rejetée comprend aussi les pertes de la "
             "chaîne électrique et du froid."},
    {"id": "batteries_charge_kw",
     "label": "Puissance de charge des batteries d'onduleurs",
     "unite": "kW", "type": "nombre", "rubrique": "2925",
     "aide": "Puissance maximale de courant continu utilisable pour la "
             "charge, tous locaux batteries confondus."},
    {"id": "batteries_hydrogene",
     "label": "Les batteries dégagent-elles de l'hydrogène à la charge ?",
     "type": "booleen", "rubrique": "2925",
     "aide": "Les accumulateurs au plomb ouverts en dégagent ; les "
             "technologies étanches et lithium, non. Le seuil de la rubrique "
             "n'est pas le même dans les deux cas. Sans réponse, le criblage "
             "retient le cas le plus contraignant."},
]


def _verifier():
    """Les fautes de structure, ou une liste vide.

    LA VÉRIFICATION QUI COMPTE est celle des seuils : ils doivent être en
    ordre décroissant et sans recouvrement, sinon une même valeur relèverait
    de deux régimes et le premier de la liste l'emporterait en silence.
    """
    fautes = []
    for code, r in RUBRIQUES.items():
        if r["numero"] != code:
            fautes.append("rubrique %s : numéro incohérent (%s)" % (code, r["numero"]))
        for nom in ("seuils", "seuils_sans_hydrogene"):
            seuils = r.get(nom)
            if not seuils:
                continue
            precedent_bas = None
            for bas, haut, regime in seuils:
                if regime not in REGIMES:
                    fautes.append("rubrique %s : régime inconnu (%s)" % (code, regime))
                if haut is not None and haut <= bas:
                    fautes.append("rubrique %s : borne haute sous la borne basse "
                                  "(%s ≤ %s)" % (code, haut, bas))
                if precedent_bas is not None and bas >= precedent_bas:
                    fautes.append("rubrique %s : seuils non décroissants "
                                  "(%s après %s)" % (code, bas, precedent_bas))
                precedent_bas = bas
        if code not in _CRIBLES:
            fautes.append("rubrique %s : aucune fonction de criblage" % code)
    for code in _CRIBLES:
        if code not in RUBRIQUES:
            fautes.append("criblage %s : aucune rubrique correspondante" % code)
    for regime in REGIMES:
        if regime not in MISSION_PAR_REGIME:
            fautes.append("régime %s : aucune conséquence de mission" % regime)
    for c in CHAMPS:
        if c.get("rubrique") not in RUBRIQUES:
            fautes.append("champ %s : rubrique inconnue (%s)"
                          % (c["id"], c.get("rubrique")))
    return fautes


_FAUTES = _verifier()
if _FAUTES:
    raise RuntimeError("icpe_dc — table incohérente : " + " ; ".join(_FAUTES))
