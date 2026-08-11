# -*- coding: utf-8 -*-
"""Faire parler les sources — combler les lacunes SANS fabriquer de faits.

CE QUE CE MODULE RÉSOUT

L'état de l'art dit honnêtement ce que ses quatre documents NE disent pas :
pas d'analyse de cycle de vie, pas de donnée européenne de terrain sur l'eau,
pas de retour d'exploitation chiffré sur le refroidissement liquide, rien sur
la fin de vie. Quatre trous nommés — et rien pour les combler. Un lecteur qui
les découvre reste devant une liste de manques.

LE PIÈGE, ET IL EST DE FOND

La valeur de cette section tient à une chose : CHAQUE FAIT PORTE SON AUTEUR, SA
PAGE ET LA NATURE DE SA SOURCE. Son titre le dit — « et qui le dit ».

Une réponse produite par un modèle de langage n'a ni auteur, ni page, ni
éditeur. Elle a un style. Versée au milieu des faits cités, elle emprunte leur
crédit sans en avoir la provenance, et un chiffre plausible assorti d'une
référence plausible est la faute la plus coûteuse qu'un cabinet puisse mettre
dans un dossier client : elle ne se voit qu'au moment où un tiers va vérifier.

TROIS REGISTRES, JAMAIS MÉLANGÉS

  1. CE QUE LE CABINET DÉTIENT DÉJÀ. Une recherche RÉELLE dans la base de
     connaissance. Ce qui en sort porte un titre et un thème : c'est une
     provenance, donc c'est citable. C'est le seul des trois registres qui
     complète VRAIMENT les quatre documents.

  2. UNE LECTURE ASSISTÉE. Ce que le modèle lit dans ces extraits — ce qu'ils
     couvrent, ce qu'ils ne couvrent pas. Marquée comme telle, NON CITABLE, et
     tenue de ne rien affirmer que les extraits ne portent pas. Elle sert à
     gagner du temps de lecture, pas à produire une réponse.

  3. OÙ CHERCHER AU-DEHORS. Des gisements de données ouvertes, NOMMÉS ICI et
     non demandés au modèle. Un modèle interrogé sur « les données ouvertes du
     WUE européen » invente un portail, un jeu de données et un chiffre, tous
     les trois vraisemblables. Cette liste est donc écrite à la main, elle dit
     ce que chaque gisement CONTIENT et ce qu'il ne règle pas, et elle
     n'affirme jamais qu'il a été consulté.

POURQUOI PAS D'ADRESSE WEB. Les gisements sont désignés par leur nom
d'organisme et leur référence durable — « règlement délégué (UE) 2024/1364 »
identifie un texte pour toujours, une adresse ne survit pas à une refonte de
site. Une adresse morte fait douter de la référence, qui, elle, reste juste.
"""
import re

VERSION = "2026-08-a"

