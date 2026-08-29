"""Ce que vaut un document de la base, et comment il se classe.

POURQUOI CE MODULE EXISTE. La base de connaissance sait chercher : elle croise
une recherche par mots et une recherche par le sens, et fusionne les deux
classements. Ce qu'elle ne sait pas, c'est ce que VAUT ce qu'elle remonte. Une
plaquette de fournisseur et un texte normatif peuvent être également « proches »
d'une question sur des seuils de refroidissement — et le moteur les sert dans
l'ordre de leur ressemblance, qui ne dit rien de leur autorité.

Sur une note de synthèse, c'est un inconvénient. Sur une pièce d'ingénierie ou
de maîtrise d'œuvre, c'est un risque : la pièce est opposable, elle sera lue en
visa, et la valeur qu'elle porte sera exigée à sa source.

LA DOCTRINE N'EST PAS NOUVELLE ICI, elle est seulement appliquée ailleurs.
`etat_art.py` la pose depuis l'origine pour la bibliographie du moteur : « Un
fait sans son auteur n'est pas un fait, c'est une rumeur », et trois natures de
source avec ce que chacune permet d'affirmer. Ce module porte la même règle
jusqu'à la base documentaire, où elle manquait entièrement.

CE QUE CE MODULE FAIT, en trois gestes :

  · il DEVINE la nature et la date d'un document à l'ingestion, sans jamais
    affirmer — une nature non reconnue ressort « indéterminée », et se corrige
    à la main depuis la console ;
  · il RECLASSE les extraits remontés par la recherche, en corrigeant l'ordre
    de pertinence par l'autorité de la source, sa fraîcheur rapportée à la
    péremption du sujet, et la nature contractuelle de la pièce en cours ;
  · il SIGNALE les divergences de valeurs entre deux documents retenus sur un
    même point — sans prétendre trancher.

LE CLASSEMENT RESTE UN CLASSEMENT, PAS UN SCORE. Les mouvements s'expriment en
RANGS : « remonté de trois rangs, source normative ». Une note sur cent donnerait
une fausse précision à un jugement qui est ordinal par nature, et que personne ne
pourrait plus contester. Un rang se discute ; une décimale, non.

ET LE RECLASSEMENT CORRIGE, IL NE RENVERSE PAS. Le déplacement total est borné :
une source normative très en dessous dans la pertinence ne remonte pas en tête.
La recherche reste maîtresse du sujet ; l'autorité départage à pertinence
comparable, ce qui est exactement son rôle.

LE POINT DE RÉGRESSION QUI COMMANDE TOUTE LA CONCEPTION. La base existante n'est
pas qualifiée : tous ses documents sont « indéterminés » et sans date. Une nature
indéterminée est donc STRICTEMENT NEUTRE au classement — jamais pénalisée. Dans
le cas contraire, la mise en service de ce module ferait sortir des résultats la
totalité du fonds documentaire, et la qualification aurait dégradé exactement ce
qu'elle prétend améliorer. Une règle d'essai le vérifie sur un corpus entier.

CE QUE CE MODULE NE FAIT PAS, ET POURQUOI.

  · Il ne juge PAS l'adéquation d'un document à la phase du projet. Rien dans la
    base ne porte de phase : ni le document, ni le fragment. Un critère bâti sur
    une donnée absente aurait l'apparence d'un jugement et la valeur d'un tirage
    au sort. La seule chose qui se déduise honnêtement est le CARACTÈRE de la
    pièce en cours — une pièce contractuelle supporte moins bien une source
    commerciale qu'une note d'esquisse — et c'est cela, et cela seul, qui entre
    au classement.
  · Il ne détecte AUCUNE contradiction de sens. Il relève des écarts de VALEURS
    dans une même unité, ce qui est vérifiable, et laisse la contradiction au
    lecteur : c'est lui qui sait si deux mètres cubes parlent de la même chose.
"""
import datetime
import re

VERSION = "2026-08-a"

RESERVE = (
    "QUALIFICATION DÉDUITE, PAS DÉCLARÉE. La nature et la date d'un document "
    "sont devinées à son dépôt sur son titre, son nom de fichier et ses "
    "premières pages ; elles se corrigent depuis la console. Une nature "
    "indéterminée ne pénalise aucun document — elle signale seulement que "
    "personne ne l'a encore qualifié.")


# ═══════════════════════════════════════════════════════════════════════════
#  LES NATURES DE SOURCE — ce que chacune permet d'affirmer
# ═══════════════════════════════════════════════════════════════════════════
# `deplacement` est un nombre de RANGS, positif vers le haut. Il n'est ni une
# probabilité ni une note : c'est de combien de places une source de cette
# nature devance, à pertinence comparable, une source non qualifiée.
#
# `motifs` sert à la déduction. Ils sont cherchés d'abord dans le titre et le
# nom de fichier — où ils sont fiables —, puis dans les premières pages, où ils
# le sont moins et où la confiance rendue est plus basse.

