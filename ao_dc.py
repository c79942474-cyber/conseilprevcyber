"""Le dossier marché du client, et la réponse à l'appel d'offres.

CE QUE CE MODULE FAIT. Deux choses, dans cet ordre :

  1. IL LIT LE DOSSIER DE CONSULTATION. On dépose les pièces du client — CCTP,
     CCAP, CCAG, règlement de consultation, DPGF, tableau de répartition
     MOE/AMO, feuilles de calcul — et il dit ce que chaque fichier EST, ce
     qu'il engage, les points de vigilance qu'il contient, et surtout CE QUI
     MANQUE au dossier. Une pièce absente est l'information la plus utile d'une
     analyse de DCE, et c'est celle qu'on remarque le moins.

  2. IL PRÉPARE LA RÉPONSE. Il déroule la composition du dossier de
     candidature, dit qui produit quoi, ce que chaque pièce doit contenir, et
     lesquelles bloquent la remise si elles manquent.

CE QU'IL NE FAIT PAS, ET IL FAUT LE DIRE FORT. Il ne remplit pas les
formulaires à votre place et n'engage personne. Les DC1 et DC2 portent des
déclarations sur l'honneur dont la fausseté est sanctionnée : elles se signent
par une personne habilitée, en connaissance de cause. Ce module dit ce que
chaque rubrique attend ; il ne déclare rien.

L'EXTRACTION EST LITTÉRALE, ET C'EST VOULU. Les points relevés dans les pièces
sont des CITATIONS avec leur position, jamais des interprétations. Un extracteur
qui « comprendrait » un CCAP se tromperait un jour sans le dire, sur une date
de remise ou une pondération de critère — c'est-à-dire sur ce qui fait perdre
une consultation. Ce qui n'est pas trouvé est déclaré non trouvé, jamais
supposé.
"""

import re

VERSION = "2026-08-a"


# ═══════════════════════════════════════════════════════════════════════════
#  1. LES PIÈCES DU DOSSIER DE CONSULTATION
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE LA TABLE APPORTE. Chaque pièce dit ce qu'elle EST, ce qu'elle ENGAGE
# — car toutes n'engagent pas de la même façon — et ce qu'il faut y CHERCHER en
# premier. La dernière colonne, `piege`, est celle qui se paie : elle nomme la
# faute de lecture propre à chaque pièce.
#
# L'ORDRE DE LECTURE N'EST PAS L'ORDRE DU DOSSIER. On ouvre le règlement de
# consultation en premier — il dit ce qu'il faut remettre et quand —, puis le
# CCAP, qui dit ce qu'on signe. Le CCTP vient après : il est le plus long et le
# moins urgent, parce qu'un dossier techniquement parfait remis hors délai ne
# se lit pas.