# ── LES QUATRE LACUNES, ET PAR QUOI ON LES INSTRUIT ────────────────────────
# `manque` reprend MOT POUR MOT la lacune déclarée par etat_art : un contrôle
# le vérifie au chargement. Deux formulations qui divergent donneraient au
# lecteur deux versions du même trou, et il croirait à deux trous.
LACUNES = {
    "acv": {
        "titre": "Le carbone incorporé, et l'analyse de cycle de vie",
        "manque": "Aucune analyse de cycle de vie au sens d'ISO 14040",
        "question": "Quel est le carbone incorporé d'un centre de données — "
                    "construction, équipements techniques et serveurs — rapporté "
                    "au kilowatt informatique installé, et sur quelle durée "
                    "d'amortissement le rapporter à l'exploitation ?",
        "requete": "analyse de cycle de vie carbone incorporé construction "
                   "serveurs ISO 14040 déclaration environnementale produit",
        "themes": ["Data center / Carbone & analyse de cycle de vie",
                   "Data center / Green Management / Indicateurs & reporting",
                   "Data center / Fournisseurs & fiches techniques"],
        "preuve": "Une ACV conforme à ISO 14040/14044, avec ses frontières de "
                  "système écrites, ou à défaut les déclarations "
                  "environnementales de produit des matériels réellement "
                  "retenus. Un ordre de grandeur générique ne ferme pas cette "
                  "lacune : il la déplace.",
        "gisements": [
            {"organisme": "ADEME", "instrument": "Base Empreinte® (ex-Base Carbone®)",
             "contient": "Des facteurs d'émission par matériau et par poste, "
                         "documentés et datés, utilisables pour reconstituer un "
                         "carbone de construction.",
             "reserve": "Facteurs GÉNÉRIQUES : ils valent pour un ordre de "
                        "grandeur, jamais pour une déclaration produit."},
            {"organisme": "Programmes de déclaration environnementale de produit "
                          "(PEP ecopassport, EPD International)",
             "instrument": "Déclarations environnementales de produit (EPD)",
             "contient": "Le profil environnemental d'un matériel précis, vérifié "
                         "par tierce partie, selon des règles de catégorie.",
             "reserve": "Couverture inégale sur les serveurs et les "
                        "accélérateurs : à demander au fournisseur si la "
                        "déclaration n'est pas publiée."},
            {"organisme": "Commission européenne",
             "instrument": "Règlement (UE) 2019/424 — écoconception des serveurs "
                           "et du stockage",
             "contient": "Des exigences d'efficacité matière : démontabilité, "
                         "disponibilité des micrologiciels, informations à "
                         "fournir par le fabricant.",
             "reserve": "Il impose des informations ; il ne publie pas de "
                        "chiffre de carbone incorporé."},
        ],
        "hors_portee": "Même complète, une ACV ne dit rien du carbone du "
                       "RÉSEAU électrique pendant l'exploitation : c'est l'autre "
                       "moitié du bilan, et elle dépend du contrat de fourniture.",
    },
    "wue": {
        "titre": "L'eau réellement consommée, en Europe",
        "manque": "Aucune donnée de terrain sur le WUE réel des installations "
                  "européennes",
        "question": "Quel WUE mesurent réellement les centres de données "
                    "européens, par famille de refroidissement et par climat, "
                    "et sur quelle période de mesure ?",
        "requete": "WUE water usage effectiveness mesure relevé exploitation "
                   "consommation d'eau refroidissement évaporatif Europe",
        "themes": ["Data center / Eau & stress hydrique",
                   "Data center / Efficacité & indicateurs (PUE, WUE, CUE, ERE)",
                   "Data center / Retours d'exploitation & mesures"],
        "preuve": "Des relevés annuels d'exploitation, sur des sites européens "
                  "nommés, avec le mode de refroidissement et le climat. Une "
                  "valeur de conception ne comble pas cette lacune : c'est "
                  "précisément l'écart entre conception et exploitation qu'on "
                  "cherche.",
        "gisements": [
            {"organisme": "Union européenne",
             "instrument": "Directive (UE) 2023/1791 art. 12 et règlement "
                           "délégué (UE) 2024/1364",
             "perimetre": "Centres de données de 500 kW et plus.",
             "contient": "Le schéma de déclaration annuelle — dont la "
                         "consommation d'eau. C'est le gisement le plus "
                         "directement dirigé sur cette lacune : il est "
                         "européen, il est de terrain, et il est obligatoire.",
             "reserve": "La base se constitue par vagues annuelles et le niveau "
                        "d'agrégation publié conditionne ce qu'on peut en tirer "
                        "par site. À vérifier au moment de l'usage."},
            {"organisme": "ISO / IEC",
             "instrument": "ISO/IEC 30134-9 — Water Usage Effectiveness",
             "contient": "La DÉFINITION normative du WUE et ses frontières de "
                         "mesure.",
             "reserve": "Une définition, pas des données. Elle sert à refuser "
                        "les WUE calculés sur un périmètre différent — c'est-à-"
                        "dire la plupart de ceux qu'on rencontre."},
            {"organisme": "Agence européenne pour l'environnement, Eurostat",
             "instrument": "Indicateurs d'exploitation de la ressource en eau "
                           "(WEI+) et statistiques de prélèvement",
             "contient": "Le stress hydrique du bassin, qui décide si un mètre "
                         "cube consommé est un problème ou non.",
             "reserve": "Renseigne le CONTEXTE, pas la consommation du centre. "
                        "Les deux se lisent ensemble, jamais l'un pour l'autre."},
        ],
        "hors_portee": "Le WUE seul ne dit rien de l'ARBITRAGE eau/énergie : un "
                       "site peut afficher un WUE nul et un PUE dégradé, et "
                       "avoir déplacé le problème sans le réduire.",
    },
    "liquide": {
        "titre": "Le refroidissement liquide, en exploitation",
        "manque": "Aucun retour d'exploitation chiffré sur le refroidissement "
                  "liquide",
        "question": "Quel gain le refroidissement liquide produit-il RÉELLEMENT "
                    "sur des installations en service — sur le PUE, sur l'eau, "
                    "et à quel coût de maintenance et de disponibilité ?",
        "requete": "refroidissement liquide direct-to-chip immersion retour "
                   "d'exploitation mesure PUE maintenance disponibilité",
        "themes": ["Data center / Refroidissement liquide & immersion",
                   "Data center / Retours d'exploitation & mesures",
                   "Data center / Thermique & refroidissement"],
        "preuve": "Des mesures avant / après sur une même installation, ou une "
                  "comparaison entre salles d'un même site. Une comparaison "
                  "entre technologies chez deux exploitants différents ne "
                  "prouve rien : trop de variables bougent en même temps.",
        "gisements": [
            {"organisme": "ASHRAE, Technical Committee 9.9",
             "instrument": "Publications sur les classes d'environnement et le "
                           "refroidissement liquide",
             "contient": "Les classes de température de liquide et les "
                         "conditions d'exploitation admissibles.",
             "reserve": "Cadre de conception. Ne contient pas de retour "
                        "d'exploitation chiffré."},
            {"organisme": "Open Compute Project",
             "instrument": "Spécifications et documents du groupe de travail "
                           "refroidissement",
             "contient": "Des spécifications d'interface et des retours "
                         "d'opérateurs à très grande échelle.",
             "reserve": "Publié par des membres qui déploient : la sélection "
                        "des cas sert aussi une filière. À lire comme un livre "
                        "blanc de fournisseur, pas comme une étude neutre."},
            {"organisme": "Commission européenne, Centre commun de recherche",
             "instrument": "Code de conduite européen sur l'efficacité "
                           "énergétique des centres de données — bonnes "
                           "pratiques",
             "contient": "Des pratiques classées par effet attendu, avec les "
                         "conditions dans lesquelles chacune vaut.",
             "reserve": "Engagement volontaire : les pratiques sont décrites, "
                        "leur effet n'est pas mesuré site par site."},
        ],
        "hors_portee": "Le gain thermique ne dit rien de la CONTRAINTE "
                       "D'EXPLOITATION que le liquide introduit — compétences, "
                       "pièces, procédures d'intervention en salle sous tension.",
    },
    "fin_de_vie": {
        "titre": "La fin de vie et le réemploi des équipements",
        "manque": "Rien sur la fin de vie des équipements ni sur le réemploi",
        "question": "Que deviennent les serveurs et les accélérateurs déposés, "
                    "quelle part est réemployée, et à partir de quelle durée de "
                    "détention le renouvellement accéléré cesse-t-il d'être un "
                    "gain net ?",
        "requete": "fin de vie réemploi reconditionnement DEEE serveurs "
                   "accélérateurs durée de détention renouvellement",
        "themes": ["Data center / Carbone & analyse de cycle de vie",
                   "Data center / Green Management / Politique & objectifs",
                   "Data center / Green Management / Indicateurs & reporting"],
        "preuve": "Une politique de fin de vie chiffrée — taux de réemploi, "
                  "filière de traitement, durée de détention moyenne — ou les "
                  "bordereaux de la filière de traitement.",
        "gisements": [
            {"organisme": "Union européenne",
             "instrument": "Directive 2012/19/UE relative aux déchets "
                           "d'équipements électriques et électroniques (DEEE)",
             "contient": "Les obligations de collecte et de traitement, et les "
                         "responsabilités du détenteur.",
             "reserve": "Fixe des obligations, pas des taux de réemploi "
                        "observés."},
            {"organisme": "ADEME",
             "instrument": "Registre et rapports de la filière DEEE "
                           "professionnels",
             "contient": "Des tonnages collectés et traités par filière, en "
                         "France.",
             "reserve": "Agrégé par filière : ne descend pas au niveau d'un "
                        "parc informatique de centre de données."},
            {"organisme": "Commission européenne",
             "instrument": "Règlement (UE) 2019/424 — exigences de "
                           "démontabilité et d'accès aux micrologiciels",
             "contient": "Ce qui rend un matériel réemployable, ou ne le rend "
                         "pas : sans micrologiciel ni pièces, le réemploi "
                         "n'existe pas.",
             "reserve": "Condition de possibilité du réemploi, pas mesure de "
                        "sa réalité."},
        ],
        "hors_portee": "Le réemploi déplace le matériel, il ne dit rien de "
                       "l'énergie que consommera son second usage — un serveur "
                       "ancien réemployé peut coûter plus, à service rendu égal.",
    },
}