NATURES = {
    "norme": {
        "nom": "Norme ou référentiel technique",
        "deplacement": 3,
        "permet": "Fonder une exigence technique et l'opposer. C'est la source "
                  "qu'un visa attend derrière une prescription.",
        "ne_permet_pas": "Prouver qu'elle s'applique à CE projet : le domaine "
                         "d'application d'une norme se vérifie, il ne se "
                         "suppose pas. Et une norme citée sans son millésime "
                         "ne prouve rien du tout.",
        "motifs": (r"\bnf\s*[ceps]", r"\ben\s?\d{4,5}\b", r"\biso\b",
                   r"\biec\b", r"\bcei\b", r"\bashrae\b", r"\buptime\b",
                   r"\bafnor\b", r"\bcenelec\b", r"norme", r"référentiel "
                   r"technique", r"\bdtu\b", r"eurocode"),
    },
    "reglementaire": {
        "nom": "Texte réglementaire ou officiel",
        "deplacement": 3,
        "permet": "Établir une obligation, un seuil, un régime. Rien d'autre "
                  "ne le fait.",
        "ne_permet_pas": "Rester vrai longtemps. Un texte se consolide, "
                         "s'abroge et se modifie en cours d'année — la version "
                         "en vigueur à la date du dépôt du dossier est la "
                         "seule qui compte.",
        "motifs": (r"décret", r"arrêté", r"\bcode de l", r"directive\s*\(?ue",
                   r"règlement\s*\(?ue", r"\bjorf\b", r"journal officiel",
                   r"circulaire", r"nomenclature", r"légifrance",
                   r"loi n[°o]", r"ordonnance n[°o]"),
    },
    "retour_exploitation": {
        "nom": "Retour d'exploitation ou mesure",
        "deplacement": 2,
        "permet": "Contredire une valeur de conception. C'est la seule nature "
                  "qui porte du CONSTATÉ, et l'écart entre le conçu et le "
                  "constaté est souvent l'information la plus utile du "
                  "dossier.",
        "ne_permet_pas": "Se généraliser. Une mesure vaut pour l'installation "
                         "mesurée, dans les conditions de la mesure — et la "
                         "période de relevé fait partie de la donnée.",
        "motifs": (r"retour d.exp[eé]rience", r"\brex\b", r"relev[ée]s? "
                   r"d.exploitation", r"campagne de mesure", r"mesures? "
                   r"in situ", r"bilan d.exploitation", r"rapport d.essais",
                   r"proc[eè]s-verbal d.essai"),
    },
    "note_projet": {
        "nom": "Pièce ou note de projet",
        "deplacement": 1,
        "permet": "Dire ce qui a été décidé sur un projet, et par qui. Sur le "
                  "projet en cours, c'est la source la plus spécifique qui "
                  "existe.",
        "ne_permet_pas": "Valoir hors de son projet. Une hypothèse retenue "
                         "ailleurs reste une hypothèse ici, et elle a été "
                         "prise dans un contexte qui n'est pas le vôtre.",
        "motifs": (r"\bcctp\b", r"\bccap\b", r"\bccag\b", r"\bdpgf\b",
                   r"\bdce\b", r"note de calcul", r"note d.hypoth[èe]ses",
                   r"compte[- ]rendu", r"\bapd\b", r"\baps\b",
                   r"cahier des charges", r"m[ée]morandum technique"),
    },
    "recherche": {
        "nom": "Publication de recherche",
        "deplacement": 1,
        "permet": "Éclairer un mécanisme, et donner l'état d'une question. Les "
                  "méthodes y sont publiées, donc discutables.",
        "ne_permet_pas": "Fonder une prescription de projet à elle seule : "
                         "entre un résultat de laboratoire et une "
                         "installation, il reste toute l'industrialisation.",
        "motifs": (r"\bdoi\b", r"\barxiv\b", r"universit[ée]", r"laboratoire",
                   r"\bth[èe]se\b", r"peer[- ]reviewed", r"revue scientifique",
                   r"\bcnrs\b", r"acte[s]? du colloque"),
    },
    "livre_blanc_fournisseur": {
        "nom": "Livre blanc de fournisseur",
        "deplacement": -1,
        "permet": "Comprendre une technologie et repérer les bonnes questions. "
                  "Les mesures techniques y sont souvent fiables : l'auteur "
                  "les tient de ses propres déploiements.",
        "ne_permet_pas": "Servir de source neutre. La SÉLECTION des faits y "
                         "sert une offre, et le citer sans nommer son auteur "
                         "expose le dossier à la première contradiction.",
        "motifs": (r"livre blanc", r"white ?paper", r"\bebook\b",
                   r"guide complet", r"solution brief"),
    },
    "document_commercial": {
        "nom": "Document commercial",
        "deplacement": -3,
        "permet": "Connaître une offre : ce qui est vendu, à quelles "
                  "conditions, et ce que le vendeur met en avant.",
        "ne_permet_pas": "Porter une valeur dans une pièce opposable. Un "
                         "chiffre de plaquette n'a pas de méthode publiée, "
                         "donc rien à quoi le confronter.",
        "motifs": (r"plaquette", r"brochure", r"catalogue produit",
                   r"tarif[s]? \d{4}", r"datasheet", r"fiche produit",
                   r"nous consulter", r"demander une d[ée]mo"),
    },
    "indetermine": {
        "nom": "Nature non qualifiée",
        "deplacement": 0,
        "permet": "Rien de particulier — et rien ne lui est retiré non plus. "
                  "Le document est servi sur sa seule pertinence, comme avant "
                  "toute qualification.",
        "ne_permet_pas": "Être présenté comme une source neutre OU comme une "
                         "source douteuse. On ne sait pas, et c'est ce que "
                         "dit cette nature.",
        "motifs": (),
    },
}

