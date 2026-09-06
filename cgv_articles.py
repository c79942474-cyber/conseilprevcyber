# -*- coding: utf-8 -*-
"""Les seize articles de loi cités par les conditions de vente, vérifiés.

POURQUOI CE MODULE EXISTE. Les conditions de vente citaient quinze
articles — le document en annonçait treize, le compte était faux ; la
correction en a ajouté un seizième, L221-1, sans lequel la condition « hors
établissement » n'était pas lisible. Chacun y porte une phrase
que le client lit comme du droit : « le professionnel de cinq salariés ou moins
bénéficie de quatorze jours », « s'y ajoute la garantie légale de conformité ».
Aucune de ces phrases n'était mesurée. Elles étaient plausibles, ce qui est
exactement le régime dont ce dépôt se méfie ailleurs : un article inventé, une
version périmée ou un renvoi mal lu se lisent comme du droit exact.

CE QUE LA VÉRIFICATION A TROUVÉ, ET QUI N'ÉTAIT PAS PRÉVU. Deux phrases sur
quinze étaient fausses, et les deux au même endroit — le renvoi de l'article
L221-3 :

  A. L221-3 exige que le contrat ait été conclu HORS ÉTABLISSEMENT. Le
     document disait « cinq salariés ou moins » et « hors de l'activité
     principale », et taisait la troisième condition. Or souscrire en ligne
     est un contrat À DISTANCE, pas un contrat hors établissement : il y faut
     une présence physique simultanée, à la conclusion ou à la sollicitation
     qui l'a immédiatement précédée (L221-1, I, 2°). La chambre commerciale l'a
     jugé en toutes lettres : « le contrat litigieux ayant été conclu entre
     deux professionnels, la société [venderesse] ne pouvait bénéficier des
     dispositions particulières applicables aux contrats à distance »
     (Cass. com., 4 septembre 2024, n° 23-16.886).

  B. L221-3 n'étend QUE les sections 2, 3 et 6 du chapitre Ier. L'article
     L224-25-12 — la garantie de conformité du numérique — est au chapitre IV.
     Le renvoi ne l'atteint pas. Le document l'annonçait pourtant comme un dû
     légal de l'acheteur relevant de L221-3.

Les deux erreurs vont en sens contraire : la première PROMETTAIT TROP peu
souvent (elle ouvrait le droit à des acheteurs qui ne l'ont pas), la seconde
PROMETTAIT TROP (une garantie que la loi ne donne pas). C'est le même défaut :
un renvoi lu de mémoire au lieu d'être ouvert.

CE QUE LE MODULE FAIT. Il porte, article par article, la version EN VIGUEUR à
la date de vérification, sa place dans le code quand cette place décide de
quelque chose, la proposition vérifiée, et l'adresse où la relire. Il extrait
ensuite les citations réellement présentes dans la page et les confronte à
cette table. Une citation ajoutée sans vérification n'a nulle part où se
cacher ; une entrée dont la citation a disparu de la page non plus.

CE QU'IL NE FAIT PAS. Il ne dit pas si une clause TIENT — cela se juge, et
`outils/verifier_cgv.py` s'en occupe en interrogeant la jurisprudence. Ici on
vérifie seulement que le texte cité existe, dans cette version, et dit ce que
la page lui fait dire.
"""
import os
import re

VERSION = "2026-09-b"

# La date à laquelle chaque article a été ouvert sur librejustice.fr. Elle est
# dans la table parce qu'une vérification sans date ne vaut rien : un code
# change, et « vérifié » sans « quand » ne dit pas si on parle du texte actuel.
VERIFIE_LE = "2026-09-06"

CORPUS = "https://librejustice.fr"


# ── LA PORTÉE DU RENVOI DE L'ARTICLE L221-3, MESURÉE ─────────────────────
# L221-3 étend « les dispositions des sections 2, 3, 6 du présent chapitre ».
# Le présent chapitre est le chapitre Ier du titre II du livre II. Savoir
# quelles sections portent quel numéro n'est pas devinable : il a fallu lire
# l'arborescence du code (titlePath) article par article. Le résultat est
# cohérent, et c'est ce qui le rend crédible — le législateur a étendu au petit
# professionnel l'appareil HORS ÉTABLISSEMENT (sections 2, 3 et 6) et rien de
# l'appareil À DISTANCE (section 4). Les deux constats A et B ci-dessus n'en
# font donc qu'un.
EXTENSION_L221_3 = {
    "2": {"titre": "Obligation d'information précontractuelle",
          "temoin": "L221-5", "etendue": True},
    "3": {"titre": "Dispositions particulières applicables aux contrats "
                   "conclus hors établissement",
          "temoin": "L221-10", "etendue": True},
    "4": {"titre": "Dispositions particulières applicables aux contrats "
                   "conclus à distance",
          "temoin": "L221-13", "etendue": False},
    "6": {"titre": "Droit de rétractation applicable aux contrats conclus à "
                   "distance et hors établissement",
          "temoin": "L221-18", "etendue": True},
}