# CE QUE LA LECTURE ASSISTÉE A LE DROIT DE FAIRE, ET RIEN DE PLUS.
# Cette consigne est la moitié du dispositif : sans elle, un modèle à qui l'on
# soumet une lacune la comble — c'est ce qu'on lui a appris à faire.
CONSIGNE_LECTURE = (
    "Tu lis des extraits de la base documentaire d'un cabinet d'ingénierie pour "
    "dire s'ils répondent à une question précise. Tu NE RÉPONDS PAS à la "
    "question toi-même.\n\n"
    "Règles absolues :\n"
    "- N'avance AUCUN chiffre, AUCUNE référence normative et AUCUN nom de "
    "document qui ne figure pas dans les extraits fournis. Si tu ne trouves "
    "rien, écris que les extraits ne répondent pas — c'est une réponse utile, "
    "et c'est la plus fréquente.\n"
    "- N'utilise PAS tes connaissances générales pour compléter : ce document "
    "sert à décider s'il faut aller chercher ailleurs, et un complément de "
    "mémoire fait croire que la recherche est finie.\n"
    "- Pour chaque extrait retenu, cite le titre du document entre crochets.\n"
    "- Termine par « CE QUI RESTE OUVERT » et la liste de ce que les extraits "
    "ne couvrent pas dans la question posée.\n"
    "- Ta réponse n'est PAS citable dans un dossier : elle oriente une "
    "recherche, elle ne l'atteste pas. Écris-la à ce titre."
)