# L'ordre de la déduction : du plus spécifique au plus général. Un texte
# réglementaire cite souvent des normes ; un livre blanc cite souvent les deux.
# Chercher dans l'ordre inverse classerait la moitié de la base en « norme ».
ORDRE_DEDUCTION = ("document_commercial", "livre_blanc_fournisseur",
                   "reglementaire", "norme", "retour_exploitation",
                   "note_projet", "recherche")

DEPLACEMENT_MAX = 4
DEPLACEMENT_MAX_NOTE = (
    "Le déplacement total d'un extrait est borné à %d rangs. LE RECLASSEMENT "
    "CORRIGE, IL NE RENVERSE PAS : une source normative très en dessous dans "
    "la pertinence ne remonte pas en tête du seul fait de sa nature. La "
    "recherche reste maîtresse du sujet ; l'autorité départage à pertinence "
    "comparable." % DEPLACEMENT_MAX)


# ═══════════════════════════════════════════════════════════════════════════
#  LA PÉREMPTION — elle dépend du SUJET, pas de la date seule
# ═══════════════════════════════════════════════════════════════════════════
# LA FAUTE QUE CETTE TABLE EMPÊCHE. Une fraîcheur appliquée uniformément se
# trompe dans les deux sens à la fois : elle laisse passer une note de 2019 sur
# la nomenclature des installations classées — modifiée par décret plusieurs
# fois par an — et elle déclasse une note de 2019 sur le transfert thermique,
# dont le contenu n'a pas bougé et ne bougera pas.
#
# Les motifs sont cherchés dans l'intitulé du thème de `rag_store`. Un contrôle
# de chargement vérifie que chaque règle en reconnaît au moins un thème réel :
# un intitulé recopié de travers ne déclencherait rien, sans erreur — et
# personne ne s'en apercevrait.

PEREMPTION = [
    {"cle": "vite", "nom": "Sujet qui change en cours d'année",
     # Intitulés confrontés au vocabulaire réel de la base par une règle
     # d'essai. « Réglementaire », « Marchés publics », « Subventions » et
     # « Fiscalité » y figuraient et ne reconnaissaient AUCUN thème : ils
     # étaient morts sans le dire, et le sujet correspondant échappait à la
     # règle de péremption sans que rien ne le signale.
     "motifs": ("Réglementation", "Textes & réglementation", "Juridique",
                "NIS2", "RGPD", "DORA", "Marchés & appels d'offres",
                "Appels d'offres", "Fournisseurs", "Veille"),
     "seuil_mois": 18, "recul": 3,
     "pourquoi": "Textes, seuils, tarifs et offres : ils sont modifiés en "
                 "cours d'année, et une version périmée se lit exactement "
                 "comme une version en vigueur."},
    {"cle": "lentement", "nom": "Sujet qui évolue par révisions",
     "motifs": ("Normes", "Efficacité & indicateurs", "Green Management",
                "Certifications", "Mise en service", "Sécurité",
                "Gouvernance", "Cyber"),
     "seuil_mois": 60, "recul": 2,
     "pourquoi": "Normes et référentiels se révisent par éditions "
                 "successives : au-delà de quelques années, le millésime se "
                 "vérifie avant d'être cité."},
    {"cle": "peu", "nom": "Sujet stable",
     "motifs": ("Conception & architecture", "Thermique", "Refroidissement",
                "Eau", "Carbone", "Chaleur fatale", "Recherche",
                "Études de site", "Retours d'exploitation"),
     "seuil_mois": 180, "recul": 1,
     "pourquoi": "Physique, thermique, principes de conception : le contenu "
                 "vieillit peu. Ce qui vieillit, ce sont les ordres de "
                 "grandeur du marché qu'on y trouve incidemment."},
]

PEREMPTION_DEFAUT = {
    "cle": "inconnue", "nom": "Péremption inconnue",
    "seuil_mois": None, "recul": 0,
    "pourquoi": "Le thème du document ne relève d'aucune règle de péremption "
                "déclarée : sa date ne le déplace donc pas. Ne pas savoir à "
                "quelle vitesse un sujet se périme n'autorise pas à supposer "
                "qu'il se périme vite.",
}


# ═══════════════════════════════════════════════════════════════════════════
#  LA DÉDUCTION — deviner sans jamais affirmer
# ═══════════════════════════════════════════════════════════════════════════