# Hors du chapitre Ier, le renvoi ne porte pas du tout. Nommé ici parce que
# c'est précisément l'erreur qui avait été commise.
HORS_CHAPITRE = {
    "L224-25-12": "chapitre IV — Règles spécifiques à des contrats ayant un "
                  "objet particulier, section 2 bis, sous-section 4",
    "L611-1": "livre VI — Règlement des litiges, titre Ier",
}


# ── LES QUINZE ARTICLES ──────────────────────────────────────────────────
# `depuis`   : début de la version EN VIGUEUR au jour de la vérification.
# `situe`    : la place dans le code, quand elle décide de quelque chose.
# `dit`      : la proposition vérifiée, dans les termes du texte.
# `porte`    : ce que la page en tire.
# `etendu`   : l'article est-il étendu au professionnel par L221-3 ?
#              True / False pour le code de la consommation, None ailleurs —
#              la question ne se pose pas pour le code civil ni le code de
#              commerce, qui s'appliquent entre professionnels de plein droit.
ARTICLES = {
    "L221-3": {
        "code": "code de la consommation",
        "depuis": "2016-07-01",
        "situe": "chapitre Ier, section 1 — Définitions et champ d'application",
        "dit": "étend les sections 2, 3 et 6 du chapitre aux contrats conclus "
               "HORS ÉTABLISSEMENT entre deux professionnels, dès lors que "
               "l'objet du contrat n'entre pas dans le champ de l'activité "
               "principale du professionnel sollicité et que celui-ci emploie "
               "cinq salariés ou moins",
        "porte": "la réserve annoncée en tête, et le bénéficiaire des "
                 "articles 5 et 6",
        "etendu": None,
        "url": CORPUS + "/texte/code-de-la-consommation/l221-3",
    },
    "L221-1": {
        "code": "code de la consommation",
        "depuis": "2022-05-28",
        "situe": "chapitre Ier, section 1 — Définitions et champ d'application",
        "dit": "le contrat À DISTANCE se conclut sans présence physique "
               "simultanée, par recours exclusif à des techniques de "
               "communication à distance (I, 1°) ; le contrat HORS "
               "ÉTABLISSEMENT suppose au contraire cette présence — au lieu "
               "de conclusion (a), ou à la sollicitation personnelle qui l'a "
               "immédiatement précédée (b), ou lors d'une excursion organisée "
               "(c)",
        "porte": "la condition que le chapeau et l'article 5 ont cessé de "
                 "taire",
        "etendu": None,
        "url": CORPUS + "/texte/code-de-la-consommation/l221-1",
    },
    "L221-18": {
        "code": "code de la consommation",
        "depuis": "2016-07-01",
        "situe": "chapitre Ier, section 6 — Droit de rétractation",
        "dit": "quatorze jours pour se rétracter, sans motif ; le délai court "
               "de la conclusion du contrat pour les prestations de services",
        "porte": "le délai de l'article 5",
        "etendu": True,
        "url": CORPUS + "/texte/code-de-la-consommation/l221-18",
    },
    "L221-25": {
        "code": "code de la consommation",
        "depuis": "2022-05-28",
        "situe": "chapitre Ier, section 6 — Droit de rétractation",
        "dit": "l'exécution avant la fin du délai suppose la demande expresse "
               "du consommateur, et le professionnel lui demande de "
               "reconnaître qu'APRÈS EXÉCUTION ENTIÈRE il n'aura plus le "
               "droit de se rétracter",
        "porte": "le premier des deux consentements recueillis à la caisse",
        "etendu": True,
        "url": CORPUS + "/texte/code-de-la-consommation/l221-25",
    },
    "L221-28": {
        "code": "code de la consommation",
        "depuis": "2022-05-28",
        "situe": "chapitre Ier, section 6 — Droit de rétractation",
        "dit": "le 13° écarte la rétractation pour le contenu numérique sans "
               "support matériel sous TROIS conditions cumulatives : accord "
               "préalable exprès, renoncement exprès, et confirmation de "
               "l'accord fournie conformément au deuxième alinéa de L221-13",
        "porte": "le fondement de la renonciation, et le risque nommé à "
                 "l'article 5",
        "etendu": True,
        "url": CORPUS + "/texte/code-de-la-consommation/l221-28",
    },
    "L224-25-12": {
        "code": "code de la consommation",
        "depuis": "2021-10-01",
        "situe": "chapitre IV, section 2 bis — HORS de la portée de L221-3",
        "dit": "pour un contenu ou service numérique fourni de manière "
               "continue, le professionnel répond des défauts de conformité "
               "qui apparaissent AU COURS DE LA PÉRIODE de fourniture — et "
               "non pendant deux ans",
        "porte": "la garantie de l'article 6, désormais donnée par le vendeur "
                 "et non par la loi",
        "etendu": False,
        "url": CORPUS + "/texte/code-de-la-consommation/l224-25-12",
    },
    "L611-1": {
        "code": "code de la consommation",
        "depuis": "2016-07-01",
        "situe": "livre VI — Règlement des litiges",
        "dit": "la médiation des litiges de la consommation vise les litiges "
               "entre UN CONSOMMATEUR et un professionnel",
        "porte": "l'article 13, qui écarte la médiation faute de "
                 "consommateurs",
        "etendu": False,
        "url": CORPUS + "/texte/code-de-la-consommation/l611-1",
    },
    "1110": {
        "code": "code civil",
        "depuis": "2018-10-01",
        "situe": "",
        "dit": "le contrat d'adhésion comporte un ensemble de clauses NON "
               "NÉGOCIABLES, déterminées à l'avance par l'une des parties",
        "porte": "la qualification que la page se donne à l'article 1",
        "etendu": None,
        "url": CORPUS + "/texte/code-civil/1110",
    },
    "1127-1": {
        "code": "code civil",
        "depuis": "2016-10-01",
        "situe": "",
        "dit": "qui propose par voie électronique met à disposition les "
               "stipulations d'une manière qui permette leur CONSERVATION et "
               "leur REPRODUCTION ; les 1° à 5° énumèrent en outre ce que "
               "l'offre énonce",
        "porte": "l'accessibilité permanente et imprimable, article 1 — le "
                 "premier alinéa, seul non dérogeable entre professionnels "
                 "(1127-3)",
        "etendu": None,
        "url": CORPUS + "/texte/code-civil/1127-1",
    },
    "1127-2": {
        "code": "code civil",
        "depuis": "2016-10-01",
        "situe": "",
        "dit": "le contrat n'est valablement conclu que si le destinataire a "
               "pu vérifier le détail de sa commande et son prix total et "
               "corriger ses erreurs avant de confirmer ; l'auteur de l'offre "
               "accuse réception sans délai injustifié",
        "porte": "le déroulement de la commande, article 4 — le vendeur s'y "
                 "tient alors que 1127-3 lui permettrait d'y déroger",
        "etendu": None,
        "url": CORPUS + "/texte/code-civil/1127-2",
    },
    "1170": {
        "code": "code civil",
        "depuis": "2016-10-01",
        "situe": "",
        "dit": "toute clause qui prive de sa substance l'obligation "
               "essentielle du débiteur est réputée non écrite",
        "porte": "la limite du plafond, article 10",
        "etendu": None,
        "url": CORPUS + "/texte/code-civil/1170",
    },
    "1171": {
        "code": "code civil",
        "depuis": "2018-10-01",
        "situe": "",
        "dit": "dans un contrat d'adhésion, la clause non négociable qui crée "
               "un déséquilibre significatif est réputée non écrite ; "
               "l'appréciation ne porte ni sur l'objet principal ni sur "
               "l'adéquation du prix",
        "porte": "la limite générale posée à l'article 10",
        "etendu": None,
        "url": CORPUS + "/texte/code-civil/1171",
    },
    "1190": {
        "code": "code civil",
        "depuis": "2016-10-01",
        "situe": "",
        "dit": "dans le doute, le contrat d'adhésion s'interprète CONTRE "
               "celui qui l'a proposé",
        "porte": "l'interprétation contre le vendeur, article 1",
        "etendu": None,
        "url": CORPUS + "/texte/code-civil/1190",
    },
    "1604": {
        "code": "code civil",
        "depuis": "1804-03-21",
        "situe": "",
        # LE TEXTE SEUL NE SUFFISAIT PAS. L'article définit la délivrance
        # comme « le transport de la chose vendue en la puissance et
        # possession de l'acheteur » : la CONFORMITÉ n'y est pas écrite. Elle
        # est jugée. La phrase de la page est donc exacte, mais elle repose
        # sur la jurisprudence et non sur la lettre — le distinguer était le
        # seul moyen de savoir si elle tenait.
        "dit": "« manque à son obligation de délivrance le vendeur qui livre "
               "une chose non conforme à la chose convenue » — Cass. 1re civ., "
               "13 février 2019, n° 17-12.580, au visa de l'article 1604",
        "porte": "l'obligation de délivrer un accès conforme, article 6",
        "etendu": None,
        "url": CORPUS + "/texte/code-civil/1604",
        "juge": CORPUS + "/decision/xv1yLXbTyhJ5",
    },
    "1641": {
        "code": "code civil",
        "depuis": "1804-03-16",
        "situe": "",
        "dit": "le vendeur répond des défauts cachés qui rendent la chose "
               "impropre à son usage ou qui diminuent tellement cet usage que "
               "l'acheteur ne l'aurait pas acquise",
        "porte": "la garantie des vices cachés, article 6",
        "etendu": None,
        "url": CORPUS + "/texte/code-civil/1641",
    },
    "L442-1": {
        "code": "code de commerce",
        "depuis": "2026-08-20",
        "situe": "",
        "dit": "engage la responsabilité de son auteur le fait de soumettre "
               "l'autre partie à des obligations créant un déséquilibre "
               "significatif dans les droits et obligations des parties (I, "
               "2°)",
        "porte": "le rappel joint à l'article 1171, article 10",
        "etendu": None,
        "url": CORPUS + "/texte/code-de-commerce/l442-1",
    },
}