MENTION_NON_CITABLE = (
    "Lecture produite par un modèle de langage à partir des extraits ci-dessus. "
    "Elle n'a ni auteur, ni page, ni éditeur : elle ne se cite pas dans un "
    "dossier. Ce qui se cite, ce sont les documents nommés au-dessus."
)


# Ce qui ressemble a une REPONSE : une consommation, une empreinte, une part.
_VALEUR = r"\d+(?:[.,]\d+)?\s*(?:%|kWh|MWh|GWh|kW|MW|m³|m3|g\s*CO|tCO|litres?)"
# Ce qui ressemble a une reponse MAIS PAS a un seuil de couverture : on retire
# du motif la puissance seule, qui sert a dire qui est concerne.
_RESULTAT = r"\d+(?:[.,]\d+)?\s*(?:%|kWh|MWh|GWh|m³|m3|g\s*CO|tCO|litres?)"


def _verifier():
    fautes = []
    try:
        import etat_art
        declarees = " ".join(etat_art.LACUNES)
    except Exception:                                     # noqa: BLE001
        declarees = None
        fautes.append("etat_art illisible : la coherence des lacunes n'est pas verifiee")
    for cle, l in LACUNES.items():
        for champ in ("titre", "manque", "question", "requete", "preuve",
                      "hors_portee"):
            if not (l.get(champ) or "").strip():
                fautes.append("lacune %s : %s manquant" % (cle, champ))
        if not l.get("themes"):
            fautes.append("lacune %s : aucun theme de recherche" % cle)
        if len(l.get("gisements") or []) < 2:
            fautes.append("lacune %s : moins de deux gisements — un seul "
                          "gisement se lit comme une reponse" % cle)
        # LA LACUNE DOIT ETRE CELLE QUE LA PAGE ANNONCE. Deux formulations qui
        # divergent donneraient au lecteur deux versions du meme trou.
        if declarees is not None and l["manque"] not in declarees:
            fautes.append("lacune %s : son enonce ne figure pas dans "
                          "etat_art.LACUNES — les deux ont diverge" % cle)
        for g in l.get("gisements") or []:
            for champ in ("organisme", "instrument", "contient", "reserve"):
                if not (g.get(champ) or "").strip():
                    fautes.append("lacune %s : gisement sans %s" % (cle, champ))
            # UN GISEMENT NE PORTE PAS DE VALEUR. C'est un endroit ou chercher,
            # pas une reponse : un chiffre glisse dans « contient » serait lu
            # comme un fait sourcé alors que personne n'a ouvert le jeu de
            # donnees.
            #
            # LE SEUIL DE COUVERTURE EST AUTRE CHOSE, ET IL A SON CHAMP. « Les
            # centres de 500 kW et plus » ne repond a aucune question : il dit
            # QUI est dans la base, ce que le lecteur doit savoir avant de s'y
            # fier — un projet de 400 kW n'y figure pas. Melanger les deux
            # obligerait a relacher le garde, et c'est par la que passerait, un
            # jour, une vraie valeur.
            if re.search(_VALEUR, g.get("contient") or ""):
                fautes.append("lacune %s : le gisement « %s » porte une valeur "
                              "chiffree dans « contient » — c'est un endroit ou "
                              "chercher, pas une reponse" % (cle, g["instrument"][:40]))
            if re.search(_RESULTAT, g.get("perimetre") or ""):
                fautes.append("lacune %s : le perimetre du gisement « %s » "
                              "annonce un resultat au lieu d'une couverture"
                              % (cle, g["instrument"][:40]))
    if declarees is not None and len(LACUNES) < len(etat_art.LACUNES):
        fautes.append("des lacunes de etat_art n'ont aucun moyen d'etre "
                      "instruites : %d declarees, %d instruites"
                      % (len(etat_art.LACUNES), len(LACUNES)))
    return fautes