# Le titre et le nom de fichier sont fiables : quelqu'un les a écrits pour
# désigner le document. Le corps l'est moins — un livre blanc cite des normes,
# une note de projet cite des décrets. D'où deux niveaux de confiance, et une
# fenêtre de lecture bornée aux premières pages, là où un document se présente.
FENETRE_TEXTE = 4000

CONFIANCES = {
    "titre": "Reconnue au titre ou au nom de fichier — le plus sûr : "
             "quelqu'un les a écrits pour désigner ce document.",
    "texte": "Reconnue dans les premières pages seulement. Moins sûr : un "
             "livre blanc cite des normes, une note de projet cite des "
             "décrets. À vérifier d'un coup d'œil.",
    "aucune": "Aucun motif reconnu. Le document reste non qualifié, ce qui ne "
              "lui retire rien — il est servi sur sa seule pertinence.",
}

_ANNEE = re.compile(r"(?<!\d)(19[89]\d|20[0-4]\d)(?!\d)")
# Dans le CORPS, une année isolée ne prouve rien : un texte technique en cite
# par dizaines. On n'accepte que celles posées dans un contexte de publication.
_ANNEE_CONTEXTE = re.compile(
    r"(?:©|\(c\)|copyright|[ée]dition|version|publi[ée]|paru|mise à jour|"
    r"r[ée]vision|janvier|février|mars|avril|mai|juin|juillet|août|"
    r"septembre|octobre|novembre|décembre)[^\n]{0,40}?"
    r"(?<!\d)(19[89]\d|20[0-4]\d)(?!\d)", re.I)


def _annee_max():
    """L'année la plus tardive acceptable : l'année prochaine.

    Un document daté au-delà n'est pas une source récente, c'est une erreur de
    lecture — un numéro de série, une référence de pièce, une plage de valeurs.
    """
    return datetime.datetime.now(datetime.timezone.utc).year + 1


def deviner_date(titre, filename, texte):
    """L'année du document, ou None — et d'où elle vient.

    DEUX RÈGLES QUI ÉVITENT D'INVENTER UNE DATE :

      · dans le titre et le nom de fichier, une année suffit : ils sont courts
        et rédigés pour désigner le document ;
      · dans le corps, une année isolée ne prouve RIEN. Un document technique
        en cite des dizaines — millésimes de normes, années de référence,
        historiques. Seule une année posée dans un contexte de publication est
        retenue.

    À défaut, None. Une date absente vaut mieux qu'une date fausse : elle laisse
    le document au rang que lui donne sa pertinence, là où une date fausse le
    ferait reculer ou avancer sans motif.
    """
    entete = " ".join(x or "" for x in (titre, filename))
    trouvees = [int(a) for a in _ANNEE.findall(entete)]
    trouvees = [a for a in trouvees if a <= _annee_max()]
    if trouvees:
        return {"annee": max(trouvees), "origine": "titre",
                "aide": "Lue au titre ou au nom de fichier."}
    corps = (texte or "")[:FENETRE_TEXTE]
    ctx = [int(m) for m in _ANNEE_CONTEXTE.findall(corps)]
    ctx = [a for a in ctx if a <= _annee_max()]
    if ctx:
        return {"annee": max(ctx), "origine": "texte",
                "aide": "Lue dans les premières pages, à côté d'une mention "
                        "de publication ou d'édition."}
    return {"annee": None, "origine": "aucune",
            "aide": "Aucune date de publication reconnue. Le document n'est "
                    "pas déplacé par sa fraîcheur — il faudrait pour cela "
                    "savoir de quand il date."}


def deviner_nature(titre, filename, texte):
    """La nature du document, et la confiance qu'on peut lui accorder.

    L'ORDRE DE RECHERCHE EST LOAD-BEARING. Un texte réglementaire cite des
    normes ; un livre blanc cite les deux. Chercher « norme » en premier
    classerait la moitié de la base en norme, et l'autorité qu'on accorde
    ensuite à cette nature ferait remonter des plaquettes devant des décrets.
    On cherche donc du plus spécifique au plus général.
    """
    entete = (" ".join(x or "" for x in (titre, filename))).lower()
    corps = (texte or "")[:FENETRE_TEXTE].lower()
    for cle in ORDRE_DEDUCTION:
        motifs = NATURES[cle]["motifs"]
        for m in motifs:
            if re.search(m, entete):
                return {"nature": cle, "confiance": "titre",
                        "motif": m, "aide": CONFIANCES["titre"]}
    for cle in ORDRE_DEDUCTION:
        for m in NATURES[cle]["motifs"]:
            if re.search(m, corps):
                return {"nature": cle, "confiance": "texte",
                        "motif": m, "aide": CONFIANCES["texte"]}
    return {"nature": "indetermine", "confiance": "aucune", "motif": None,
            "aide": CONFIANCES["aucune"]}