# LES DEUX DÉCISIONS QUI TRANCHENT LE CONSTAT A. Elles ont été OUVERTES, pas
# seulement repérées : un aperçu de recherche peut citer l'argument d'une
# partie et non ce que la cour juge.
DECISIONS = {
    "cass-com-23-16.886": {
        "titre": "Cour de cassation, chambre commerciale, 4 septembre 2024, "
                 "n° 23-16.886",
        "tient": "casse le jugement qui avait appliqué le régime des contrats "
                 "à distance entre deux professionnels, et exige du juge "
                 "qu'il recherche d'abord la présence physique simultanée "
                 "avant d'appliquer L221-3",
        "url": CORPUS + "/decision/6mme57BKnDNb",
    },
    "ca-lyon-22-01141": {
        "titre": "Cour d'appel de Lyon, 3e chambre A, 13 novembre 2025, "
                 "n° 22/01141",
        "tient": "applique L221-3 à un contrat conclu hors établissement, "
                 "vérifie les trois conditions l'une après l'autre, et étend "
                 "au professionnel le délai de rétractation prolongé",
        "url": CORPUS + "/decision/amZamF72UKR5",
    },
}


# ── L'EXTRACTION ─────────────────────────────────────────────────────────
# Un article de code se reconnaît à sa forme : « L221-3 », « L224-25-12 »,
# « 1127-1 ». Les articles des présentes conditions, eux, vont de 1 à 15 et
# ne peuvent pas être confondus avec un article du code civil, qui commence à
# 1000. Restent les millésimes — d'où NON_CITATIONS, qui les NOMME au lieu de
# les filtrer en silence : une exception écrite se relit, un filtre muet non.
NON_CITATIONS = {
    "1971": "millésime de la loi n° 71-1130 du 31 décembre 1971 (article 10), "
            "et non un article de code",
}