_FAUTES = _verifier()
if _FAUTES:
    raise RuntimeError("lacunes — configuration incoherente : "
                       + " ; ".join(_FAUTES))


def referentiel():
    """Les lacunes et ce par quoi on peut les instruire, sans rien consulter."""
    return {"version": VERSION,
            "lacunes": [dict(l, cle=k) for k, l in LACUNES.items()],
            "mention_non_citable": MENTION_NON_CITABLE}


def get(cle):
    l = LACUNES.get(str(cle or "").strip())
    return dict(l, cle=cle) if l else None


def prompt_lecture(lacune, contexte):
    """(consigne système, demande) pour la lecture assistée des extraits.

    Le contexte arrive DÉJÀ CLOS par garde_ia — c'est build_context qui le
    fait, et cette fonction ne le refait pas : une seconde clôture emboîtée
    apprendrait au modèle que la première n'était pas sérieuse.
    """
    u = ["QUESTION À INSTRUIRE — %s" % lacune["question"], "",
         "CE QUE LES QUATRE SOURCES PUBLIÉES NE DISENT PAS — %s."
         % lacune["manque"], "",
         "CE QUI VAUDRAIT PREUVE — %s" % lacune["preuve"], "",
         contexte or "", "",
         "Dis, en quinze lignes au plus : ce que ces extraits apportent "
         "réellement à la question, en citant les titres entre crochets ; puis "
         "« CE QUI RESTE OUVERT ». Si les extraits ne portent rien d'utile, "
         "dis-le en une phrase et passe directement à ce qui reste ouvert."]
    return CONSIGNE_LECTURE, "\n".join(u)


def sante():
    return {"module": "lacunes", "version": VERSION,
            "lacunes": len(LACUNES),
            "gisements": sum(len(l["gisements"]) for l in LACUNES.values()),
            "problemes": _verifier()}