def deviner(titre="", filename="", texte="", theme=""):
    """La qualification d'un document au dépôt : nature, date, et ce que ça vaut.

    RIEN N'EST AFFIRMÉ. Le résultat porte la confiance et le motif reconnu, de
    sorte qu'une déduction fausse se voie et se corrige. Une déduction fausse
    présentée comme un fait serait pire que pas de déduction du tout : elle
    déplacerait des documents au classement sans que personne ne sache pourquoi.
    """
    n = deviner_nature(titre, filename, texte)
    d = deviner_date(titre, filename, texte)
    return {
        "version": VERSION,
        "nature": n["nature"],
        "nature_nom": NATURES[n["nature"]]["nom"],
        "confiance": n["confiance"],
        "motif": n["motif"],
        "aide_nature": n["aide"],
        "date_source": str(d["annee"]) if d["annee"] else None,
        "date_origine": d["origine"],
        "aide_date": d["aide"],
        "peremption": peremption_du_theme(theme)["cle"],
        "reserve": RESERVE,
    }


def peremption_du_theme(theme):
    """À quelle vitesse le sujet de ce thème se périme.

    Première règle dont un motif figure dans l'intitulé. À défaut, la règle par
    défaut, qui ne déplace RIEN : ne pas savoir à quelle vitesse un sujet se
    périme n'autorise pas à supposer qu'il se périme vite.
    """
    t = (theme or "")
    for regle in PEREMPTION:
        for m in regle["motifs"]:
            if m.lower() in t.lower():
                return regle
    return PEREMPTION_DEFAUT


# ═══════════════════════════════════════════════════════════════════════════
#  LE RECLASSEMENT
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE LA PIÈCE EN COURS CHANGE. Une note d'esquisse survole le marché : une
# plaquette de fournisseur y est à sa place, c'est même ce qu'on cherche. Une
# pièce contractuelle est lue en visa, et la valeur qu'elle porte sera exigée à
# sa source : une plaquette y devient un risque. La même source ne vaut donc pas
# la même chose selon l'endroit où elle atterrit.

RECUL_CONTRACTUEL = {
    "document_commercial": 2,
    "livre_blanc_fournisseur": 1,
}
RECUL_CONTRACTUEL_NOTE = (
    "Sur une pièce contractuelle — celle qui est gelée au dossier de "
    "consultation et lue en visa —, les sources d'origine commerciale reculent "
    "davantage : la valeur qu'elles portent sera exigée à sa source, et une "
    "plaquette n'a pas de méthode publiée à opposer. Sur une note d'esquisse, "
    "elles ne reculent pas : y survoler le marché est précisément l'objet.")

BONUS_PROJET = 2
BONUS_PROJET_NOTE = (
    "Un document qui nomme le projet ou le client remonte : c'est la source la "
    "plus spécifique qui existe, et une littérature générale mieux écrite ne "
    "sait rien de CETTE installation.")


def _mois_ecoules(annee):
    """L'âge du document en mois, approché à l'année. Une précision au mois
    serait fausse : on ne connaît que l'année de publication."""
    if not annee:
        return None
    try:
        a = int(annee)
    except (TypeError, ValueError):
        return None
    return max(0, (datetime.datetime.now(datetime.timezone.utc).year - a) * 12)


def _deplacement(hit, contexte):
    """De combien de rangs cet extrait se déplace, et pour quels motifs.

    CHAQUE MOTIF EST NOMMÉ ET CHIFFRÉ EN RANGS. Un déplacement qu'on ne peut
    pas expliquer ne se conteste pas, et un classement qu'on ne peut pas
    contester n'est pas un classement : c'est un oracle.
    """
    contexte = contexte or {}
    raisons, total = [], 0

    nature = (hit.get("nature") or "indetermine")
    if nature not in NATURES:
        nature = "indetermine"
    d = NATURES[nature]["deplacement"]
    if d:
        total += d
        raisons.append({"motif": "nature", "rangs": d,
                        "dit": "%s — %s" % (NATURES[nature]["nom"],
                                            NATURES[nature]["permet"])})

    # La péremption, rapportée au sujet du document — jamais à une durée
    # universelle.
    regle = peremption_du_theme(hit.get("theme"))
    age = _mois_ecoules(hit.get("date_source"))
    if age is not None and regle.get("seuil_mois") and age > regle["seuil_mois"]:
        total -= regle["recul"]
        raisons.append({"motif": "peremption", "rangs": -regle["recul"],
                        "dit": "Publié il y a environ %d ans, sur un sujet où "
                               "%s Millésime à vérifier avant citation."
                               % (age // 12, regle["pourquoi"][0].lower()
                                  + regle["pourquoi"][1:])})

    if contexte.get("contractuel") and nature in RECUL_CONTRACTUEL:
        r = RECUL_CONTRACTUEL[nature]
        total -= r
        raisons.append({"motif": "caractere_piece", "rangs": -r,
                        "dit": RECUL_CONTRACTUEL_NOTE})

    # La spécificité au projet : le titre nomme le projet ou le client.
    cibles = [str(contexte.get(k) or "").strip()
              for k in ("projet", "client")]
    titre = (hit.get("title") or "").lower()
    for c in cibles:
        if len(c) >= 4 and c.lower() in titre:
            total += BONUS_PROJET
            raisons.append({"motif": "specificite", "rangs": BONUS_PROJET,
                            "dit": BONUS_PROJET_NOTE})
            break

    borne = max(-DEPLACEMENT_MAX, min(DEPLACEMENT_MAX, total))
    if borne != total:
        raisons.append({"motif": "borne", "rangs": borne - total,
                        "dit": DEPLACEMENT_MAX_NOTE})
    return borne, raisons