PIECES_MARCHE = {
    "rc": {
        "nom": "Règlement de la consultation",
        "sigle": "RC",
        "rang_lecture": 1,
        "contractuel": False,
        "ce_que_c_est": "La règle du jeu de la consultation : procédure, "
                        "composition du dossier à remettre, date et heure "
                        "limites, modalités de dépôt, critères de jugement et "
                        "leur pondération, conditions de visite.",
        "engage": "Il n'est pas une pièce du marché — il cesse de s'appliquer "
                  "à la signature — mais il commande l'ADMISSION de l'offre. "
                  "Une pièce manquante à la liste qu'il fixe rend le pli "
                  "irrégulier.",
        "chercher": "La date et l'heure limites, la liste exacte des pièces à "
                    "remettre, les critères et leur pondération, les "
                    "conditions de groupement imposées, et l'obligation ou "
                    "non de visite.",
        "piege": "Lire la liste des pièces en diagonale parce qu'elle "
                 "« ressemble à d'habitude ». C'est là que se glissent le "
                 "formulaire d'évaluation des tiers propre à l'acheteur, la "
                 "note au format imposé, ou la limite de pages qui fait "
                 "écarter un mémoire technique.",
        "obligatoire_dce": True,
    },
    "ae": {
        "nom": "Acte d'engagement",
        "sigle": "AE / ATTRI1",
        "rang_lecture": 2,
        "contractuel": True,
        "ce_que_c_est": "La pièce que le candidat signe pour s'engager : "
                        "identification, prix ou taux, délai, et acceptation "
                        "des autres pièces.",
        "engage": "Tout. C'est la signature de l'offre.",
        "chercher": "Le contenu exact de l'engagement de prix — forfait, "
                    "taux, bordereau —, la durée, et la liste des pièces "
                    "contractuelles qu'il vise par renvoi.",
        "piege": "Signer avant d'avoir lu les pièces qu'il vise. L'acte "
                 "d'engagement fait entrer au contrat, par simple renvoi, des "
                 "documents qu'on n'a parfois pas ouverts.",
        "obligatoire_dce": True,
    },
    "ccap": {
        "nom": "Cahier des clauses administratives particulières",
        "sigle": "CCAP",
        "rang_lecture": 3,
        "contractuel": True,
        "ce_que_c_est": "Les clauses administratives propres au marché : "
                        "prix et révision, délais, pénalités, avances et "
                        "acomptes, garanties, assurances, propriété "
                        "intellectuelle, résiliation, litiges.",
        "engage": "C'est la pièce qui décide de ce que coûte un retard, de "
                  "qui porte quel risque, et de la façon dont on est payé.",
        "chercher": "Le régime des pénalités et leur plafond, les délais de "
                    "paiement, la retenue de garantie, les assurances "
                    "exigées, les clauses de propriété intellectuelle sur les "
                    "études, et l'ordre de priorité des pièces contractuelles.",
        "piege": "Ne pas lire l'article qui fixe l'ORDRE DE PRIORITÉ des "
                 "pièces. C'est lui qui dit laquelle l'emporte quand le CCTP "
                 "et le CCAP se contredisent — et ils se contredisent "
                 "toujours quelque part.",
        "obligatoire_dce": True,
    },
    "ccag": {
        "nom": "Cahier des clauses administratives générales",
        "sigle": "CCAG",
        "rang_lecture": 4,
        "contractuel": True,
        "ce_que_c_est": "Le socle administratif type auquel le marché se "
                        "réfère — prestations intellectuelles, travaux, "
                        "maîtrise d'œuvre, fournitures et services, "
                        "techniques de l'information. Il n'est pas rédigé par "
                        "l'acheteur : il est choisi.",
        "engage": "Il s'applique intégralement, SAUF sur les points où le "
                  "CCAP y déroge. Les dérogations doivent être récapitulées "
                  "dans un article final du CCAP.",
        "chercher": "Lequel est retenu — le CCAG applicable change tout —, et "
                    "la liste des dérogations récapitulées au CCAP.",
        "piege": "Croire que « CCAG applicable » veut dire « conditions "
                 "standard, rien à lire ». Les dérogations sont l'endroit où "
                 "l'acheteur déplace le risque, et elles tiennent parfois en "
                 "trois lignes à la fin du CCAP.",
        "obligatoire_dce": False,
    },
    "cctp": {
        "nom": "Cahier des clauses techniques particulières",
        "sigle": "CCTP",
        "rang_lecture": 5,
        "contractuel": True,
        "ce_que_c_est": "Le besoin technique : périmètre, prestations "
                        "attendues, performances exigées, contraintes "
                        "d'exécution, livrables et leur forme.",
        "engage": "Il définit la prestation due. Ce qui n'y est pas n'est pas "
                  "dû — et ce qui y est, l'est, même caché dans une "
                  "sous-section.",
        "chercher": "Les performances CHIFFRÉES et leur méthode de preuve "
                    "(un PUE engagé sans plan de comptage est invérifiable), "
                    "les livrables et leurs indices, les contraintes de "
                    "phasage, et les prestations « pour mémoire » qui "
                    "reviennent en cours de marché.",
        "piege": "Chiffrer un CCTP sans relever ses exigences de PREUVE. Les "
                 "essais, les campagnes de mesure et les périodes "
                 "d'observation coûtent, et ils ne figurent presque jamais "
                 "dans la décomposition de prix demandée.",
        "obligatoire_dce": True,
    },
    "dpgf": {
        "nom": "Décomposition du prix global et forfaitaire",
        "sigle": "DPGF",
        "rang_lecture": 6,
        "contractuel": True,
        "ce_que_c_est": "Le tableau qui décompose le prix par poste. Sur un "
                        "marché de maîtrise d'œuvre, il décompose par mission "
                        "et par phase ; sur un marché de travaux, par lot et "
                        "par ouvrage.",
        "engage": "Il sert à analyser l'offre et, souvent, à régler les "
                  "acomptes et à valoriser les modifications. Une ligne mal "
                  "remplie se paie pendant toute la durée du marché.",
        "chercher": "Les lignes à zéro ou absentes, les unités imposées, et "
                    "la correspondance ligne à ligne avec le CCTP. Un poste "
                    "du CCTP sans ligne de DPGF est un poste que personne ne "
                    "paiera.",
        "piege": "Répartir un prix global sur les lignes « pour que ça "
                 "tombe juste ». La répartition sert de base au règlement des "
                 "modifications : une ligne sous-évaluée revient au moment de "
                 "l'avenant, et jamais en votre faveur.",
        "obligatoire_dce": False,
    },
    "bpu": {
        "nom": "Bordereau des prix unitaires",
        "sigle": "BPU",
        "rang_lecture": 7,
        "contractuel": True,
        "ce_que_c_est": "Les prix unitaires applicables aux prestations "
                        "commandées au fil de l'eau, souvent accompagné d'un "
                        "détail quantitatif estimatif qui n'engage pas les "
                        "quantités.",
        "engage": "Les PRIX, pas les quantités. C'est la différence avec la "
                  "décomposition d'un prix forfaitaire, et elle change "
                  "complètement la stratégie de réponse.",
        "chercher": "Les quantités estimatives et leur valeur réelle "
                    "probable, les prix appelés à être commandés souvent, et "
                    "les unités ambiguës.",
        "piege": "Optimiser sur les quantités estimatives affichées. Elles "
                 "n'engagent pas l'acheteur, et un prix bas placé sur une "
                 "ligne qui ne sera jamais commandée n'améliore que le "
                 "classement — jusqu'à ce que l'acheteur commande l'inverse.",
        "obligatoire_dce": False,
    },
    "repartition": {
        "nom": "Tableau de répartition des missions MOE / AMO",
        "sigle": "Répartition MOE/AMO",
        "rang_lecture": 8,
        "contractuel": True,
        "ce_que_c_est": "Le tableau qui dit, tâche par tâche, qui fait, qui "
                        "contrôle, qui valide et qui est informé — entre la "
                        "maîtrise d'ouvrage, son assistant et la maîtrise "
                        "d'œuvre.",
        "engage": "Le périmètre réel de la mission, bien plus précisément "
                  "que l'intitulé des missions normalisées. C'est lui qu'on "
                  "ressortira en cas de désaccord sur « qui devait le faire ».",
        "chercher": "Les tâches attribuées à personne, celles attribuées à "
                    "deux, et celles où la maîtrise d'œuvre « assiste » sans "
                    "qu'on dise à quoi. Comptez aussi les tâches ajoutées par "
                    "rapport aux missions normalisées : elles se chiffrent.",
        "piege": "Le lire comme un organigramme. C'est un document de PRIX : "
                 "chaque case cochée face à votre nom est une charge, et "
                 "l'absence de case n'est une économie que si elle est "
                 "cochée en face de quelqu'un d'autre.",
        "obligatoire_dce": False,
    },
    "calculs": {
        "nom": "Feuilles de calcul et données d'entrée",
        "sigle": "Calculs",
        "rang_lecture": 9,
        "contractuel": False,
        "ce_que_c_est": "Les tableurs fournis par l'acheteur : bilans de "
                        "puissance, hypothèses de charge, estimations, "
                        "surfaces, plannings prévisionnels.",
        "engage": "Rien par eux-mêmes, en général — mais ils portent les "
                  "hypothèses sur lesquelles l'acheteur a bâti son besoin, et "
                  "les reprendre sans les vérifier revient à en hériter.",
        "chercher": "Les hypothèses cachées dans les formules, les valeurs "
                    "codées en dur, les onglets masqués, et la cohérence "
                    "entre les totaux affichés et le CCTP.",
        "piege": "Les traiter comme des données. Ce sont des HYPOTHÈSES "
                 "d'acheteur : un bilan de puissance fourni ne vaut pas "
                 "note de calcul, et le reprendre tel quel transfère sur vous "
                 "une erreur que vous n'avez pas commise.",
        "obligatoire_dce": False,
    },
    "plans": {
        "nom": "Plans et pièces graphiques",
        "sigle": "Plans",
        "rang_lecture": 10,
        "contractuel": True,
        "ce_que_c_est": "Plans de l'existant, plans de principe, schémas de "
                        "principe des installations, plans masse.",
        "engage": "Ils sont contractuels quand le marché les vise. Sur un "
                  "existant, ils sont souvent faux, et ils engagent quand "
                  "même.",
        "chercher": "L'indice et la date, la mention « pour information » ou "
                    "« contractuel », et la cohérence avec le CCTP.",
        "piege": "Chiffrer un fit-out ou un rétrofit sur les plans fournis "
                 "sans relevé. Les plans d'origine d'un site en exploitation "
                 "ne décrivent plus l'ouvrage, et l'écart se découvre en "
                 "exécution.",
        "obligatoire_dce": False,
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  L'IDENTIFICATION D'UNE PIÈCE
# ═══════════════════════════════════════════════════════════════════════════
# COMMENT ELLE PROCÈDE, ET POURQUOI DANS CET ORDRE. Le nom du fichier est
# regardé en premier parce qu'il est presque toujours juste — les acheteurs
# nomment leurs pièces —, mais il ne suffit jamais : « 03_CCAP_CCTP.pdf »
# existe. Le contenu tranche donc, et le résultat porte SA CONFIANCE et les
# INDICES qui l'ont produite. Une classification sans indice ne se conteste
# pas ; celle-ci se relit.
#
# UNE PIÈCE NON RECONNUE RESTE NON RECONNUE. On ne la range pas dans la
# catégorie la plus proche : un CCTP pris pour un CCAP ferait chercher des
# pénalités là où il n'y en a pas, et conclure qu'il n'y en a pas.

# LA FRONTIÈRE D'UN SIGLE N'EST PAS `\b`, ET CE DÉFAUT A COÛTÉ LA MOITIÉ DE
# CETTE FONCTION. En expression régulière, « _ » est un caractère de MOT :
# `\brc\b` ne s'accroche donc PAS dans « 01_RC.pdf », ni `\bccap\b` dans
# « 02_CCAP.pdf » ou « CCAP_v2.pdf » — c'est-à-dire dans la façon dont les
# plateformes acheteur nomment leurs pièces. Le nom du fichier, que ce module
# regarde EN PREMIER parce qu'il est « presque toujours juste », ne reconnaissait
# rien sur la convention la plus répandue.
#
# CE QUE LE DÉFAUT PRODUISAIT, ET POURQUOI IL NE SE VOYAIT PAS. Le texte
# rattrapait : un CCAP contient « cahier des clauses administratives
# particulières ». Mais une DPGF est un TABLEUR — pas de texte, pas de
# rattrapage. Éprouvé : « 04_DPGF.xlsx » était rangé en « Calculs » par son
# extension, et la DPGF, présente dans le dossier, était déclarée MANQUANTE.
# C'est-à-dire que le module se trompait sur ce qu'il vend comme son
# information la plus utile.
#
# LA FRONTIÈRE JUSTE EST « PAS UNE LETTRE ». Le nom est déjà minusculé et
# désaccentué : borner par des lettres laisse passer « _ », « - », « . », les
# chiffres et les bords, et refuse « rc » dans « parcours » ou « cct » dans
# « cctp ».


def _sigle(s):
    """Le motif d'un sigle de pièce, borné par autre chose qu'une lettre."""
    return r"(?<![a-z])" + s + r"(?![a-z])"


_MARQUEURS = {
    "rc": {
        "nom": [_sigle("rc"), r"r[eè]glement.{0,10}consultation", _sigle("rdc")],
        "texte": [r"r[èe]glement de (?:la )?consultation",
                  r"date (?:et heure )?limite de r[ée]ception des (?:plis|offres|candidatures)",
                  r"crit[èe]res? (?:de )?(?:jugement|s[ée]lection|attribution)",
                  r"composition du dossier"],
    },
    "ae": {
        "nom": [_sigle("ae"), r"acte.{0,3}d.?engagement", r"attri1"],
        "texte": [r"acte d.?engagement", r"attri1",
                  r"apr[èe]s avoir pris connaissance"],
    },
    "ccap": {
        "nom": [_sigle("ccap"), r"clauses administratives particuli"],
        "texte": [r"cahier des clauses administratives particuli",
                  r"p[ée]nalit[ée]s? de retard", r"retenue de garantie",
                  r"ordre de priorit[ée] des pi[èe]ces"],
    },
    "ccag": {
        "nom": [_sigle("ccag"), r"clauses administratives g[ée]n[ée]rales"],
        "texte": [r"cahier des clauses administratives g[ée]n[ée]rales",
                  r"ccag[- ](?:pi|moe|travaux|fcs|tic)"],
    },
    "cctp": {
        "nom": [_sigle("cctp"), r"clauses techniques", _sigle("cct")],
        "texte": [r"cahier des clauses techniques particuli",
                  r"prestations attendues", r"performances? exig[ée]es?"],
    },
    "dpgf": {
        "nom": [_sigle("dpgf"), r"d[ée]composition du prix"],
        "texte": [r"d[ée]composition du prix global et forfaitaire",
                  _sigle("dpgf")],
    },
    "bpu": {
        "nom": [_sigle("bpu"), r"bordereau des prix", _sigle("dqe")],
        "texte": [r"bordereau des prix unitaires",
                  r"d[ée]tail quantitatif estimatif"],
    },
    "repartition": {
        "nom": [r"r[ée]partition", r"moe.?amo", r"amo.?moe", _sigle("raci")],
        "texte": [r"r[ée]partition des (?:missions|t[âa]ches)",
                  r"ma[îi]trise d.?[œoe]uvre.{0,40}assistan",
                  _sigle("raci")],
    },
    "calculs": {
        "nom": [r"calcul", r"bilan de puissance", r"tableur", r"estimation"],
        "texte": [r"bilan de puissance", r"hypoth[èe]ses de calcul"],
    },
    "plans": {
        "nom": [_sigle("plan"), r"plans", r"sch[ée]ma", _sigle("dwg"), _sigle("pid")],
        "texte": [r"[ée]chelle\s*:?\s*1[/:]", r"nomenclature des plans"],
    },
}

# Extensions qui font pencher vers une nature de pièce, à défaut d'autre indice.
_EXT_INDICE = {
    ".xlsx": ("calculs", "un tableur, sans marqueur plus précis"),
    ".xls": ("calculs", "un tableur, sans marqueur plus précis"),
    ".csv": ("calculs", "un tableau de données, sans marqueur plus précis"),
    ".dwg": ("plans", "un fichier de dessin"),
    ".dxf": ("plans", "un fichier de dessin"),
}


def _sans_accent(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn")


def identifier(nom, texte="", extension=""):
    """Ce qu'une pièce est, avec la confiance et les indices qui le disent.

    LE RÉSULTAT PORTE TOUJOURS SES INDICES. Un classement qu'on ne peut pas
    contester est un classement qu'on croit sur parole — et cette fonction se
    trompera un jour sur un dossier dont les pièces sont mal nommées.
    """
    n = _sans_accent((nom or "").lower())
    t = _sans_accent((texte or "")[:20000].lower())
    scores, indices = {}, {}
    for code, m in _MARQUEURS.items():
        pts, vus = 0, []
        for motif in m.get("nom", []):
            if re.search(motif, n):
                pts += 3
                vus.append("nom du fichier : « %s »" % motif)
        for motif in m.get("texte", []):
            if re.search(motif, t):
                pts += 2
                vus.append("dans le texte : « %s »" % motif)
        if pts:
            scores[code] = pts
            indices[code] = vus
    if not scores:
        ext = (extension or "").lower()
        if ext in _EXT_INDICE:
            code, pourquoi = _EXT_INDICE[ext]
            return {"code": code, "nom": PIECES_MARCHE[code]["nom"],
                    "confiance": "faible", "indices": [pourquoi],
                    "reconnue": True}
        return {"code": None, "nom": None, "confiance": "aucune",
                "indices": [], "reconnue": False,
                "pourquoi": ("Aucun marqueur reconnu, ni dans le nom du "
                             "fichier ni dans le texte. La pièce n'est PAS "
                             "rangée par défaut : la classer au plus proche "
                             "ferait chercher dedans ce qui n'y est pas.")}
    meilleur = max(scores, key=lambda c: (scores[c], c))
    second = sorted((s for c, s in scores.items() if c != meilleur),
                    reverse=True)
    ecart = scores[meilleur] - (second[0] if second else 0)
    confiance = "forte" if scores[meilleur] >= 5 and ecart >= 3 else (
        "moyenne" if ecart >= 2 else "faible")
    r = {"code": meilleur, "nom": PIECES_MARCHE[meilleur]["nom"],
         "confiance": confiance, "indices": indices[meilleur],
         "reconnue": True}
    if confiance != "forte" and len(scores) > 1:
        r["autres"] = [{"code": c, "nom": PIECES_MARCHE[c]["nom"]}
                       for c in sorted(scores, key=lambda c: -scores[c])
                       if c != meilleur][:2]
    return r


# ═══════════════════════════════════════════════════════════════════════════
#  2. CE QU'ON RELÈVE DANS LES PIÈCES
# ═══════════════════════════════════════════════════════════════════════════
# TOUT CE QUI EST RELEVÉ EST UNE CITATION. Le module rend le passage trouvé,
# pas son interprétation : « remise avant le 12/09/2026 à 12 h 00 » se lit et
# se vérifie ; « délai de remise : 12 septembre » a déjà perdu l'heure, et
# l'heure fait perdre des consultations.
#
# CE QUI N'EST PAS TROUVÉ EST DÉCLARÉ NON TROUVÉ. Jamais supposé, jamais
# rempli par un défaut. Une date de remise absente du relevé veut dire « allez
# la lire vous-même », et c'est la seule réponse honnête.

RELEVES = [
    {
        "cle": "date_limite",
        "libelle": "Date et heure limites de remise",
        "pieces": ("rc",),
        "motifs": [
            r"(?:date|heure)s?\s*(?:et\s*heures?\s*)?limites?[^.\n]{0,120}",
            r"remise des (?:plis|offres|candidatures)[^.\n]{0,120}",
            r"avant le\s+\d{1,2}[/ ]\w+[/ ]\d{2,4}[^.\n]{0,60}",
        ],
        "pourquoi": "Le seul élément qui rend tout le reste inutile s'il est "
                    "manqué.",
        "piege": "L'heure compte autant que la date, et le fuseau de la "
                 "plateforme de dépôt fait foi — pas la pendule du bureau.",
    },
    {
        "cle": "criteres",
        "libelle": "Critères de jugement et pondération",
        "pieces": ("rc",),
        "motifs": [
            r"crit[èe]res?\s+(?:de\s+)?(?:jugement|attribution|s[ée]lection)[^.\n]{0,200}",
            r"(?:valeur technique|prix des prestations)[^.\n]{0,80}\d{1,3}\s*%",
            r"\d{1,3}\s*%[^.\n]{0,60}(?:valeur technique|prix|d[ée]lai)",
        ],
        "pourquoi": "La pondération dit où placer l'effort. Un mémoire "
                    "technique à 60 % ne se rédige pas comme un mémoire à "
                    "20 %.",
        "piege": "Les sous-critères pèsent souvent plus que le critère : un "
                 "prix à 40 % avec une valeur technique décomposée en quatre "
                 "sous-critères se gagne sur les sous-critères.",
    },
    {
        "cle": "groupement",
        "libelle": "Forme de groupement imposée ou admise",
        "pieces": ("rc",),
        "motifs": [
            r"groupement\s+(?:conjoint|solidaire)[^.\n]{0,120}",
            r"mandataire[^.\n]{0,120}solidaire[^.\n]{0,60}",
            r"forme de groupement[^.\n]{0,120}",
        ],
        "pourquoi": "Elle décide de la responsabilité de chaque cotraitant et "
                    "de la façon de remplir le DC1.",
        "piege": "« Conjoint avec mandataire solidaire » n'est pas "
                 "« solidaire » : le mandataire répond du groupement entier, "
                 "les autres de leur seule prestation. C'est un risque à "
                 "chiffrer avant d'accepter le mandat.",
    },
    {
        "cle": "visite",
        "libelle": "Visite de site",
        "pieces": ("rc", "cctp"),
        "motifs": [
            r"visite (?:du site|des lieux|obligatoire)[^.\n]{0,140}",
            r"attestation de visite[^.\n]{0,100}",
        ],
        "pourquoi": "Une visite obligatoire non faite rend l'offre "
                    "irrégulière, et les créneaux sont limités.",
        "piege": "L'attestation est souvent une pièce à joindre : la visite "
                 "faite sans attestation signée ne compte pas.",
    },
    {
        "cle": "penalites",
        "libelle": "Pénalités et plafonds",
        "pieces": ("ccap",),
        "motifs": [
            r"p[ée]nalit[ée]s?[^.\n]{0,180}",
            r"plafond[^.\n]{0,80}p[ée]nalit[ée]s?[^.\n]{0,80}",
        ],
        "pourquoi": "Elles chiffrent le risque de retard, et leur plafond dit "
                    "jusqu'où il va.",
        "piege": "Une pénalité sans plafond, sur un marché d'études, peut "
                 "dépasser les honoraires. C'est le premier point à "
                 "renégocier ou à provisionner.",
    },
    {
        "cle": "priorite_pieces",
        "libelle": "Ordre de priorité des pièces contractuelles",
        "pieces": ("ccap", "ae"),
        "motifs": [
            r"(?:ordre de priorit[ée]|pi[èe]ces contractuelles)[^.\n]{0,200}",
            r"en cas de contradiction[^.\n]{0,160}",
        ],
        "pourquoi": "Il tranche les contradictions entre pièces, et il y en a "
                    "toujours.",
        "piege": "L'ordre place parfois une annexe au-dessus du CCTP. Une "
                 "annexe qu'on n'a pas lue peut ainsi l'emporter sur la pièce "
                 "qu'on a chiffrée.",
    },
    {
        "cle": "derogations",
        "libelle": "Dérogations au CCAG",
        "pieces": ("ccap",),
        "motifs": [
            r"d[ée]rogation[^.\n]{0,180}",
            r"il est d[ée]rog[ée][^.\n]{0,160}",
        ],
        "pourquoi": "C'est là que le risque se déplace vers le titulaire, "
                    "souvent en trois lignes à la fin du document.",
        "piege": "Une dérogation non récapitulée reste opposable si elle "
                 "figure au corps du CCAP : le récapitulatif est une "
                 "obligation de forme, pas une condition de validité.",
    },
    {
        "cle": "assurances",
        "libelle": "Assurances et garanties exigées",
        "pieces": ("ccap", "rc"),
        "motifs": [
            r"assurance[^.\n]{0,160}",
            r"responsabilit[ée] (?:civile|d[ée]cennale)[^.\n]{0,120}",
            r"retenue de garantie[^.\n]{0,120}",
        ],
        "pourquoi": "Les montants exigés peuvent excéder les polices en cours "
                    "et demander une extension, qui prend du temps.",
        "piege": "L'attestation doit couvrir la période d'exécution, pas la "
                 "date de remise. Une police qui expire pendant le marché "
                 "est un motif de rejet.",
    },
    {
        "cle": "delai",
        "libelle": "Délais et durée du marché",
        "pieces": ("ccap", "cctp", "ae"),
        "motifs": [
            r"d[ée]lai (?:global|d.?ex[ée]cution|de r[ée]alisation)[^.\n]{0,140}",
            r"dur[ée]e du march[ée][^.\n]{0,120}",
            r"reconduction[^.\n]{0,120}",
        ],
        "pourquoi": "Il commande le plan de charge et les pénalités.",
        "piege": "Le délai court souvent de la NOTIFICATION, pas de l'ordre "
                 "de service. L'écart entre les deux se compte en semaines.",
    },
    {
        "cle": "performances",
        "libelle": "Performances techniques engagées",
        "pieces": ("cctp",),
        "motifs": [
            r"\bPUE\b[^.\n]{0,120}",
            r"\bWUE\b[^.\n]{0,120}",
            r"\btier\s*(?:i{1,3}v?|[1-4])\b[^.\n]{0,120}",
            r"disponibilit[ée][^.\n]{0,60}\d{2},?\d*\s*%",
        ],
        "pourquoi": "Une performance engagée sans méthode de preuve est une "
                    "clause invérifiable — pour vous comme pour l'acheteur.",
        "piege": "Un PUE engagé sans plan de comptage ni conditions de mesure "
                 "se retourne contre le titulaire : c'est à lui de démontrer "
                 "qu'il l'a tenu.",
    },
    {
        "cle": "variantes",
        "libelle": "Variantes et prestations supplémentaires",
        "pieces": ("rc",),
        "motifs": [
            r"variantes?[^.\n]{0,140}",
            r"prestations? suppl[ée]mentaires? [ée]ventuelles?[^.\n]{0,120}",
            r"\bPSE\b[^.\n]{0,100}",
        ],
        "pourquoi": "Une variante interdite et proposée quand même rend "
                    "l'offre irrégulière ; une variante autorisée et non "
                    "proposée est une occasion perdue.",
        "piege": "Une variante ne dispense jamais de remettre une offre de "
                 "base conforme.",
    },
    # LES CINQ RELEVÉS QUI OUVRENT TOUT FORMULAIRE. Le DC1, le DC2 et l'acte
    # d'engagement commencent tous les trois par les mêmes lignes : qui achète,
    # quoi, en combien de lots, selon quelle procédure, et où l'on dépose.
    # Aucun n'était relevé — ce module savait dire ce que la rubrique ATTEND et
    # n'avait rien à y mettre.
    #
    # LE GROUPE DE CAPTURE N'EST PAS UN DÉTAIL. Le motif cite la ligne entière
    # — « Objet du marché : maîtrise d'œuvre pour… » — et capture la partie qui
    # se recopie dans la case. La citation reste rendue avec sa position : ce
    # qui se recopie doit pouvoir se vérifier sur la pièce, et une valeur sans
    # sa phrase d'origine est une interprétation déguisée.
    {
        "cle": "acheteur",
        "libelle": "Acheteur — pouvoir adjudicateur ou maître d'ouvrage",
        "pieces": ("rc", "ae", "ccap"),
        "motifs": [
            # « acheteur » NU EST RETIRÉ, et c'est un défaut que l'essai a
            # montré : il attrapait « Profil d'acheteur : https://… » et
            # proposait une adresse web comme nom de pouvoir adjudicateur.
            r"(?:pouvoir adjudicateur|entit[ée] adjudicatrice|ma[îi]tre "
            r"d.?ouvrage|acheteur public)\s*:\s*([^.\n]{4,120})",
            r"(?:march[ée]|consultation) (?:public )?(?:lanc[ée]e? |pass[ée]e? )?"
            r"par\s+((?:la |le |l.)?[A-ZÉÈÀ][^.\n]{4,110})",
        ],
        "pourquoi": "C'est la première ligne du DC1 comme du DC2, et elle se "
                    "recopie à l'identique sur chaque pièce remise.",
        "piege": "L'acheteur qui SIGNE n'est pas toujours celui qui publie : "
                 "une centrale d'achat, un groupement de commandes ou un "
                 "mandataire de maîtrise d'ouvrage passe le marché pour le "
                 "compte d'un autre. C'est le nom du POUVOIR ADJUDICATEUR "
                 "qu'attend le formulaire.",
    },
    {
        "cle": "objet",
        "libelle": "Objet du marché",
        "pieces": ("rc", "ae", "cctp", "ccap"),
        "motifs": [
            # LE RETOUR À LA LIGNE N'EST PAS UNE FIN DE PHRASE. Un objet de
            # marché extrait d'un PDF est coupé par la mise en page, pas par
            # son auteur : s'arrêter au premier saut rendait « maîtrise
            # d'œuvre pour la construction d'un centre de données » là où la
            # phrase disait « … de 4 MW IT sur le site de la zone nord ». On
            # s'arrête au POINT, borné en longueur.
            r"objet (?:du (?:pr[ée]sent )?march[ée]|de la consultation)"
            r"\s*:?\s*([^.]{8,220})",
            r"le pr[ée]sent march[ée] a pour objet\s*:?\s*([^.]{8,220})",
            r"la pr[ée]sente consultation (?:a pour objet|porte sur)"
            r"\s*:?\s*([^.]{8,220})",
        ],
        "pourquoi": "Le DC1 demande l'objet de la consultation ET l'objet de "
                    "la candidature — marché entier, lot désigné, ou "
                    "prestation. Les deux se remplissent depuis cette ligne.",
        "piege": "L'objet du RC et celui du CCTP diffèrent parfois d'un mot "
                 "qui change le périmètre — « maîtrise d'œuvre » contre "
                 "« assistance à maîtrise d'ouvrage ». Le relevé les rend "
                 "tous les deux plutôt que d'en choisir un.",
    },
    {
        "cle": "lots",
        "libelle": "Allotissement",
        "pieces": ("rc",),
        "motifs": [
            r"(?:allotissement|d[ée]composition en lots)\s*:?\s*([^.\n]{4,160})",
            r"march[ée] (?:non )?alloti[^.\n]{0,120}",
            r"lot\s*n?[°o]?\s*\d{1,2}\s*[:–—-]\s*([^.\n]{4,120})",
        ],
        "pourquoi": "L'objet de la candidature au DC1 change selon qu'on "
                    "postule au marché entier ou à des lots désignés.",
        "piege": "Un candidat qui se déclare sur « le marché » alors que la "
                 "consultation est allotie ne postule à AUCUN lot. La case "
                 "des lots se coche, elle ne se déduit pas.",
    },
    {
        "cle": "procedure",
        "libelle": "Procédure de passation",
        "pieces": ("rc",),
        "motifs": [
            r"(proc[ée]dure\s+(?:adapt[ée]e|formalis[ée]e|n[ée]goci[ée]e|"
            r"avec n[ée]gociation|restreinte)(?:\s+ouverte)?)",
            r"(appel d.?offres?\s+(?:ouvert|restreint))",
            r"(dialogue comp[ée]titif)",
            r"(march[ée] (?:public )?global(?: de performance)?)",
        ],
        "pourquoi": "Elle décide de ce qui se remet en une fois et de ce qui "
                    "se remet en deux — candidature puis offre — et donc de "
                    "la composition du pli.",
        "piege": "En procédure restreinte, remettre l'offre avec la "
                 "candidature n'avance à rien et peut rompre l'égalité de "
                 "traitement. En procédure adaptée, l'inverse fait perdre.",
    },
    {
        "cle": "plateforme",
        "libelle": "Profil d'acheteur et modalités de dépôt",
        "pieces": ("rc",),
        "motifs": [
            # UNE ADRESSE NE SE COUPE PAS AU PREMIER POINT — « https://marches »
            # au lieu de « https://marches.vallee-agglo.fr/consultation/2026-014 »
            # est une adresse fausse, ce qui est pire qu'une case vide.
            r"(?:profil d.?acheteur|plate?[- ]?forme de d[ée]mat[ée]rialisation)"
            r"\s*:?\s*(https?://\S{6,150})",
            r"(https?://\S{8,150})",
            # Le repli en texte libre ne se déclenche PAS sur une adresse :
            # sinon il en rend une seconde, coupée au premier point.
            r"(?:profil d.?acheteur|plate?[- ]?forme de d[ée]mat[ée]rialisation)"
            # LE GARDE-FOU EST SUR LE DÉBUT DE LA CAPTURE, pas seulement
            # devant le séparateur : `\s*:?\s*` peut ne rien consommer, et le
            # moteur reculait jusqu'à faire commencer la valeur par « : », ce
            # qui rendait « https://marches » — une adresse fausse à côté de
            # la vraie.
            r"\s*:?\s*(?!https?://|:)([^\s.:][^.\n]{5,140})",
            r"d[ée]p[ôo]t\s+(?:des (?:plis|offres|candidatures)|"
            r"[ée]lectronique)[^.\n]{0,140}",
        ],
        "pourquoi": "Le dépôt se fait là et nulle part ailleurs, et l'horloge "
                    "qui fait foi est celle de cette plateforme.",
        "piege": "Un dépôt par courriel quand le RC impose le profil "
                 "d'acheteur est un pli non remis. Et le compte sur la "
                 "plateforme se crée AVANT le dernier jour : la validation "
                 "d'un certificat de signature prend parfois plusieurs jours.",
    },
    {
        "cle": "reference",
        "libelle": "Référence de la consultation",
        "pieces": ("rc", "ae", "ccap"),
        "motifs": [
            # SANS GROUPE DE CAPTURE, UN RELEVÉ NE PEUT REMPLIR AUCUNE CASE :
            # il cite et c'est tout. La référence est justement ce qui « se
            # reporte sur chaque pièce remise » — elle doit donc se recopier.
            r"(?:r[ée]f[ée]rence|n[°o]\s*(?:de\s*)?(?:march[ée]|consultation|"
            r"dossier))\s*:?\s*(?!:)([^\s.:][^.\n]{2,70})",
            r"(\b\d{4}[-_/]\d{2,4}[-_/][A-Z0-9]{2,10}\b)",
        ],
        "pourquoi": "À reporter sur chaque pièce remise : une pièce sans "
                    "référence se perd dans un dépôt dématérialisé.",
        "piege": "La référence du RC et celle de la plateforme diffèrent "
                 "parfois. Reportez les deux.",
    },
]


def _extraire(texte, motifs, maxi=4):
    """Les passages qui correspondent, avec leur position, sans doublon.

    LA POSITION EST RENDUE parce qu'un relevé sans repère ne se vérifie pas :
    « à 38 % du document » suffit à retrouver le passage dans un CCAP de
    quatre-vingts pages.
    """
    if not texte:
        return []
    out, vus = [], set()
    n = len(texte)
    for motif in motifs:
        for m in re.finditer(motif, texte, re.IGNORECASE):
            frag = " ".join(m.group(0).split())
            if len(frag) < 12:
                continue
            # DEUX CITATIONS QUI PROPOSENT LA MÊME VALEUR SONT UNE SEULE
            # PROPOSITION. La clé de dédoublonnage est la valeur quand il y en
            # a une : « Profil d'acheteur : https://x » et « https://x » sont
            # deux phrases et une seule adresse, et les rendre deux fois ferait
            # croire à deux plateformes.
            brut = None
            if m.groups() and m.group(1):
                brut = " ".join(m.group(1).split()).strip(" .:;,-–—")[:220]
            cle = (brut or frag[:80]).lower()
            if cle in vus:
                continue
            vus.add(cle)
            # LA VALEUR CAPTURÉE, QUAND LE MOTIF EN ISOLE UNE. Le premier
            # groupe est la partie qui se RECOPIE dans une case de formulaire ;
            # la citation entière reste rendue à côté, avec sa position. Une
            # valeur sans sa phrase d'origine est une interprétation déguisée,
            # et c'est exactement ce que ce module refuse.
            out.append({"texte": frag[:400],
                        "position": m.start(),
                        "part": round(100.0 * m.start() / n) if n else 0,
                        "valeur": brut or None})
            if len(out) >= maxi:
                return out
    return out


def relever(code_piece, texte):
    """Les points de vigilance relevés dans une pièce, citation par citation."""
    out = []
    for r in RELEVES:
        if code_piece not in r["pieces"]:
            continue
        trouves = _extraire(texte, r["motifs"])
        out.append({
            "cle": r["cle"], "libelle": r["libelle"],
            "pourquoi": r["pourquoi"], "piege": r["piege"],
            "trouve": bool(trouves), "citations": trouves,
            "note": None if trouves else (
                "Non trouvé dans cette pièce. Ce n'est pas « il n'y en a "
                "pas » : c'est « le relevé automatique ne l'a pas vu ». "
                "À lire à la main."),
        })
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  L'ANALYSE DU DOSSIER DÉPOSÉ
# ═══════════════════════════════════════════════════════════════════════════

def analyser(documents):
    """Le dossier de consultation, pièce par pièce, et ce qui manque.

    `documents` : une liste de dicts {nom, texte, extension}. Le texte peut
    être vide — un plan DWG n'en a pas — et la pièce est alors identifiée sur
    son seul nom, avec la confiance qui va avec.

    CE QUE CETTE FONCTION REND D'ESSENTIEL : `manquantes`. Un DCE sans CCAP ou
    sans règlement de consultation n'est pas un DCE, et c'est le genre de
    constat qu'on fait trois jours avant la remise si personne ne le fait le
    premier jour.
    """
    pieces, inconnues, presentes = [], [], set()
    for d in documents or []:
        nom = (d.get("nom") or d.get("filename") or "").strip()
        texte = d.get("texte") or ""
        ext = d.get("extension") or ("." + nom.rsplit(".", 1)[-1].lower()
                                     if "." in nom else "")
        ident = identifier(nom, texte, ext)
        ligne = {"fichier": nom, "identification": ident,
                 "octets_texte": len(texte)}
        if ident["reconnue"]:
            code = ident["code"]
            presentes.add(code)
            p = PIECES_MARCHE[code]
            ligne.update({
                "code": code, "piece": p["nom"], "sigle": p["sigle"],
                "rang_lecture": p["rang_lecture"],
                "contractuel": p["contractuel"],
                "engage": p["engage"], "chercher": p["chercher"],
                "piege": p["piege"],
                "releves": relever(code, texte),
            })
            if not texte:
                ligne["sans_texte"] = (
                    "Aucun texte n'a pu être extrait de ce fichier : les "
                    "points de vigilance n'ont pas pu y être cherchés. La "
                    "pièce est identifiée sur son nom seul.")
            pieces.append(ligne)
        else:
            ligne["pourquoi"] = ident.get("pourquoi", "")
            inconnues.append(ligne)

    pieces.sort(key=lambda l: l["rang_lecture"])
    manquantes = [{"code": c, "nom": p["nom"], "sigle": p["sigle"],
                   "ce_que_c_est": p["ce_que_c_est"],
                   "gravite": "bloquante" if p["obligatoire_dce"] else "à vérifier"}
                  for c, p in sorted(PIECES_MARCHE.items(),
                                     key=lambda kv: kv[1]["rang_lecture"])
                  if c not in presentes]
    return {
        "version": VERSION,
        "pieces": pieces,
        "inconnues": inconnues,
        "manquantes": manquantes,
        "alertes": _alertes(pieces, manquantes, inconnues),
        "ordre_lecture": [{"rang": p["rang_lecture"], "sigle": p["sigle"],
                           "nom": p["nom"]}
                          for p in sorted(PIECES_MARCHE.values(),
                                          key=lambda p: p["rang_lecture"])],
        "reserve": RESERVE_ANALYSE,
    }


RESERVE_ANALYSE = (
    "CE RELEVÉ NE REMPLACE PAS LA LECTURE DES PIÈCES. Il identifie les "
    "documents, cite les passages qu'il reconnaît et signale ce qui manque au "
    "dossier. Il ne comprend pas ce qu'il cite : un passage relevé peut être "
    "une clause abrogée, un renvoi, ou l'inverse de ce qu'il semble dire. "
    "Chaque citation porte sa position pour être vérifiée sur la pièce, et "
    "tout ce qui n'est pas trouvé est déclaré non trouvé plutôt que supposé "
    "absent.")


def _alertes(pieces, manquantes, inconnues):
    """Ce qui doit sauter aux yeux avant le reste.

    L'ORDRE EST CELUI DU RISQUE : ce qui rend l'offre irrecevable d'abord, ce
    qui coûte cher ensuite, ce qui demande une vérification en dernier.
    """
    a = []
    bloquantes = [m for m in manquantes if m["gravite"] == "bloquante"]
    if bloquantes:
        a.append({
            "niveau": "bloquante",
            "texte": "Pièce(s) essentielle(s) absente(s) du dossier déposé : "
                     + ", ".join(m["sigle"] for m in bloquantes)
                     + ". Sans elles, ni le délai, ni les critères, ni "
                       "l'étendue de l'engagement ne peuvent être établis.",
        })
    for p in pieces:
        for r in p.get("releves", []):
            if r["cle"] == "date_limite" and not r["trouve"]:
                a.append({"niveau": "bloquante",
                          "texte": "Aucune date limite de remise n'a été "
                                   "relevée dans le règlement de "
                                   "consultation. À lire à la main avant "
                                   "toute autre chose."})
            if r["cle"] == "penalites" and r["trouve"]:
                a.append({"niveau": "attention",
                          "texte": "Des clauses de pénalité ont été relevées "
                                   "au CCAP : vérifiez leur plafond avant de "
                                   "chiffrer."})
            if r["cle"] == "derogations" and r["trouve"]:
                a.append({"niveau": "attention",
                          "texte": "Des dérogations au CCAG ont été relevées : "
                                   "c'est là que le risque se déplace vers le "
                                   "titulaire."})
    if inconnues:
        a.append({
            "niveau": "verifier",
            "texte": "%d fichier(s) n'ont pas été reconnus. Ils ne sont pas "
                     "rangés au plus proche : ouvrez-les." % len(inconnues),
        })
    for p in pieces:
        if p["identification"]["confiance"] == "faible":
            a.append({
                "niveau": "verifier",
                "texte": "« %s » est identifié comme %s avec une confiance "
                         "faible. Vérifiez avant de vous fier au relevé."
                         % (p["fichier"], p["sigle"]),
            })
    rang = {"bloquante": 0, "attention": 1, "verifier": 2}
    a.sort(key=lambda x: rang.get(x["niveau"], 9))
    # Une même alerte peut naître de deux pièces ; on ne la dit qu'une fois.
    vues, out = set(), []
    for x in a:
        if x["texte"] in vues:
            continue
        vues.add(x["texte"])
        out.append(x)
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  3. LE DOSSIER DE CANDIDATURE
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE LA TABLE EST. La composition du dossier de candidature demandée par
# les acheteurs publics, pièce par pièce, avec ce que chacune doit contenir et
# la faute qui la fait écarter. Elle sert deux fois : à la relecture avant
# dépôt, et à la génération des notes rédigées.
#
# TROIS NATURES DE PIÈCES, ET ELLES NE SE PRODUISENT PAS PAREIL :
#   · `formulaire` — un imprimé à remplir (DC1, DC2). Le module dit ce
#     qu'attend chaque rubrique ; il ne remplit rien ;
#   · `justificatif` — une pièce à OBTENIR d'un tiers (attestations, pouvoirs,
#     certifications). Elle a un délai d'obtention, et c'est ce délai qui fait
#     rater des dépôts ;
#   · `note` — un texte à RÉDIGER. Celles-là se génèrent, et le module dit ce
#     qu'elles doivent démontrer.
#
# LA COLONNE `bloquant` DIT CE QUI REND LA CANDIDATURE IRRECEVABLE. Tout n'est
# pas au même niveau, et traiter les seize pièces avec la même urgence revient
# à n'en traiter aucune correctement.

# ── DEUX FAMILLES, ET ELLES NE SE PRÉPARENT PAS PAREIL ────────────────────
# CE QUE LA DISTINCTION APPORTE, ET QUI N'EST PAS COSMÉTIQUE. Un règlement de
# consultation sépare presque toujours les pièces qui établissent QUI VOUS ÊTES
# de celles qui établissent CE QUE VOUS SAVEZ FAIRE — et ce ne sont ni les
# mêmes personnes, ni les mêmes délais, ni les mêmes risques. L'administratif
# se rassemble : il existe déjà quelque part, ou il s'obtient d'un tiers. Le
# technique s'écrit : il n'existe nulle part avant qu'on l'écrive.
#
# LE PIÈGE QUE CETTE SÉPARATION ÉVITE. Traiter les quatorze pièces d'un seul
# tenant fait commencer par les formulaires — ils sont courts, ils rassurent —
# et laisse pour la fin les notes techniques, qui sont ce qui départage les
# candidats et ce qui prend le plus de temps.

FAMILLES_PIECE = {
    "administratif": {
        "nom": "Pièces administratives",
        "etablit": "Qui vous êtes, et que vous avez le droit de contracter.",
        "qui": "Direction juridique, secrétariat général, expert-comptable.",
        "piege": "Rien ne s'y invente et rien ne s'y rattrape : une attestation "
                 "périmée ou une délégation incomplète fait écarter une "
                 "candidature par ailleurs excellente.",
    },
    "technique": {
        "nom": "Pièces techniques et de capacité",
        "etablit": "Ce que vous savez faire, avec qui, et l'avez déjà fait.",
        "qui": "Direction technique, responsables de mission, RH.",
        "piege": "C'est là que se joue la note, et c'est ce qu'on écrit en "
                 "dernier. Une note d'équipe rédigée la veille se lit comme "
                 "une note d'équipe rédigée la veille.",
    },
}

# ── TROIS VOIES DE PRODUCTION, ET UNE SEULE PASSE PAR CE MODULE ───────────
# La voie n'est pas la nature : elle dit ce que VOUS avez à faire du document,
# ici et maintenant. Le module ne remplit que la première.

VOIES = {
    "remplir": {
        "nom": "Se remplit ici",
        "aide": "Ses rubriques factuelles se reportent depuis votre fiche et "
                "depuis le dossier de consultation analysé. Ses déclarations, "
                "elles, restent à signer.",
    },
    "rediger": {
        "nom": "À rédiger",
        "aide": "Un texte qui n'existe nulle part avant qu'on l'écrive. Ce "
                "module dit ce qu'il doit démontrer ; il ne l'écrit pas à "
                "votre place.",
    },
    "obtenir": {
        "nom": "À obtenir",
        "aide": "Une pièce délivrée par un tiers. Elle a un DÉLAI, et c'est ce "
                "délai — pas la rédaction — qui fait rater les dépôts.",
    },
}


def voie(cle_piece, nature):
    """Ce qu'il y a à FAIRE de cette pièce : la remplir, l'écrire, l'obtenir.

    LA VOIE SE DÉDUIT, ELLE NE SE DÉCLARE PAS. Écrite à la main sur chaque
    pièce, elle dirait « se remplit ici » le jour où l'on retirerait ses
    rubriques — et le menu proposerait un document que rien ne remplit.
    """
    if cle_piece in RUBRIQUES:
        return "remplir"
    return "obtenir" if nature == "justificatif" else "rediger"


DOSSIER_CANDIDATURE = [
    {
        "cle": "dc1", "famille": "administratif",
        "nom": "Lettre de candidature — formulaire DC1",
        "nature": "formulaire",
        "bloquant": True,
        "produit_par": "Le candidat, ou le mandataire pour le groupement.",
        "contient": [
            "Identification de l'acheteur et objet de la consultation",
            "Objet de la candidature — marché entier, lot(s), ou "
            "prestation(s) désignée(s)",
            "Présentation du candidat : individuel ou groupement, forme du "
            "groupement",
            "Identification des membres du groupement et répartition des "
            "prestations entre eux",
            "Engagements du candidat individuel ou de chaque membre du "
            "groupement",
            "Désignation du mandataire et étendue de son habilitation",
        ],
        "piege": "La répartition des prestations entre cotraitants inscrite "
                 "ici engage le groupement. Elle doit correspondre exactement "
                 "à la note de répartition des compétences et au tableau de "
                 "répartition des honoraires — trois documents qui disent "
                 "souvent trois choses différentes.",
        "delai": None,
    },
    {
        "cle": "dc2", "famille": "administratif",
        "nom": "Déclaration du candidat — formulaire DC2",
        "nature": "formulaire",
        "bloquant": True,
        "produit_par": "Chaque membre du groupement, un formulaire par "
                       "membre.",
        "contient": [
            "Identification de l'acheteur et objet de la consultation",
            "Identification du candidat individuel ou du membre du groupement",
            "Aptitude à exercer l'activité professionnelle — inscriptions et "
            "immatriculations",
            "Capacité économique et financière — chiffres d'affaires des "
            "exercices demandés",
            "Capacité technique et professionnelle — moyens, effectifs, "
            "références",
            "Capacités des opérateurs économiques sur lesquels le candidat "
            "s'appuie, et engagement de ces opérateurs",
        ],
        "piege": "Un candidat qui s'appuie sur les capacités d'un tiers doit "
                 "produire l'ENGAGEMENT de ce tiers, pas seulement le citer. "
                 "Sans cet engagement, la capacité invoquée ne compte pas.",
        "delai": None,
    },
    {
        "cle": "pouvoirs", "famille": "administratif",
        "nom": "Pouvoirs des personnes habilitées à engager",
        "nature": "justificatif",
        "bloquant": True,
        "produit_par": "Chaque membre du groupement, depuis ses statuts ou "
                       "une délégation.",
        "contient": [
            "Délégation de pouvoir ou de signature, à jour",
            "Extrait des statuts ou du registre du commerce désignant le "
            "représentant légal",
            "Chaîne complète quand la signature est déléguée en cascade",
        ],
        "piege": "Une délégation périmée ou incomplète fait écarter une "
                 "candidature par ailleurs excellente. La chaîne doit être "
                 "COMPLÈTE : du représentant légal au signataire, sans "
                 "maillon manquant.",
        "delai": "Quelques jours si la délégation existe ; plusieurs semaines "
                 "s'il faut la faire signer.",
    },
    {
        "cle": "tiers", "famille": "administratif",
        "nom": "Formulaire d'évaluation des tiers de l'acheteur",
        "nature": "formulaire",
        "bloquant": True,
        "produit_par": "Chaque membre du groupement.",
        "contient": [
            "Le formulaire propre à l'acheteur, dans SA version et SON format",
            "Les informations d'intégrité, de conformité et de sous-traitance "
            "qu'il demande",
        ],
        "piege": "C'est une pièce PROPRE à l'acheteur : il n'y a pas de "
                 "modèle national, et un formulaire d'une autre consultation "
                 "ne convient pas. Elle est souvent citée au règlement de "
                 "consultation et oubliée parce qu'elle ne ressemble à rien "
                 "de connu.",
        "delai": None,
    },
    {
        "cle": "honneur", "famille": "administratif",
        "nom": "Déclaration sur l'honneur — absence d'interdiction de "
               "soumissionner",
        "nature": "formulaire",
        "bloquant": True,
        "produit_par": "Chaque membre du groupement, sous la signature d'une "
                       "personne habilitée.",
        "contient": [
            "L'absence des interdictions de soumissionner obligatoires "
            "prévues aux articles L. 2141-1 à L. 2141-5 du code de la "
            "commande publique",
            "L'absence des interdictions de soumissionner facultatives "
            "prévues aux articles L. 2141-7 à L. 2141-11 du même code",
            "La régularité de la situation au regard des obligations "
            "fiscales et sociales",
        ],
        "piege": "Elle est intégrée au DC1 dans sa version courante — la "
                 "produire deux fois ne nuit pas, l'omettre parce qu'« elle "
                 "est dans le DC1 » quand le règlement la demande à part "
                 "fait écarter la candidature. Sa fausseté est sanctionnée : "
                 "elle se signe en connaissance de cause.",
        "delai": None,
    },
    {
        "cle": "repartition_competences", "famille": "technique",
        "nom": "Note de répartition des compétences en groupement",
        "nature": "note",
        "bloquant": False,
        "produit_par": "Le mandataire, avec l'accord de chaque cotraitant.",
        "contient": [
            "Le périmètre de prestation de chaque cotraitant, par phase et "
            "par discipline",
            "Les interfaces entre cotraitants et la façon dont elles sont "
            "arbitrées",
            "Le rôle du mandataire et l'étendue de sa solidarité",
            "La cohérence avec la répartition inscrite au DC1",
        ],
        "piege": "Une répartition qui laisse une tâche à personne ou à deux "
                 "se voit à la lecture, et l'évaluateur en déduit — souvent "
                 "à raison — que le groupement s'est constitué la semaine du "
                 "dépôt.",
        "delai": None,
    },
    {
        "cle": "conventions", "famille": "administratif",
        "nom": "Note sur les conventions collectives applicables",
        "nature": "note",
        "bloquant": False,
        "produit_par": "Chaque membre du groupement.",
        "contient": [
            "La ou les conventions collectives dont relèvent les personnels "
            "affectés à la mission",
            "Leur incidence sur les conditions d'emploi des intervenants",
            "Le traitement des intervenants relevant de conventions "
            "différentes au sein du groupement",
        ],
        "piege": "Elle passe pour une formalité et n'en est pas une : c'est "
                 "par elle qu'un acheteur vérifie que les taux horaires "
                 "annoncés sont compatibles avec les qualifications "
                 "affichées.",
        "delai": None,
    },
    {
        "cle": "equipe", "famille": "technique",
        "nom": "Note de présentation de l'équipe",
        "nature": "note",
        "bloquant": False,
        "produit_par": "Le mandataire.",
        "contient": [
            "La composition de l'équipe rapportée aux besoins de la mission",
            "L'adéquation de chaque profil aux prestations qui lui sont "
            "confiées",
            "La disponibilité des intervenants sur la durée du marché",
            "Les moyens de remplacement en cas d'indisponibilité",
        ],
        "piege": "Présenter des experts qui n'interviendront pas. "
                 "L'engagement porte sur les personnes nommées : un "
                 "remplacement non prévu au dossier se négocie en cours de "
                 "marché, et rarement en votre faveur.",
        "delai": None,
    },
    {
        "cle": "organigramme", "famille": "technique",
        "nom": "Organigramme fonctionnel de la mission",
        "nature": "note",
        "bloquant": False,
        "produit_par": "Le mandataire.",
        "contient": [
            "Le mandataire et son représentant",
            "L'interlocuteur principal du maître d'ouvrage, nommément désigné",
            "Les responsables par discipline et par phase",
            "Les liens hiérarchiques et fonctionnels, et qui décide en cas "
            "de désaccord entre disciplines",
        ],
        "piege": "Un organigramme sans point de décision unique. Le maître "
                 "d'ouvrage veut savoir qui il appelle, et qui tranche quand "
                 "deux bureaux d'études du groupement ne sont pas d'accord.",
        "delai": None,
    },
    {
        "cle": "cv", "famille": "technique",
        "nom": "Curriculum vitae des intervenants clés",
        "nature": "justificatif",
        "bloquant": False,
        "produit_par": "Chaque membre, pour ses intervenants nommés.",
        "contient": [
            "La formation et l'expérience, rapportées à la mission confiée",
            "Les références personnelles de l'intervenant, distinctes de "
            "celles de son employeur",
            "Le rôle tenu sur chaque référence citée",
        ],
        "piege": "Un CV qui reprend les références de l'entreprise au lieu de "
                 "celles de la personne. L'évaluateur cherche ce que CETTE "
                 "personne a fait, et le distingue sans difficulté.",
        "delai": None,
    },
    {
        "cle": "atd_atp", "famille": "administratif",
        "nom": "Justificatifs d'aptitude technique et professionnelle "
               "(ATD / ATP)",
        "nature": "justificatif",
        "bloquant": False,
        "produit_par": "Chaque membre concerné, auprès de l'organisme "
                       "délivrant.",
        "contient": [
            "Les attestations en cours de validité, dans le domaine demandé",
            "La correspondance entre le domaine de l'attestation et l'objet "
            "de la consultation",
        ],
        "piege": "La date de validité. Une attestation qui expire entre la "
                 "remise et l'attribution se remplace mal, et le "
                 "renouvellement prend des semaines.",
        "delai": "Plusieurs semaines en cas de renouvellement ou de première "
                 "demande.",
    },
    {
        "cle": "references", "famille": "technique",
        "nom": "Références — six au minimum",
        "nature": "note",
        "bloquant": True,
        "produit_par": "Chaque membre, pour son périmètre.",
        "contient": [
            "Six références au moins, comparables en nature et en taille",
            "Pour chacune : le maître d'ouvrage, l'objet, le montant, la "
            "période, la mission tenue et le résultat",
            "La part réellement tenue par le candidat quand la référence est "
            "un groupement",
            "Les attestations de bonne exécution quand elles sont demandées",
        ],
        "piege": "Compter une référence de groupement comme une référence "
                 "propre. Il faut dire ce qu'on y a fait ; un évaluateur qui "
                 "reconnaît l'opération et n'y retrouve pas le candidat "
                 "écarte la référence entière.",
        "delai": "Les attestations de bonne exécution se demandent aux "
                 "anciens clients : comptez plusieurs semaines.",
    },
    {
        "cle": "moyens", "famille": "technique",
        "nom": "Note sur les moyens, procédures et outils",
        "nature": "note",
        "bloquant": False,
        "produit_par": "Le mandataire, avec la contribution de chaque "
                       "cotraitant.",
        "contient": [
            "Les moyens de coordination et de pilotage : instances, "
            "périodicité, comptes rendus, tableaux de bord",
            "Le partage documentaire : plateforme, arborescence, "
            "nomenclature, indices, droits d'accès",
            "Le contrôle des études : qui vérifie quoi, à quel moment, et "
            "comment la vérification est tracée",
            "Les outils employés, et leur compatibilité avec ceux du maître "
            "d'ouvrage",
        ],
        "piege": "Décrire des outils sans dire ce qu'ils PRODUISENT. Un "
                 "acheteur ne juge pas le nom de la plateforme : il juge "
                 "s'il recevra un document indexé, à jour, et si le contrôle "
                 "interne laisse une trace vérifiable.",
        "delai": None,
    },
    {
        "cle": "qse", "famille": "technique",
        "nom": "Note sur la démarche qualité, sécurité et environnement",
        "nature": "note",
        "bloquant": False,
        "produit_par": "Chaque membre, ou le mandataire pour le groupement.",
        "contient": [
            "Le système de management de la qualité et son périmètre réel",
            "La démarche sécurité, et son application aux interventions sur "
            "site en exploitation",
            "La démarche environnementale, et ce qu'elle change dans les "
            "études — pas seulement dans le fonctionnement du bureau",
            "Les certifications détenues, avec leur périmètre exact, leur "
            "organisme et leur date de validité",
        ],
        "piege": "Joindre un certificat dont le périmètre ne couvre pas "
                 "l'activité concernée, ou l'entité qui exécutera. Le "
                 "périmètre est écrit sur le certificat, et il est lu.",
        "delai": None,
    },
]

NATURES_PIECE = {
    "formulaire": {
        "nom": "Formulaire à remplir",
        "aide": "Un imprimé dont les rubriques sont fixées. Ce module dit ce "
                "que chaque rubrique attend ; il ne remplit rien et ne "
                "déclare rien — ces formulaires portent des déclarations dont "
                "la fausseté est sanctionnée.",
    },
    "justificatif": {
        "nom": "Justificatif à obtenir",
        "aide": "Une pièce délivrée par un tiers. Elle a un DÉLAI "
                "d'obtention, et c'est ce délai — pas la rédaction — qui fait "
                "rater les dépôts.",
    },
    "note": {
        "nom": "Note à rédiger",
        "aide": "Un texte à écrire, qui se génère à partir du dossier de "
                "consultation et de la base de connaissance, puis se relit et "
                "s'assume.",
    },
}


def plan_reponse(analyse=None, groupement=False):
    """Le dossier de candidature à produire, dans l'ordre où on s'y prend.

    L'ORDRE N'EST PAS CELUI DE LA LISTE DU RÈGLEMENT DE CONSULTATION, et c'est
    le point : on commence par ce qui a un DÉLAI D'OBTENTION, parce que c'est
    la seule chose qu'on ne peut pas rattraper la dernière nuit. Les notes à
    rédiger viennent ensuite, les formulaires en dernier — ils se remplissent
    vite dès lors que le reste existe.

    `groupement` ajoute à chaque pièce ce qu'elle devient en groupement :
    plusieurs exemplaires, une cohérence à tenir entre eux, et un mandataire
    qui répond de l'ensemble.
    """
    ordre = {"justificatif": 0, "note": 1, "formulaire": 2}
    out = []
    for p in DOSSIER_CANDIDATURE:
        e = dict(p)
        e["nature_nom"] = NATURES_PIECE[p["nature"]]["nom"]
        e["nature_aide"] = NATURES_PIECE[p["nature"]]["aide"]
        e["rang"] = (ordre[p["nature"]], 0 if p["bloquant"] else 1, p["nom"])
        if groupement:
            e["en_groupement"] = _groupement(p)
        out.append(e)
    out.sort(key=lambda e: e["rang"])
    for e in out:
        e.pop("rang", None)
    return {
        "version": VERSION,
        "pieces": out,
        "natures": NATURES_PIECE,
        "bloquantes": [p["nom"] for p in DOSSIER_CANDIDATURE if p["bloquant"]],
        "avec_delai": [{"nom": p["nom"], "delai": p["delai"]}
                       for p in DOSSIER_CANDIDATURE if p.get("delai")],
        "note": NOTE_REPONSE,
        "consultation": _rappel_consultation(analyse),
    }


def _groupement(p):
    """Ce que la pièce devient quand on répond en groupement."""
    if p["cle"] == "dc1":
        return ("Un seul DC1 pour le groupement, rempli par le mandataire, "
                "avec la répartition des prestations entre tous les membres "
                "et la désignation du mandataire.")
    if p["cle"] in ("dc2", "honneur", "tiers"):
        return ("Un exemplaire PAR MEMBRE du groupement. L'oubli d'un seul "
                "membre rend la candidature incomplète pour tous.")
    if p["cle"] == "pouvoirs":
        return ("Les pouvoirs de chaque membre, ET l'habilitation du "
                "mandataire à représenter le groupement.")
    if p["cle"] == "references":
        return ("Les références de chaque membre, sur SON périmètre. Une "
                "référence portée au crédit du groupement entier sans dire "
                "qui a fait quoi ne compte pour personne.")
    return ("À produire pour le groupement, sous la responsabilité du "
            "mandataire, en cohérence avec la répartition inscrite au DC1.")


NOTE_REPONSE = (
    "CE PLAN NE SIGNE RIEN. Les formulaires de candidature portent des "
    "déclarations dont la fausseté est sanctionnée : elles se signent par une "
    "personne habilitée, après vérification. Ce module dit ce que chaque "
    "rubrique attend et dans quel ordre s'y prendre — il ne déclare, "
    "n'atteste et n'engage rien. La liste des pièces réellement exigées est "
    "celle du règlement de consultation de VOTRE consultation, et elle "
    "l'emporte sur celle-ci.")


def _rappel_consultation(analyse):
    """Ce que l'analyse du DCE a relevé et qui commande la réponse.

    DEUX POINTS SEULEMENT — la date limite et les critères —, parce que ce
    sont les deux qui décident de la façon de répondre. Les recopier tous
    ferait un second rapport là où on veut un rappel.
    """
    if not analyse:
        return None
    out = {}
    for p in analyse.get("pieces", []):
        for r in p.get("releves", []):
            if r["cle"] in ("date_limite", "criteres") and r["trouve"]:
                out.setdefault(r["cle"], {
                    "libelle": r["libelle"], "source": p["fichier"],
                    "citations": r["citations"]})
    if not out:
        return {"note": ("Ni date limite ni critères de jugement n'ont été "
                        "relevés dans le dossier déposé. Les lire au "
                        "règlement de consultation avant de commencer : ils "
                        "commandent l'ordre et l'effort.")}
    return out


def referentiel():
    """Les tables, sans analyse — pour la page et la documentation."""
    return {
        "version": VERSION,
        "pieces_marche": PIECES_MARCHE,
        "releves": [{k: v for k, v in r.items() if k != "motifs"}
                    for r in RELEVES],
        "dossier_candidature": DOSSIER_CANDIDATURE,
        "natures_piece": NATURES_PIECE,
        "champs_candidat": CHAMPS_CANDIDAT,
        "groupes_fiche": GROUPES_FICHE,
        "rubriques": RUBRIQUES,
        "statuts": STATUTS,
        "note_remplissage": NOTE_REMPLISSAGE,
        "note_reponse": NOTE_REPONSE,
        "reserve_analyse": RESERVE_ANALYSE,
        "glossaire": glossaire(),
    }


def glossaire():
    """Les familles d'infobulles servies par ce module."""
    return {
        "piece_marche": {k: {
            "nom": "%s — %s" % (v["sigle"], v["nom"]),
            "aide": ("%s\n\nCe qu'elle engage — %s\n\nCe qu'il faut y chercher "
                     "— %s\n\nLe piège — %s"
                     % (v["ce_que_c_est"], v["engage"], v["chercher"],
                        v["piege"])),
        } for k, v in PIECES_MARCHE.items()},
        "piece_candidature": {p["cle"]: {
            "nom": p["nom"],
            "aide": ("%s\n\nProduite par — %s\n\nCe qu'elle doit contenir :\n"
                     "· %s\n\nLe piège — %s%s"
                     % (NATURES_PIECE[p["nature"]]["aide"], p["produit_par"],
                        "\n· ".join(p["contient"]), p["piege"],
                        ("\n\nDélai d'obtention — " + p["delai"])
                        if p.get("delai") else "")),
        } for p in DOSSIER_CANDIDATURE},
    }


# ═══════════════════════════════════════════════════════════════════════════
#  4. LA FICHE DU CANDIDAT, ET LE REMPLISSAGE DES PIÈCES
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE CETTE PARTIE FAIT, ET CE QU'ELLE NE FERA JAMAIS.
#
# Elle remplit les cases FACTUELLES du dossier de candidature : celles dont la
# réponse est déjà écrite quelque part — dans la fiche du candidat, saisie une
# fois, ou dans le dossier de consultation, relevé à l'instant. Une raison
# sociale, un SIRET, un objet de marché, une date limite ne se devinent pas :
# ils se recopient. Les recopier à la main sur quatorze pièces est le travail
# qui produit les fautes de cohérence dont les candidatures meurent.
#
# ELLE NE PRÉ-REMPLIT AUCUNE DÉCLARATION, et ce n'est pas une prudence
# d'affichage. Les DC1, DC2 et déclarations sur l'honneur portent des
# affirmations — ne pas entrer dans un cas d'exclusion, être à jour de ses
# obligations fiscales et sociales, ne pas être en situation de conflit
# d'intérêts — dont la fausseté est sanctionnée pénalement. Une case cochée
# par un programme est une déclaration que personne n'a faite. Ces rubriques
# ressortent donc au statut `a_declarer`, avec LE TEXTE EXACT de ce qui est
# affirmé, et elles restent vides jusqu'à ce qu'une personne habilitée les
# assume.
#
# TOUTE VALEUR PORTE SON ORIGINE. Trois origines, et elles ne s'équivalent
# pas : `fiche` (vous l'avez saisie), `consultation` (relevée dans telle pièce,
# à tel endroit, avec la citation), `calcul` (déduite d'une autre valeur par
# une règle nommée). Une valeur sans origine se recopie sans se relire, et
# c'est ainsi qu'un SIRET d'une autre filiale finit sur un DC2.

CHAMPS_CANDIDAT = [
    {"cle": "raison_sociale", "nom": "Dénomination sociale", "groupe": "identite",
     "ou": "Extrait Kbis, ligne « Dénomination ». Le nom commercial n'est pas "
           "la dénomination sociale, et c'est la dénomination qui engage."},
    {"cle": "forme_juridique", "nom": "Forme juridique", "groupe": "identite",
     "ou": "Extrait Kbis. SAS, SARL, SA, SCOP, EURL, société d'exercice "
           "libéral…"},
    {"cle": "siret", "nom": "SIRET de l'établissement", "groupe": "identite",
     "format": "siret",
     "ou": "Extrait Kbis ou avis de situation INSEE. Quatorze chiffres : les "
           "neuf du SIREN, puis les cinq du numéro interne de "
           "l'établissement. C'est le SIRET de L'ÉTABLISSEMENT qui exécutera "
           "le marché, pas celui du siège s'ils diffèrent."},
    {"cle": "capital", "nom": "Capital social", "groupe": "identite",
     "ou": "Extrait Kbis. En euros."},
    {"cle": "rcs", "nom": "Ville d'immatriculation au RCS", "groupe": "identite",
     "ou": "Extrait Kbis, greffe d'immatriculation."},
    {"cle": "naf", "nom": "Code NAF / APE", "groupe": "identite",
     "ou": "Avis de situation INSEE. Quatre chiffres et une lettre."},
    {"cle": "adresse", "nom": "Adresse du siège", "groupe": "identite",
     "ou": "Extrait Kbis."},
    {"cle": "code_postal", "nom": "Code postal", "groupe": "identite"},
    {"cle": "ville", "nom": "Ville", "groupe": "identite"},
    {"cle": "telephone", "nom": "Téléphone", "groupe": "contact"},
    {"cle": "courriel", "nom": "Courriel de la personne à contacter",
     "groupe": "contact",
     "ou": "L'adresse à laquelle l'acheteur écrira. Une boîte partagée vaut "
           "mieux qu'une adresse personnelle : les demandes de compléments "
           "arrivent avec un délai de réponse de quelques jours."},
    {"cle": "representant_nom", "nom": "Nom du représentant habilité",
     "groupe": "signature",
     "ou": "Celui qui SIGNE. Représentant légal au Kbis, ou titulaire d'une "
           "délégation de signature — auquel cas la délégation est jointe."},
    {"cle": "representant_qualite", "nom": "Qualité du signataire",
     "groupe": "signature",
     "ou": "Président, gérant, directeur général, directeur délégué… telle "
           "qu'elle figure sur le Kbis ou la délégation."},
    {"cle": "effectif", "nom": "Effectif moyen annuel", "groupe": "capacites",
     "ou": "Bilan social ou déclaration sociale nominative. Le DC2 demande "
           "l'effectif des trois derniers exercices ; renseignez le dernier "
           "et tenez les deux autres prêts."},
    {"cle": "ca_n1", "nom": "Chiffre d'affaires — dernier exercice clos",
     "groupe": "capacites", "ou": "Liasse fiscale. En euros hors taxes."},
    {"cle": "ca_n2", "nom": "Chiffre d'affaires — exercice N-2",
     "groupe": "capacites", "ou": "Liasse fiscale. En euros hors taxes."},
    {"cle": "ca_n3", "nom": "Chiffre d'affaires — exercice N-3",
     "groupe": "capacites", "ou": "Liasse fiscale. En euros hors taxes."},
    {"cle": "assurance_compagnie", "nom": "Assureur responsabilité civile "
     "professionnelle", "groupe": "assurances"},
    {"cle": "assurance_police", "nom": "Numéro de police",
     "groupe": "assurances"},
    {"cle": "assurance_echeance", "nom": "Échéance de la police",
     "groupe": "assurances",
     "ou": "L'attestation doit couvrir la PÉRIODE D'EXÉCUTION du marché, pas "
           "la date de remise du pli. Une police qui expire pendant le marché "
           "est un motif de rejet."},
]

GROUPES_FICHE = [
    ("identite", "Identité de l'entreprise"),
    ("contact", "Contact"),
    ("signature", "Signataire"),
    ("capacites", "Capacités économiques"),
    ("assurances", "Assurances"),
]


# ── LES CONTRÔLES DE FORME ─────────────────────────────────────────────────
# UN CONTRÔLE NE VALIDE PAS UNE VALEUR, IL ÉCARTE UNE FAUTE DE FRAPPE. Un
# SIRET syntaxiquement juste peut être celui d'une autre société ; un SIRET
# faux, lui, est faux à coup sûr, et il vaut mieux l'apprendre ici que dans la
# lettre de rejet.

def _luhn(chiffres):
    """La clé de contrôle des SIREN et SIRET (algorithme de Luhn)."""
    total, pair = 0, False
    for c in reversed(chiffres):
        n = ord(c) - 48
        if pair:
            n *= 2
            if n > 9:
                n -= 9
        total += n
        pair = not pair
    return total % 10 == 0


def controler(cle, valeur):
    """(valide, message) — le message dit CE QUI cloche, pas « invalide »."""
    v = re.sub(r"[\s.-]", "", str(valeur or ""))
    if cle == "siret":
        if not v.isdigit():
            return False, "Un SIRET ne contient que des chiffres."
        if len(v) != 14:
            return False, ("Un SIRET compte quatorze chiffres ; celui-ci en "
                           "compte %d." % len(v))
        if not _luhn(v):
            # LA POSTE EST L'EXCEPTION CONNUE, et la nommer évite de faire
            # corriger un numéro juste : ses établissements ne satisfont pas la
            # clé de Luhn. MAIS L'EXCEPTION A SA PROPRE RÈGLE — la somme des
            # quatorze chiffres est un multiple de cinq — et l'ignorer
            # accepterait n'importe quel numéro commençant par 356000000, y
            # compris une faute de frappe. Une exception sans règle n'est pas
            # une exception, c'est un trou.
            if v.startswith("356000000"):
                if sum(ord(c) - 48 for c in v) % 5 == 0:
                    return True, None
                return False, ("Numéro de La Poste : la somme de ses quatorze "
                               "chiffres doit être un multiple de cinq, et "
                               "elle ne l'est pas.")
            return False, ("La clé de contrôle ne tombe pas juste : il y a une "
                           "faute de frappe dans ce numéro.")
        return True, None
    return True, None


def derive(fiche):
    """Ce qui se déduit d'une valeur saisie, par une règle NOMMÉE.

    DÉDUIRE N'EST PAS INVENTER, à une condition : que la règle soit écrite et
    vérifiable. Le SIREN sont les neuf premiers chiffres du SIRET ; la clé du
    numéro de TVA intracommunautaire est (12 + 3 × (SIREN mod 97)) mod 97.
    Ces deux-là se déduisent. Le reste se saisit.
    """
    out = {}
    siret = re.sub(r"[\s.-]", "", str((fiche or {}).get("siret") or ""))
    if len(siret) == 14 and siret.isdigit():
        siren = siret[:9]
        out["siren"] = {"valeur": siren,
                        "regle": "Les neuf premiers chiffres du SIRET."}
        cle = (12 + 3 * (int(siren) % 97)) % 97
        out["tva"] = {"valeur": "FR%02d%s" % (cle, siren),
                      "regle": "FR, puis la clé (12 + 3 × (SIREN mod 97)) "
                               "mod 97, puis le SIREN."}
    return out


# ── LES RUBRIQUES DE CHAQUE PIÈCE, ET D'OÙ VIENT CHACUNE ───────────────────
# QUATRE SOURCES, ET ELLES NE S'ÉQUIVALENT PAS :
#   · `fiche`        — vous l'avez saisie une fois, elle se recopie partout ;
#   · `consultation` — relevée dans le dossier déposé, avec sa citation et sa
#                      position, pour être vérifiée sur la pièce ;
#   · `calcul`       — déduite par une règle nommée (SIREN, numéro de TVA) ;
#   · `saisie`       — propre à CETTE consultation : elle ne va pas dans la
#                      fiche, elle se décide ici (les lots visés, la forme du
#                      groupement) ;
#   · `declaration`  — ce qui s'affirme sous peine de sanction. JAMAIS
#                      pré-remplie, et le texte exact de ce qui est affirmé est
#                      rendu pour être lu avant d'être assumé.
#
# LE TEXTE D'UNE DÉCLARATION N'EST PAS RÉÉCRIT ICI : il est repris mot pour mot
# de ce que la pièce dit contenir, et une règle refuse qu'il en diverge. Deux
# rédactions de la même déclaration finiraient par ne plus dire la même chose.

RUBRIQUES = {
    "dc1": [
        {"cle": "acheteur", "libelle": "Identification de l'acheteur",
         "source": "consultation", "releve": "acheteur"},
        {"cle": "objet_consultation", "libelle": "Objet de la consultation",
         "source": "consultation", "releve": "objet"},
        {"cle": "reference", "libelle": "Référence de la consultation",
         "source": "consultation", "releve": "reference"},
        {"cle": "objet_candidature",
         "libelle": "Objet de la candidature — marché entier, lot(s) ou "
                    "prestation(s) désignée(s)",
         "source": "saisie",
         "aide": "À décider au vu de l'allotissement relevé. Un candidat qui "
                 "se déclare sur « le marché » alors que la consultation est "
                 "allotie ne postule à AUCUN lot."},
        {"cle": "candidat", "libelle": "Dénomination du candidat",
         "source": "fiche", "champ": "raison_sociale"},
        {"cle": "forme", "libelle": "Forme juridique",
         "source": "fiche", "champ": "forme_juridique"},
        {"cle": "siret", "libelle": "SIRET", "source": "fiche", "champ": "siret"},
        {"cle": "adresse", "libelle": "Adresse", "source": "fiche",
         "champ": "adresse"},
        {"cle": "forme_groupement",
         "libelle": "Candidat individuel ou groupement, et forme du groupement",
         "source": "saisie",
         "aide": "La forme imposée ou admise est relevée au règlement de "
                 "consultation. « Conjoint avec mandataire solidaire » n'est "
                 "pas « solidaire »."},
        {"cle": "mandataire",
         "libelle": "Désignation du mandataire et étendue de son habilitation",
         "source": "saisie",
         "aide": "Sans objet pour un candidat individuel. En groupement, "
                 "l'habilitation doit couvrir ce que le règlement exige — "
                 "signer l'offre, représenter, encaisser."},
        {"cle": "signataire", "libelle": "Signataire et qualité",
         "source": "fiche", "champ": "representant_nom"},
        {"cle": "qualite", "libelle": "Qualité du signataire",
         "source": "fiche", "champ": "representant_qualite"},
        {"cle": "d_exclusion", "source": "declaration",
         "libelle": "Déclaration d'absence d'interdiction de soumissionner",
         "reprend": ("honneur", 0)},
    ],
    "dc2": [
        {"cle": "acheteur", "libelle": "Identification de l'acheteur",
         "source": "consultation", "releve": "acheteur"},
        {"cle": "objet_consultation", "libelle": "Objet de la consultation",
         "source": "consultation", "releve": "objet"},
        {"cle": "candidat", "libelle": "Dénomination du candidat ou du membre "
         "du groupement", "source": "fiche", "champ": "raison_sociale"},
        {"cle": "forme", "libelle": "Forme juridique", "source": "fiche",
         "champ": "forme_juridique"},
        {"cle": "siret", "libelle": "SIRET", "source": "fiche", "champ": "siret"},
        {"cle": "siren", "libelle": "SIREN", "source": "calcul", "calcul": "siren"},
        {"cle": "tva", "libelle": "Numéro de TVA intracommunautaire",
         "source": "calcul", "calcul": "tva"},
        {"cle": "capital", "libelle": "Capital social", "source": "fiche",
         "champ": "capital"},
        {"cle": "rcs", "libelle": "Immatriculation au RCS", "source": "fiche",
         "champ": "rcs"},
        {"cle": "naf", "libelle": "Code NAF / APE — aptitude à exercer "
         "l'activité", "source": "fiche", "champ": "naf"},
        {"cle": "ca_n1", "libelle": "Chiffre d'affaires — dernier exercice",
         "source": "fiche", "champ": "ca_n1"},
        {"cle": "ca_n2", "libelle": "Chiffre d'affaires — N-2",
         "source": "fiche", "champ": "ca_n2"},
        {"cle": "ca_n3", "libelle": "Chiffre d'affaires — N-3",
         "source": "fiche", "champ": "ca_n3"},
        {"cle": "effectif", "libelle": "Effectif moyen annuel",
         "source": "fiche", "champ": "effectif"},
        {"cle": "appui_tiers",
         "libelle": "Capacités d'opérateurs tiers invoquées, et engagement de "
                    "ces opérateurs",
         "source": "saisie",
         "aide": "Citer un tiers ne suffit pas : son ENGAGEMENT écrit se "
                 "joint, sans quoi la capacité invoquée ne compte pas."},
    ],
    "honneur": [
        {"cle": "candidat", "libelle": "Dénomination du déclarant",
         "source": "fiche", "champ": "raison_sociale"},
        {"cle": "signataire", "libelle": "Signataire habilité",
         "source": "fiche", "champ": "representant_nom"},
        {"cle": "qualite", "libelle": "Qualité du signataire",
         "source": "fiche", "champ": "representant_qualite"},
        {"cle": "d_obligatoires", "source": "declaration",
         "libelle": "Interdictions obligatoires", "reprend": ("honneur", 0)},
        {"cle": "d_facultatives", "source": "declaration",
         "libelle": "Interdictions facultatives", "reprend": ("honneur", 1)},
        {"cle": "d_fiscal_social", "source": "declaration",
         "libelle": "Situation fiscale et sociale", "reprend": ("honneur", 2)},
    ],
    "tiers": [
        {"cle": "acheteur", "libelle": "Acheteur destinataire du formulaire",
         "source": "consultation", "releve": "acheteur"},
        {"cle": "candidat", "libelle": "Dénomination", "source": "fiche",
         "champ": "raison_sociale"},
        {"cle": "siret", "libelle": "SIRET", "source": "fiche", "champ": "siret"},
        {"cle": "contact", "libelle": "Courriel de contact", "source": "fiche",
         "champ": "courriel"},
        {"cle": "format",
         "libelle": "Formulaire de l'acheteur, dans SA version et SON format",
         "source": "saisie",
         "aide": "Il n'y a pas de modèle national : le formulaire d'une autre "
                 "consultation ne convient pas. Il est joint au dossier de "
                 "consultation, ou à demander à l'acheteur."},
    ],
    "atd_atp": [
        {"cle": "candidat", "libelle": "Dénomination", "source": "fiche",
         "champ": "raison_sociale"},
        {"cle": "siret", "libelle": "SIRET", "source": "fiche", "champ": "siret"},
        {"cle": "assureur", "libelle": "Assureur responsabilité civile "
         "professionnelle", "source": "fiche", "champ": "assurance_compagnie"},
        {"cle": "police", "libelle": "Numéro de police", "source": "fiche",
         "champ": "assurance_police"},
        {"cle": "echeance", "libelle": "Échéance", "source": "fiche",
         "champ": "assurance_echeance"},
    ],
}

STATUTS = {
    "rempli": "Rempli",
    "a_saisir": "À saisir",
    "a_declarer": "À déclarer et signer",
    "non_trouve": "Non relevé dans le dossier",
    "invalide": "À corriger",
}


def _index_releves(analyse):
    """Ce que le dossier déposé dit, relevé par relevé, pièce par pièce.

    QUAND DEUX PIÈCES NE DISENT PAS LA MÊME CHOSE, ON LE DIT. L'objet du RC et
    celui du CCTP diffèrent parfois d'un mot qui change le périmètre. La valeur
    retenue est celle de la pièce qu'on ouvre EN PREMIER — le règlement de
    consultation fait foi sur ce qu'il faut remettre — et l'autre est rendue
    comme une DIVERGENCE, jamais écrasée en silence.
    """
    par_cle = {}
    for p in sorted((analyse or {}).get("pieces", []),
                    key=lambda x: x.get("rang_lecture", 99)):
        for r in p.get("releves", []):
            for c in r.get("citations", []):
                if not c.get("valeur"):
                    continue
                prop = {"valeur": c["valeur"], "citation": c["texte"],
                        "fichier": p.get("fichier"), "sigle": p.get("sigle"),
                        "part": c.get("part", 0)}
                par_cle.setdefault(r["cle"], []).append(prop)
                break
    return par_cle


def remplir(fiche=None, analyse=None, saisies=None, groupement=False):
    """Chaque pièce, rubrique par rubrique, avec la valeur ET son origine.

    RIEN N'EST INVENTÉ, ET RIEN N'EST DÉCLARÉ. Une rubrique dont la valeur
    n'existe ni dans la fiche ni dans le dossier ressort VIDE, avec ce qui
    manque et où le trouver. Les déclarations sur l'honneur ressortent au
    statut `a_declarer` avec le texte exact de ce qui est affirmé.
    """
    fiche = fiche or {}
    saisies = saisies or {}
    idx = _index_releves(analyse)
    calc = derive(fiche)
    par_champ = {c["cle"]: c for c in CHAMPS_CANDIDAT}
    par_piece = {p["cle"]: p for p in DOSSIER_CANDIDATURE}

    # LE DOSSIER ENTIER, ET PAS SEULEMENT CE QUE CE MODULE SAIT REMPLIR.
    # La version précédente n'affichait que les cinq pièces à rubriques : les
    # neuf autres n'apparaissaient nulle part dans ce bloc — dont DEUX
    # BLOQUANTES, les pouvoirs et les références. Un dossier de candidature
    # qu'on croit complet parce que l'écran ne montre que ce qu'il sait faire
    # est pire qu'un écran vide.
    pieces = []
    for base in DOSSIER_CANDIDATURE:
        cle_piece = base["cle"]
        rubriques = RUBRIQUES.get(cle_piece, [])
        lignes = []
        for r in rubriques:
            l = {"cle": r["cle"], "libelle": r["libelle"],
                 "source": r["source"], "valeur": None, "origine": None,
                 "citation": None, "divergences": [], "aide": r.get("aide"),
                 "message": None}
            if r["source"] == "declaration":
                p_src, i = r["reprend"]
                l["texte"] = par_piece[p_src]["contient"][i]
                l["statut"] = "a_declarer"
                l["message"] = ("Cette affirmation engage pénalement celui qui "
                                "la signe. Elle n'est pas pré-remplie : lisez-la, "
                                "vérifiez-la, puis assumez-la.")
            elif r["source"] == "fiche":
                champ = par_champ[r["champ"]]
                v = str(fiche.get(r["champ"]) or "").strip()
                if not v:
                    l["statut"] = "a_saisir"
                    l["message"] = champ.get("ou") or ("À renseigner dans la "
                                                       "fiche du candidat.")
                else:
                    ok, pourquoi = controler(r["champ"], v)
                    l["valeur"] = v
                    l["origine"] = "Votre fiche — « %s »" % champ["nom"]
                    l["statut"] = "rempli" if ok else "invalide"
                    l["message"] = pourquoi
            elif r["source"] == "calcul":
                d = calc.get(r["calcul"])
                if not d:
                    l["statut"] = "a_saisir"
                    l["message"] = ("Se déduit du SIRET : renseignez-le dans "
                                    "la fiche.")
                else:
                    l["valeur"] = d["valeur"]
                    l["origine"] = "Déduit — " + d["regle"]
                    l["statut"] = "rempli"
            elif r["source"] == "consultation":
                props = idx.get(r["releve"], [])
                if not props:
                    l["statut"] = "non_trouve"
                    l["message"] = ("Non relevé dans les pièces déposées. Ce "
                                    "n'est pas « il n'y en a pas » : c'est "
                                    "« le relevé ne l'a pas vu ». À lire à la "
                                    "main, puis à saisir ici.")
                else:
                    p0 = props[0]
                    l["valeur"] = p0["valeur"]
                    l["origine"] = "Relevé dans %s, à %d %% du document" % (
                        p0["sigle"] or p0["fichier"], p0["part"])
                    l["citation"] = {"texte": p0["citation"],
                                     "fichier": p0["fichier"],
                                     "part": p0["part"]}
                    l["statut"] = "rempli"
                    autres = [p for p in props[1:]
                              if p["valeur"].lower() != p0["valeur"].lower()]
                    if autres:
                        l["divergences"] = autres
                        l["message"] = (
                            "%d autre(s) pièce(s) ne disent pas la même chose. "
                            "Une divergence entre deux pièces du même dossier "
                            "se tranche AVANT de remplir, pas après."
                            % len(autres))
            else:                                       # saisie
                v = str(saisies.get("%s.%s" % (cle_piece, r["cle"])) or "").strip()
                if v:
                    l["valeur"] = v
                    l["origine"] = "Saisi pour cette consultation"
                    l["statut"] = "rempli"
                else:
                    l["statut"] = "a_saisir"
            l["statut_nom"] = STATUTS[l["statut"]]
            lignes.append(l)

        compte = {k: sum(1 for l in lignes if l["statut"] == k)
                  for k in STATUTS}
        v = voie(cle_piece, base["nature"])
        mesurable = v == "remplir"
        pieces.append({
            "cle": cle_piece, "nom": base["nom"], "nature": base["nature"],
            "nature_nom": NATURES_PIECE[base["nature"]]["nom"],
            "famille": base["famille"],
            "famille_nom": FAMILLES_PIECE[base["famille"]]["nom"],
            "voie": v, "voie_nom": VOIES[v]["nom"], "voie_aide": VOIES[v]["aide"],
            # CE QU'UNE PIÈCE NON REMPLISSABLE DOIT QUAND MÊME DIRE : ce
            # qu'elle contient, qui la produit, et son délai. Sans cela, le
            # menu la nommerait et le lecteur ne trouverait rien derrière.
            "mesurable": mesurable,
            "contient": base["contient"], "produit_par": base["produit_par"],
            "delai": base.get("delai"),
            "bloquant": base["bloquant"], "piege": base["piege"],
            "rubriques": lignes, "compte": compte, "total": len(lignes),
            "en_groupement": _groupement(base) if groupement else None,
            # DEUX NOTIONS, ET LES CONFONDRE ÉTAIT UN MENSONGE. « Complète »
            # veut dire : plus rien ne manque DE CE QUE CE MODULE PEUT
            # APPORTER. « Prête » veut dire : et il ne reste rien à déclarer.
            # Ma première version n'avait que `pret`, calculé comme `complet`,
            # sous un commentaire qui affirmait le contraire — un DC1 dont
            # toutes les cases factuelles étaient remplies ressortait « prêt »
            # avec sa déclaration sur l'honneur vierge. Une pièce qui porte une
            # déclaration ne peut JAMAIS être dite prête par un programme :
            # c'est une signature qui la rend prête, et personne ici ne signe.
            # UNE PIÈCE QUE CE MODULE NE REMPLIT PAS N'EST NI COMPLÈTE NI
            # INCOMPLÈTE : elle n'est pas MESURABLE. Lui donner « complète =
            # faux » la ferait compter comme un manque que rien ne peut
            # combler ici ; « complète = vrai » la ferait compter comme faite
            # alors que personne ne l'a écrite. `None` est la seule réponse
            # honnête, et le décompte ne porte que sur les mesurables.
            "complet": (compte["a_saisir"] == 0 and compte["non_trouve"] == 0
                        and compte["invalide"] == 0) if mesurable else None,
            "pret": (compte["a_saisir"] == 0 and compte["non_trouve"] == 0
                     and compte["invalide"] == 0
                     and compte["a_declarer"] == 0) if mesurable else None,
            "porte_declaration": compte["a_declarer"] > 0,
        })

    mesurables = [p for p in pieces if p["mesurable"]]
    manque_bloquant = [p["nom"] for p in mesurables
                       if p["bloquant"] and not p["complet"]]
    # LES BLOQUANTES QU'ON NE PEUT PAS REMPLIR ICI SONT DITES À PART, et c'est
    # l'information qui manquait le plus : les pouvoirs et les références
    # rendent la candidature irrecevable si elles manquent, et ce module n'a
    # aucun moyen de les produire. Les taire parce qu'il ne sait pas les faire
    # serait la pire des omissions.
    a_produire = [{"nom": p["nom"], "voie": p["voie"], "voie_nom": p["voie_nom"],
                   "delai": p["delai"], "famille": p["famille"]}
                  for p in pieces if p["bloquant"] and not p["mesurable"]]
    return {
        "version": VERSION,
        "pieces": pieces,
        "statuts": STATUTS,
        "champs": CHAMPS_CANDIDAT,
        "groupes": GROUPES_FICHE,
        "etat": {
            "rubriques": sum(p["total"] for p in pieces),
            "remplies": sum(p["compte"]["rempli"] for p in pieces),
            "a_saisir": sum(p["compte"]["a_saisir"] for p in pieces),
            "a_declarer": sum(p["compte"]["a_declarer"] for p in pieces),
            "non_trouvees": sum(p["compte"]["non_trouve"] for p in pieces),
            "invalides": sum(p["compte"]["invalide"] for p in pieces),
            "pieces_completes": sum(1 for p in mesurables if p["complet"]),
            "pieces_pretes": sum(1 for p in mesurables if p["pret"]),
            "pieces_a_signer": sum(1 for p in mesurables
                                   if p["complet"] and p["porte_declaration"]),
            "pieces": len(pieces),
            "mesurables": len(mesurables),
            "bloquantes_incompletes": manque_bloquant,
            "bloquantes_a_produire": a_produire,
        },
        "familles": FAMILLES_PIECE,
        "voies": VOIES,
        "note": NOTE_REMPLISSAGE,
        "sans_dossier": not (analyse and analyse.get("pieces")),
    }


NOTE_REMPLISSAGE = (
    "CE MODULE RECOPIE, IL NE DÉCLARE PAS. Il porte dans chaque pièce ce qui "
    "est déjà écrit ailleurs — votre fiche, ou le dossier de consultation que "
    "vous venez de déposer — et il dit pour chaque valeur d'où elle vient. Les "
    "déclarations sur l'honneur ne sont JAMAIS pré-remplies : leur fausseté "
    "est sanctionnée pénalement, et une case cochée par un programme est une "
    "déclaration que personne n'a faite. Une pièce dite « prête » est une "
    "pièce dont plus rien ne manque de ce que ce module peut apporter — elle "
    "n'est ni relue, ni signée, ni conforme au règlement de VOTRE "
    "consultation, qui l'emporte sur cette liste.")


def _cellule(x):
    """Une valeur dans une cellule de tableau, sans casser le tableau."""
    return " ".join(str(x or "—").split()).replace("|", "\\|")[:300]


def markdown_remplissage(r):
    """Le dossier préparé, en Markdown, pour être emporté.

    POURQUOI UN TABLEAU ET PAS UN FORMULAIRE. Ce document ne remplace pas le
    DC1 : les formulaires officiels ont leur version, leur format et leurs
    cases, et un fac-similé produit ici serait refusé — ou pire, accepté et
    faux. Il se pose À CÔTÉ du formulaire, rubrique par rubrique, avec pour
    chacune la valeur et SON ORIGINE, pour être recopié en le vérifiant.

    LES DÉCLARATIONS SORTENT VIDES, avec le texte de ce qui est affirmé et une
    ligne de signature. Les pré-remplir dans un document exporté serait pire
    que dans la page : le document circule, et il se signerait sans être lu.
    """
    e = r["etat"]
    L = ["# Dossier de candidature — pièces préparées", ""]
    L.append(r["note"])
    L.append("")
    L.append("## Où en est le dossier")
    L.append("")
    L.append("| | Nombre |")
    L.append("|---|---|")
    L.append("| Rubriques remplies | %d |" % e["remplies"])
    L.append("| À saisir | %d |" % e["a_saisir"])
    L.append("| Non relevées dans le dossier de consultation | %d |"
             % e["non_trouvees"])
    L.append("| À déclarer et signer | %d |" % e["a_declarer"])
    L.append("| À corriger | %d |" % e["invalides"])
    L.append("| Pièces sans rien à compléter | %d sur %d |"
             % (e["pieces_completes"], e["pieces"]))
    L.append("| Dont il ne reste qu'à SIGNER | %d |" % e["pieces_a_signer"])
    L.append("")
    if e["bloquantes_incompletes"]:
        L.append("**Pièces bloquantes encore incomplètes :** "
                 + ", ".join(e["bloquantes_incompletes"]) + ".")
        L.append("")
    if r.get("sans_dossier"):
        L.append("**Aucun dossier de consultation n'a été analysé.** Les "
                 "rubriques qui viennent des pièces de l'acheteur — l'acheteur, "
                 "l'objet, la référence, les lots — sont donc vides.")
        L.append("")

    for p in r["pieces"]:
        L.append("## %s" % p["nom"])
        L.append("")
        L.append("*%s%s*" % (p["nature_nom"],
                             " — pièce bloquante" if p["bloquant"] else ""))
        L.append("")
        lignes = [l for l in p["rubriques"] if l["source"] != "declaration"]
        if lignes:
            L.append("| Rubrique | Valeur | Origine | État |")
            L.append("|---|---|---|---|")
            for l in lignes:
                L.append("| %s | %s | %s | %s |" % (
                    _cellule(l["libelle"]), _cellule(l["valeur"]),
                    _cellule(l["origine"]), _cellule(l["statut_nom"])))
            L.append("")
        for l in p["rubriques"]:
            if l["citation"]:
                L.append("> **%s** — %s  \n> *(%s, à %d %% du document)*"
                         % (l["libelle"], l["citation"]["texte"],
                            l["citation"]["fichier"], l["citation"]["part"]))
                L.append("")
            for d in l.get("divergences") or []:
                L.append("**Divergence sur « %s ».** %s dit : %s — à trancher "
                         "AVANT de remplir, pas après."
                         % (l["libelle"], d.get("sigle") or d.get("fichier"),
                            d["valeur"]))
                L.append("")
        decl = [l for l in p["rubriques"] if l["source"] == "declaration"]
        if decl:
            L.append("### Déclarations — à lire, à vérifier, puis à signer")
            L.append("")
            for l in decl:
                L.append("**%s**" % l["libelle"])
                L.append("")
                L.append("> " + l["texte"])
                L.append("")
            L.append("Nom et qualité du signataire : "
                     "_______________________________________")
            L.append("")
            L.append("Date et signature : "
                     "_______________________________________")
            L.append("")
        L.append("*Le piège* — %s" % p["piege"])
        L.append("")
    return "\n".join(L)


# ═══════════════════════════════════════════════════════════════════════════
#  LES CONTRÔLES DE COHÉRENCE
# ═══════════════════════════════════════════════════════════════════════════

def _verifier():
    """Les fautes de structure, ou une liste vide.

    LA VÉRIFICATION QUI COMPTE porte sur les expressions régulières : une
    expression invalide ferait échouer l'analyse au moment du dépôt d'un
    document — c'est-à-dire au pire moment, sur un poste où personne ne peut
    la corriger. Elles sont donc toutes compilées ici, au chargement.
    """
    fautes = []
    rangs = {}
    for code, p in PIECES_MARCHE.items():
        for champ in ("nom", "sigle", "ce_que_c_est", "engage", "chercher",
                      "piege"):
            if not (p.get(champ) or "").strip():
                fautes.append("pièce %s : champ « %s » vide" % (code, champ))
        r = p.get("rang_lecture")
        if r in rangs:
            fautes.append("rang de lecture en double (%s) : %s et %s"
                          % (r, rangs[r], code))
        rangs[r] = code
        if code not in _MARQUEURS:
            fautes.append("pièce %s : aucun marqueur d'identification" % code)
    for code, m in _MARQUEURS.items():
        if code not in PIECES_MARCHE:
            fautes.append("marqueurs %s : aucune pièce correspondante" % code)
        for cle in ("nom", "texte"):
            for motif in m.get(cle, []):
                try:
                    re.compile(motif)
                except re.error as exc:
                    fautes.append("marqueur %s/%s invalide (%s) : %s"
                                  % (code, cle, motif, exc))
    for r in RELEVES:
        for p in r["pieces"]:
            if p not in PIECES_MARCHE:
                fautes.append("relevé %s : pièce inconnue (%s)" % (r["cle"], p))
        for motif in r["motifs"]:
            try:
                re.compile(motif)
            except re.error as exc:
                fautes.append("relevé %s : motif invalide (%s) : %s"
                              % (r["cle"], motif, exc))
    for code, pourquoi in _EXT_INDICE.values():
        if code not in PIECES_MARCHE:
            fautes.append("indice d'extension : pièce inconnue (%s)" % code)
    vues = set()
    for p in DOSSIER_CANDIDATURE:
        if p["cle"] in vues:
            fautes.append("pièce de candidature en double : %s" % p["cle"])
        vues.add(p["cle"])
        if p["nature"] not in NATURES_PIECE:
            fautes.append("pièce %s : nature inconnue (%s)"
                          % (p["cle"], p["nature"]))
        if not p.get("contient"):
            fautes.append("pièce %s : rien à contenir" % p["cle"])
        if p.get("famille") not in FAMILLES_PIECE:
            fautes.append("pièce %s : famille inconnue (%s) — le menu la "
                          "rangerait nulle part" % (p["cle"], p.get("famille")))
        for champ in ("nom", "produit_par", "piege"):
            if not (p.get(champ) or "").strip():
                fautes.append("pièce %s : champ « %s » vide" % (p["cle"], champ))

    # ── LE REMPLISSAGE : CHAQUE RUBRIQUE DOIT POUVOIR ÊTRE REMPLIE ─────────
    # UNE RUBRIQUE QUI DÉSIGNE UN RELEVÉ SANS GROUPE DE CAPTURE EST UNE CASE
    # DÉFINITIVEMENT VIDE. Le défaut existait : la « Référence de la
    # consultation » du DC1 ressortait « non relevée » sur un dossier qui la
    # portait en toutes lettres, parce que son motif citait sans capturer. Rien
    # ne plantait — c'est bien le problème.
    par_releve = {r["cle"]: r for r in RELEVES}
    par_champ = {c["cle"] for c in CHAMPS_CANDIDAT}
    par_piece = {p["cle"]: p for p in DOSSIER_CANDIDATURE}
    calculs = set(derive({"siret": "80295478500019"}))
    for cle_piece, rubriques in RUBRIQUES.items():
        if cle_piece not in par_piece:
            fautes.append("rubriques %s : aucune pièce de candidature"
                          % cle_piece)
            continue
        vues_r = set()
        for r in rubriques:
            if r["cle"] in vues_r:
                fautes.append("%s : rubrique en double (%s)"
                              % (cle_piece, r["cle"]))
            vues_r.add(r["cle"])
            if not (r.get("libelle") or "").strip():
                fautes.append("%s/%s : libellé vide" % (cle_piece, r["cle"]))
            if r["source"] == "consultation":
                rel = par_releve.get(r.get("releve"))
                if not rel:
                    fautes.append("%s/%s : relevé inconnu (%s)"
                                  % (cle_piece, r["cle"], r.get("releve")))
                elif not any(re.compile(m).groups for m in rel["motifs"]):
                    fautes.append(
                        "%s/%s : le relevé « %s » ne capture aucune valeur — "
                        "la case ne pourra jamais être remplie"
                        % (cle_piece, r["cle"], r["releve"]))
            elif r["source"] == "fiche":
                if r.get("champ") not in par_champ:
                    fautes.append("%s/%s : champ de fiche inconnu (%s)"
                                  % (cle_piece, r["cle"], r.get("champ")))
            elif r["source"] == "calcul":
                if r.get("calcul") not in calculs:
                    fautes.append("%s/%s : calcul inconnu (%s)"
                                  % (cle_piece, r["cle"], r.get("calcul")))
            elif r["source"] == "declaration":
                src, i = r.get("reprend", (None, None))
                contient = (par_piece.get(src) or {}).get("contient") or []
                # `(i or -1)` traitait l'indice 0 comme absent : 0 est faux.
                if not (isinstance(i, int) and 0 <= i < len(contient)):
                    fautes.append(
                        "%s/%s : la déclaration reprise (%s, %s) n'existe pas "
                        "— le texte de ce qui est affirmé serait réécrit à côté"
                        % (cle_piece, r["cle"], src, i))
            elif r["source"] != "saisie":
                fautes.append("%s/%s : source inconnue (%s)"
                              % (cle_piece, r["cle"], r["source"]))
    return fautes


_FAUTES = _verifier()
if _FAUTES:
    raise RuntimeError("ao_dc — table incohérente : " + " ; ".join(_FAUTES))