_ARTICLE = re.compile(r"\bL\.?\s?\d{3}-\d+(?:-\d+)*|(?<![\d\-])1\d{3}(?:-\d+)*(?![\d])")
_BALISE = re.compile(r"<[^>]+>")


def _texte(source):
    """La page débarrassée de ses balises. Une citation coupée par un <strong>
    doit être vue comme une seule."""
    return _BALISE.sub(" ", source)


def citations(source):
    """Les jetons de forme « article de code » présents dans la page."""
    return sorted({m.group(0).replace(". ", "").replace(".", "").replace(" ", "")
                   for m in _ARTICLE.finditer(_texte(source))})


def _chemin_cgv():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "cgv.html")


def lire_cgv():
    with open(_chemin_cgv(), encoding="utf-8") as f:
        return f.read()


def etat(source=None):
    """Ce que la page cite, ce que la table vérifie, et l'écart entre les deux.

    `non_verifies` : cité par la page, absent de la table — une affirmation
                     juridique que personne n'a ouverte.
    `orphelins`    : vérifié dans la table, plus cité par la page — la table
                     dérive du document qu'elle prétend décrire.
    """
    src = lire_cgv() if source is None else source
    citees = citations(src)
    connus = set(ARTICLES) | set(NON_CITATIONS)
    return {
        "version": VERSION,
        "verifie_le": VERIFIE_LE,
        "citees": citees,
        "verifies": sorted(a for a in citees if a in ARTICLES),
        "non_verifies": sorted(a for a in citees if a not in connus),
        "orphelins": sorted(a for a in ARTICLES if a not in citees),
        "nommes_non_citations": sorted(a for a in citees if a in NON_CITATIONS),
    }


def etendu(article):
    """L'article est-il étendu au professionnel par le renvoi de L221-3 ?

    True / False pour le code de la consommation, None quand la question ne se
    pose pas — un texte du code civil ou du code de commerce s'applique entre
    professionnels sans avoir besoin d'être étendu.
    """
    fiche = ARTICLES.get(article)
    return None if fiche is None else fiche.get("etendu")