def classer(hits, contexte=None):
    """Les extraits reclassés, chacun avec le mouvement qu'il a subi et pourquoi.

    LE CLASSEMENT D'ENTRÉE EST CELUI DE LA RECHERCHE, et il reste maître du
    sujet : le déplacement est borné, de sorte qu'aucune source ne remonte en
    tête sur sa seule nature. On corrige un ordre de pertinence ; on ne le
    remplace pas par un ordre d'autorité.

    RIEN N'EST RETIRÉ. Un extrait qui recule reste dans la liste, à son
    nouveau rang, avec le motif de son recul. Une sélection silencieuse serait
    exactement ce que ce module existe pour empêcher.

    Le tri est STABLE : à déplacement égal, l'ordre de la recherche est
    conservé. Sans cela, deux extraits également qualifiés changeraient de
    place d'un appel à l'autre, et la pièce ne serait pas reproductible.
    """
    out = []
    for i, h in enumerate(hits or []):
        d, raisons = _deplacement(h, contexte)
        out.append(dict(h, rang_initial=i, deplacement=d, raisons=raisons,
                        cle_tri=i - d))
    out.sort(key=lambda x: (x["cle_tri"], x["rang_initial"]))
    for j, h in enumerate(out):
        h["rang_final"] = j
        h.pop("cle_tri", None)
        n = h.get("nature") or "indetermine"
        h["nature"] = n if n in NATURES else "indetermine"
        h["nature_nom"] = NATURES[h["nature"]]["nom"]
        h["deplace"] = h["rang_final"] != h["rang_initial"]
    return out


def lecture_classement(classes):
    """Ce que le reclassement a fait, en une phrase — ou rien s'il n'a rien fait.

    UN RECLASSEMENT INERTE DOIT LE DIRE. Sur une base non qualifiée, il ne
    déplace rien : l'annoncer évite de croire qu'un tri savant a eu lieu.
    """
    if not classes:
        return ""
    bouges = [c for c in classes if c["deplace"]]
    if not bouges:
        qualifies = [c for c in classes if c["nature"] != "indetermine"]
        if not qualifies:
            return ("Ordre de pertinence inchangé : aucun des documents "
                    "remontés n'est qualifié. Renseigner leur nature depuis "
                    "la console ferait jouer l'autorité des sources.")
        return ("Ordre de pertinence inchangé : les documents remontés se "
                "valent au regard de leur nature et de leur fraîcheur.")
    return ("%d document(s) déplacé(s) sur %d au vu de la nature des sources "
            "et de leur fraîcheur. Le mouvement est borné : la pertinence "
            "reste maîtresse de l'ordre."
            % (len(bouges), len(classes)))


# ═══════════════════════════════════════════════════════════════════════════
#  LES DIVERGENCES DE VALEURS
# ═══════════════════════════════════════════════════════════════════════════
# CE QUE CETTE FONCTION PRÉTEND FAIRE, ET CE QU'ELLE NE PRÉTEND PAS. Elle ne
# comprend rien : elle relève que deux documents retenus sur le même point
# portent des valeurs différentes DANS LA MÊME UNITÉ, et le dit. Elle ne
# tranche pas, elle ne suppose pas qu'il s'agit de la même grandeur — c'est au
# lecteur de savoir si les deux mètres cubes parlent de la même cuve.
#
# POURQUOI C'EST LE SIGNAL QUI COMPTE LE PLUS EN INGÉNIERIE. Une pièce est lue
# en visa, et une valeur y est exigée à sa source. Deux sources qui donnent
# deux chiffres, c'est la situation où le rédacteur doit ARBITRER — et celle
# où, faute de signal, il prend le premier extrait venu sans savoir qu'un
# second le contredit. La discipline est déjà écrite ailleurs dans la maison :
# « deux sources qui se contredisent restent deux lignes contradictoires — la
# contradiction est l'information ».

# Unités où un écart de valeur veut dire quelque chose. Les unités très
# fréquentes et peu spécifiques — le mètre seul, le volt, l'ampère — sont
# volontairement absentes : elles produiraient un bruit qui ferait cesser de
# lire les signalements, ce qui est pire que de ne rien signaler.
UNITES = ("kWh", "MWh", "GWh", "kW", "MW", "GW", "kVA", "kV",
          "m³", "m3", "m²", "m2", "°C", "bar", "kg", "mm",
          "t", "L", "%", "€/MWh", "€/kW", "€", "h", "ans", "mois")

# Écart relatif en deçà duquel deux valeurs sont tenues pour la même : un
# arrondi de rédaction n'est pas une divergence.
ECART_MINIMAL = 0.05

