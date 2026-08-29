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

_MARQUEURS = {
    "rc": {
        "nom": [r"\brc\b", r"r[eè]glement.{0,10}consultation", r"\brdc\b"],
        "texte": [r"r[èe]glement de (?:la )?consultation",
                  r"date (?:et heure )?limite de r[ée]ception des (?:plis|offres|candidatures)",
                  r"crit[èe]res? (?:de )?(?:jugement|s[ée]lection|attribution)",
                  r"composition du dossier"],
    },
    "ae": {
        "nom": [r"\bae\b", r"acte.{0,3}d.?engagement", r"attri1"],
        "texte": [r"acte d.?engagement", r"attri1",
                  r"apr[èe]s avoir pris connaissance"],
    },
    "ccap": {
        "nom": [r"\bccap\b", r"clauses administratives particuli"],
        "texte": [r"cahier des clauses administratives particuli",
                  r"p[ée]nalit[ée]s? de retard", r"retenue de garantie",
                  r"ordre de priorit[ée] des pi[èe]ces"],
    },
    "ccag": {
        "nom": [r"\bccag\b", r"clauses administratives g[ée]n[ée]rales"],
        "texte": [r"cahier des clauses administratives g[ée]n[ée]rales",
                  r"ccag[- ](?:pi|moe|travaux|fcs|tic)"],
    },
    "cctp": {
        "nom": [r"\bcctp\b", r"clauses techniques", r"\bcct\b"],
        "texte": [r"cahier des clauses techniques particuli",
                  r"prestations attendues", r"performances? exig[ée]es?"],
    },
    "dpgf": {
        "nom": [r"\bdpgf\b", r"d[ée]composition du prix"],
        "texte": [r"d[ée]composition du prix global et forfaitaire",
                  r"\bdpgf\b"],
    },
    "bpu": {
        "nom": [r"\bbpu\b", r"bordereau des prix", r"\bdqe\b"],
        "texte": [r"bordereau des prix unitaires",
                  r"d[ée]tail quantitatif estimatif"],
    },
    "repartition": {
        "nom": [r"r[ée]partition", r"moe.?amo", r"amo.?moe", r"\braci\b"],
        "texte": [r"r[ée]partition des (?:missions|t[âa]ches)",
                  r"ma[îi]trise d.?[œoe]uvre.{0,40}assistan",
                  r"\braci\b"],
    },
    "calculs": {
        "nom": [r"calcul", r"bilan de puissance", r"tableur", r"estimation"],
        "texte": [r"bilan de puissance", r"hypoth[èe]ses de calcul"],
    },
    "plans": {
        "nom": [r"\bplan\b", r"plans", r"sch[ée]ma", r"\bdwg\b", r"\bpid\b"],
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
    {
        "cle": "reference",
        "libelle": "Référence de la consultation",
        "pieces": ("rc", "ae", "ccap"),
        "motifs": [
            r"(?:r[ée]f[ée]rence|n[°o]\s*(?:de\s*)?(?:march[ée]|consultation|dossier))[^.\n]{0,80}",
            r"\b\d{4}[-_/]\d{2,4}[-_/][A-Z0-9]{2,10}\b",
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
            cle = frag[:80].lower()
            if cle in vus:
                continue
            vus.add(cle)
            out.append({"texte": frag[:400],
                        "position": m.start(),
                        "part": round(100.0 * m.start() / n) if n else 0})
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

DOSSIER_CANDIDATURE = [
    {
        "cle": "dc1",
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
        "cle": "dc2",
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
        "cle": "pouvoirs",
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
        "cle": "tiers",
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
        "cle": "honneur",
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
        "cle": "repartition_competences",
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
        "cle": "conventions",
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
        "cle": "equipe",
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
        "cle": "organigramme",
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
        "cle": "cv",
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
        "cle": "atd_atp",
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
        "cle": "references",
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
        "cle": "moyens",
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
        "cle": "qse",
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
        for champ in ("nom", "produit_par", "piege"):
            if not (p.get(champ) or "").strip():
                fautes.append("pièce %s : champ « %s » vide" % (p["cle"], champ))
    return fautes


_FAUTES = _verifier()
if _FAUTES:
    raise RuntimeError("ao_dc — table incohérente : " + " ; ".join(_FAUTES))