DIVERGENCE_NOTE = (
    "SIGNALEMENT, PAS ARBITRAGE. Deux documents retenus sur ce point portent "
    "des valeurs différentes dans la même unité. Rien ne dit qu'elles "
    "désignent la même grandeur — c'est au rédacteur de le vérifier, et c'est "
    "précisément pour qu'il le vérifie que l'écart est signalé plutôt que "
    "résolu en silence.")

_NOMBRE = r"\d[\d   ]*(?:[.,]\d+)?"
_UNITES_RE = "|".join(re.escape(u) for u in
                      sorted(UNITES, key=len, reverse=True))
_VALEUR = re.compile(r"(?<![\w.,])(" + _NOMBRE + r")\s?(" + _UNITES_RE + r")"
                     r"(?![\w])", re.I)


def _nombre(txt):
    """Un nombre français ou anglais en flottant, ou None."""
    s = (txt or "").replace(" ", "").replace(" ", "").replace(" ", "")
    # Une virgule décimale française ; un point décimal anglais. Les
    # séparateurs de milliers ont déjà sauté avec les espaces.
    s = s.replace(",", ".")
    if s.count(".") > 1:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def valeurs_du_texte(texte):
    """Les couples (valeur, unité) reconnus dans un extrait.

    L'unité est ramenée à une forme unique — « m3 » et « m³ » sont la même —
    sans quoi deux documents qui écrivent la même unité autrement ne seraient
    jamais comparés, et la divergence resterait invisible.
    """
    out = []
    for m in _VALEUR.finditer(texte or ""):
        v = _nombre(m.group(1))
        if v is None:
            continue
        u = m.group(2)
        u = {"m3": "m³", "m2": "m²"}.get(u.lower(), u)
        out.append((v, u))
    return out


def divergences(extraits, maximum=3):
    """Les écarts de valeurs entre documents retenus, du plus grand au plus petit.

    DEUX DOCUMENTS DISTINCTS, ET SEULEMENT EUX. Un même document qui donne
    deux valeurs dans une même unité n'est pas en contradiction : il donne une
    plage, une série, un avant et un après. C'est entre SOURCES que l'écart
    interroge.
    """
    par_unite = {}
    for e in extraits or []:
        did = e.get("doc_id")
        if not did:
            continue
        titre = (e.get("title") or e.get("titre") or "").strip() or "sans titre"
        texte = (e.get("content") or e.get("text") or e.get("extrait") or "")
        for v, u in valeurs_du_texte(texte):
            par_unite.setdefault(u, {}).setdefault(did, {"titre": titre,
                                                         "valeurs": []})
            par_unite[u][did]["valeurs"].append(v)

    trouves = []
    for u, docs in par_unite.items():
        if len(docs) < 2:
            continue
        ids = list(docs)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = docs[ids[i]], docs[ids[j]]
                # L'écart le plus PARLANT entre les deux documents : celui des
                # valeurs les plus proches. Si même les plus proches divergent,
                # les deux sources disent bien deux choses différentes ; à
                # l'inverse, deux plages qui se recouvrent ne divergent pas.
                paires = [(x, y, abs(x - y) / max(abs(x), abs(y)))
                          for x in a["valeurs"] for y in b["valeurs"]
                          if max(abs(x), abs(y)) > 0]
                if not paires:
                    continue
                x, y, ecart = min(paires, key=lambda p: p[2])
                if ecart <= ECART_MINIMAL:
                    continue
                trouves.append({
                    "unite": u, "ecart_relatif": round(ecart, 3),
                    "sources": [{"doc_id": ids[i], "titre": a["titre"],
                                 "valeur": x},
                                {"doc_id": ids[j], "titre": b["titre"],
                                 "valeur": y}],
                    "dit": "%s et %s donnent %g et %g %s."
                           % (a["titre"], b["titre"], x, y, u),
                })
    trouves.sort(key=lambda d: -d["ecart_relatif"])
    return {"divergences": trouves[:maximum], "total": len(trouves),
            "note": DIVERGENCE_NOTE} if trouves else None


# ═══════════════════════════════════════════════════════════════════════════
#  LE RÉFÉRENTIEL ET LES CONTRÔLES
# ═══════════════════════════════════════════════════════════════════════════

def natures():
    """Les natures, ordonnées de la plus autorisée à la moins — pour la console."""
    return [dict(v, cle=k) for k, v in
            sorted(NATURES.items(), key=lambda kv: (-kv[1]["deplacement"], kv[0]))]


def referentiel():
    """Les tables, sans qualification — pour la console et la documentation."""
    return {
        "version": VERSION,
        "reserve": RESERVE,
        "natures": natures(),
        "ordre_deduction": list(ORDRE_DEDUCTION),
        "peremption": PEREMPTION,
        "peremption_defaut": PEREMPTION_DEFAUT,
        "deplacement_max": DEPLACEMENT_MAX,
        "deplacement_max_note": DEPLACEMENT_MAX_NOTE,
        "recul_contractuel": RECUL_CONTRACTUEL,
        "recul_contractuel_note": RECUL_CONTRACTUEL_NOTE,
        "bonus_projet": BONUS_PROJET,
        "unites_comparees": list(UNITES),
        "ecart_minimal": ECART_MINIMAL,
        "confiances": CONFIANCES,
        "glossaire": glossaire(),
    }


def glossaire():
    """Les familles d'infobulles servies par ce module."""
    return {
        "nature_source": {k: {
            "nom": v["nom"],
            "aide": ("Ce qu'elle permet d'affirmer — %s\n\nCe qu'elle ne "
                     "permet pas — %s\n\nAu classement — %s\n\n%s"
                     % (v["permet"], v["ne_permet_pas"],
                        ("remonte de %d rang(s)" % v["deplacement"])
                        if v["deplacement"] > 0 else
                        ("recule de %d rang(s)" % -v["deplacement"])
                        if v["deplacement"] < 0 else
                        "ne déplace rien, dans aucun sens",
                        RESERVE)),
        } for k, v in NATURES.items()},
        "peremption": {r["cle"]: {
            "nom": r["nom"],
            "aide": ("%s\n\nAu-delà de %s, la source recule de %d rang(s) — "
                     "le temps de vérifier son millésime."
                     % (r["pourquoi"],
                        ("%d mois" % r["seuil_mois"]) if r.get("seuil_mois")
                        else "aucun seuil déclaré",
                        r["recul"])),
        } for r in PEREMPTION + [PEREMPTION_DEFAUT]},
    }


def _verifier():
    """Les fautes de structure, ou une liste vide.

    LES DEUX VÉRIFICATIONS QUI COMPTENT :

      · « indéterminé » ne déplace RIEN. C'est la propriété qui protège le
        fonds existant : la base n'est pas qualifiée, et une nature inconnue
        qui pénaliserait ferait sortir la totalité des documents actuels ;
      · l'ordre de déduction couvre toutes les natures qui portent des motifs.
        Une nature absente de cet ordre ne serait jamais devinée — elle
        existerait dans la table, et aucun document ne la recevrait.

    LA CONCORDANCE DES INTITULÉS DE THÈME N'EST PAS VÉRIFIÉE ICI : ce module
    est importé PAR la base, et lui demander ses thèmes au chargement fermerait
    un cycle d'imports. C'est une règle d'essai qui tient ce lien — la même
    discipline que pour la carte des sous-dossiers du cadre d'ingénierie.
    """
    fautes = []
    if NATURES.get("indetermine", {}).get("deplacement") != 0:
        fautes.append("« indéterminé » déplace les documents : le fonds "
                      "existant, entièrement non qualifié, serait déclassé "
                      "en bloc au premier reclassement")
    for k, v in NATURES.items():
        for champ in ("nom", "permet", "ne_permet_pas"):
            if not (v.get(champ) or "").strip():
                fautes.append("nature %s : champ « %s » vide" % (k, champ))
        d = v.get("deplacement")
        if not isinstance(d, int) or abs(d) > DEPLACEMENT_MAX:
            fautes.append("nature %s : déplacement absent ou au-delà de la "
                          "borne (%s)" % (k, d))
        if v.get("motifs"):
            for m in v["motifs"]:
                try:
                    re.compile(m)
                except re.error:
                    fautes.append("nature %s : motif illisible (%r)" % (k, m))
    for k in ORDRE_DEDUCTION:
        if k not in NATURES:
            fautes.append("ordre de déduction : nature inconnue (%s)" % k)
    porteuses = {k for k, v in NATURES.items() if v.get("motifs")}
    manquantes = sorted(porteuses - set(ORDRE_DEDUCTION))
    if manquantes:
        fautes.append("natures jamais devinées faute de figurer dans l'ordre "
                      "de déduction : %s" % ", ".join(manquantes))
    if len(set(ORDRE_DEDUCTION)) != len(ORDRE_DEDUCTION):
        fautes.append("ordre de déduction : nature en double")
    vus = set()
    for r in PEREMPTION:
        if r["cle"] in vus:
            fautes.append("règle de péremption en double : %s" % r["cle"])
        vus.add(r["cle"])
        for champ in ("nom", "pourquoi"):
            if not (r.get(champ) or "").strip():
                fautes.append("péremption %s : champ « %s » vide"
                              % (r["cle"], champ))
        if not r.get("motifs"):
            fautes.append("péremption %s : aucun motif de thème" % r["cle"])
        if not r.get("seuil_mois") or r.get("recul", 0) <= 0:
            fautes.append("péremption %s : seuil ou recul absent — la règle "
                          "ne déplacerait rien" % r["cle"])
    if PEREMPTION_DEFAUT.get("recul"):
        fautes.append("la péremption par défaut recule les documents : ne pas "
                      "savoir à quelle vitesse un sujet se périme "
                      "n'autorise pas à supposer qu'il se périme vite")
    for u in UNITES:
        if not u.strip():
            fautes.append("unité vide dans la table de comparaison")
    return fautes


_FAUTES = _verifier()
if _FAUTES:                                              # pragma: no cover
    raise RuntimeError("qualite_source : table incohérente — "
                       + " ; ".join(_FAUTES))
