# -*- coding: utf-8 -*-
"""LE CYCLE DE VIE D'UNE MISSION DE CONSEIL — dans quel ordre, et pourquoi.

CE QUE CE MODULE AJOUTE AU CATALOGUE DE LIVRABLES

`livrables.py` compte quatre-vingt-cinq livrables et les range par DOMAINE :
operating model, maturité, feuille de route, continuité, architecture. Ce
classement répond à « de quoi parle ce document ». Il ne répond pas à la
question que pose un consultant qui démarre : « par quoi je commence, et
qu'est-ce que je ne peux pas écrire tant que je n'ai pas écrit autre chose ».

CE QUE LE DÉFAUT COÛTAIT, ET IL SE CONSTATE. `PAGES_CONSEIL` est une liste
PLATE de huit domaines, présentés côte à côte comme s'ils étaient
interchangeables. Ils ne le sont pas : un operating model cible écrit avant le
diagnostic organisationnel décrit une organisation qu'on n'a pas regardée, et
une feuille de route écrite avant l'analyse d'écarts séquence des actions dont
on ignore l'ampleur. Ces deux fautes-là ne se voient pas à la relecture du
livrable — il est bien écrit, il est complet, et il est faux.

CE QUE CE MODULE NE FAIT PAS, ET C'EST DÉLIBÉRÉ

IL N'INTERDIT RIEN. Une mission réelle commence rarement au début : on arrive
en cours de programme, une partie du travail est faite, le client a déjà un
radar de maturité vieux de deux ans. Un parcours qui refuserait d'avancer
serait abandonné au premier dossier. Il DIT ce qui manque et ce que cela coûte
— la décision reste au consultant.

IL NE CALCULE AUCUNE DURÉE. Une phase ne dure pas « trois semaines » : elle
dure le temps qu'il faut pour obtenir les entretiens. Afficher un délai serait
une promesse que rien ne tient, et c'est le genre de chiffre qu'un client
retient.

LE PARCOURS EST BÂTI SUR LES LIVRABLES EXISTANTS, JAMAIS SUR UNE LISTE
PARALLÈLE. Chaque phase nomme des identifiants du catalogue, et
`verifier_le_catalogue()` confronte les deux : un livrable renommé ou retiré
fait tomber une règle plutôt que de laisser une phase promettre un document
qui n'existe plus. C'est la leçon de `ecart_referentiel` — une carte qui ne
peut pas se tromper est une carte qu'on ne peut pas croire.
"""
import reglages

VERSION = "2026-09-a"

#: Ce qu'une phase peut manquer, et ce que ce manque coûte à la suivante.
#
# LE MOTIF EST ÉCRIT ICI, PAS DANS L'ÉCRAN. Un écran qui dit « prérequis
# manquant » ne dit rien : c'est la CONSÉQUENCE qui fait décider. Chacune de
# ces phrases nomme ce qui arrive si l'on passe outre, et elles viennent
# toutes d'une faute qu'on peut commettre sans s'en apercevoir.
PHASES = [
    {
        "cle": "cadrage",
        "titre": "Cadrage de la mission",
        "question": "Sur quoi porte la mission, et qu'est-ce qui en sortira ?",
        "livrables": ["cadrage-amoa", "cadrage-amoa-ia-cyber"],
        "prealables": [],
        "ce_qui_se_decide": "Le périmètre — sites, systèmes, fonctions — et "
                            "les instances qui arbitreront. Un périmètre non "
                            "arrêté se renégocie à chaque restitution.",
        "piege": "Le périmètre annoncé par le client est presque toujours plus "
                 "large que ce qu'il finance. L'écrire tôt évite de découvrir "
                 "à la restitution qu'on a évalué trois sites sur douze.",
    },
    {
        "cle": "etat_des_lieux",
        "titre": "État des lieux",
        "question": "Qu'est-ce qui existe déjà, et qu'est-ce qui tient ?",
        "livrables": ["revue-dispositif-ot", "diag-organisationnel-ot",
                      "carto-exposition"],
        "prealables": ["cadrage"],
        "ce_qui_se_decide": "Ce qu'on reprend et ce qu'on refait. Et qui "
                            "décide aujourd'hui, ce qui n'est presque jamais "
                            "ce que l'organigramme annonce.",
        "piege": "On arrive après d'autres. Ignorer ce qui a déjà été payé — "
                 "un outil acheté et non déployé, un référentiel écrit et non "
                 "appliqué — fait proposer une deuxième fois ce qui a déjà "
                 "échoué une première.",
    },
    {
        "cle": "evaluation",
        "titre": "Évaluation et écarts",
        "question": "Où en est-on, contre quel référentiel, et de combien ?",
        "livrables": ["mat-radar", "ecarts-62443", "analyse-ecarts-nis2",
                      "mat-carto-ecarts", "mat-benchmark", "analyse-risque"],
        "prealables": ["cadrage", "etat_des_lieux"],
        "ce_qui_se_decide": "Le niveau atteint, le niveau visé, et l'écart "
                            "entre les deux — par domaine et par zone.",
        "piege": "Un niveau de maturité se DÉCLARE contre des descriptions "
                 "concrètes ; il ne se calcule pas en comptant des cases "
                 "cochées. Un chiffre obtenu par comptage se défend mal "
                 "devant une direction industrielle qui connaît ses ateliers.",
    },
    {
        "cle": "cible",
        "titre": "Cible et operating model",
        "question": "À quoi ressemble le dispositif qu'on veut, et qui le tient ?",
        "livrables": ["om-operating-model", "om-charte-gouvernance",
                      "om-raci-roles", "om-cartographie-processus",
                      "om-comitologie-reporting", "dossier-architecture-ot",
                      "sr-interface-surete-securite", "pssi-ot"],
        "prealables": ["etat_des_lieux", "evaluation"],
        "ce_qui_se_decide": "La gouvernance, les rôles, les processus et les "
                            "interfaces IT/OT/engineering/opérations/sûreté.",
        "piege": "Une cible écrite sans le diagnostic organisationnel décrit "
                 "une organisation qu'on n'a pas regardée : elle sera juste "
                 "sur le papier et inapplicable dans l'atelier.",
    },
    {
        "cle": "trajectoire",
        "titre": "Trajectoire et feuille de route",
        "question": "Dans quel ordre, avec quels moyens, et pour quel gain ?",
        "livrables": ["fdr-pluriannuelle", "roadmap-cyber",
                      "fdr-trajectoire-conformite", "fdr-business-case",
                      "fdr-plan-charge-budget", "plan-remediation",
                      "om-plan-transition", "mat-plan-montee"],
        "prealables": ["evaluation", "cible"],
        "ce_qui_se_decide": "Les jalons, les streams, la charge et le budget. "
                            "Et ce qu'on ne fera pas.",
        "piege": "Une feuille de route écrite avant l'analyse d'écarts "
                 "séquence des actions dont on ignore l'ampleur : les six "
                 "premiers mois tiennent, la suite dérive.",
    },
    {
        "cle": "decision",
        "titre": "Décision et engagement",
        "question": "Qui décide, sur quoi, et qu'est-ce qui est acté ?",
        "livrables": ["mat-restitution-comex", "atelier-direction",
                      "fdr-business-case"],
        "prealables": ["trajectoire"],
        "ce_qui_se_decide": "L'engagement des moyens, et le mandat de la "
                            "fonction OT Security.",
        "piege": "Un atelier de direction sans relevé de décisions opposable "
                 "produit un consensus qui s'évapore : trois mois plus tard, "
                 "chacun se souvient d'un arbitrage différent.",
    },
    {
        "cle": "execution",
        "titre": "Exécution et pilotage",
        "question": "Où en est-on, et qu'est-ce qui dérape ?",
        "livrables": ["reporting-programme", "fdr-tableau-bord",
                      "procedure-moc", "moc-formulaire-impact",
                      "moc-registre-revue", "deploiement-sonde-ot",
                      "referentiel-durcissement", "pca-pra-ot",
                      "politique-sauvegarde-configs"],
        "prealables": ["decision"],
        "ce_qui_se_decide": "Le rythme de pilotage, les indicateurs, et les "
                            "mécanismes d'exécution — dont la gestion des "
                            "changements, qui est l'endroit où un dispositif "
                            "OT se perd le plus vite.",
        "piege": "Un tableau de bord dont les indicateurs ne sont pas "
                 "collectables devient un rituel de remplissage : on mesure "
                 "ce qui est facile plutôt que ce qui compte.",
    },
    {
        "cle": "transfert",
        "titre": "Transfert et autonomie",
        "question": "Le client sait-il tenir le dispositif sans nous ?",
        "livrables": ["form-programme-profils", "form-evaluation-habilitations",
                      "plan-montee-competence", "exercice-crise-ot",
                      "sensibilisation"],
        "prealables": ["execution"],
        "ce_qui_se_decide": "Les compétences transférées, et la preuve "
                            "qu'elles le sont — un exercice de crise conduit "
                            "par le client, pas par nous.",
        "piege": "Une mission qui se termine sans transfert laisse un "
                 "dispositif qui fonctionne tant que le consultant est là. "
                 "C'est la forme la plus coûteuse de l'échec, parce qu'elle "
                 "ne se voit qu'après le départ.",
    },
]

#: Combien de phases au plus peuvent être déclarées faites d'un coup.
#
# POURQUOI UNE BORNE. Une reprise de mission en cours peut légitimement
# déclarer plusieurs phases acquises. Toutes les déclarer d'un coup, en
# revanche, revient à dire qu'on n'a rien à faire — et c'est le signe d'un
# formulaire rempli sans être lu, pas d'une mission avancée.
FAITES_MAX = reglages.entier("MISSION_FAITES_MAX", len(PHASES) - 1, mini=1,
                             maxi=len(PHASES))


def _index():
    return {p["cle"]: p for p in PHASES}


def verifier_le_catalogue():
    """Les livrables nommés par les phases existent-ils vraiment ?

    UNE CARTE QUI NE PEUT PAS SE TROMPER EST UNE CARTE QU'ON NE PEUT PAS
    CROIRE. Ce parcours nomme des identifiants du catalogue ; un livrable
    renommé ou retiré laisserait ici une promesse morte — une phase qui
    annonce un document qu'aucune console ne sait produire. Rend la liste des
    identifiants introuvables, vide quand tout va bien.
    """
    import livrables                                              # noqa: PLC0415
    connus = {t["id"] for t in livrables.TYPES}
    manquants = []
    for p in PHASES:
        for lid in p["livrables"]:
            if lid not in connus:
                manquants.append((p["cle"], lid))
    return manquants


def etat(faites=None):
    """Où en est la mission, et ce que la phase suivante exige.

    FONCTION PURE : l'état est passé, jamais lu quelque part. Une règle
    l'éprouve sans base ni session.

    ELLE NE BLOQUE RIEN. Chaque phase porte `prete` — tous ses préalables
    sont déclarés faits — et `manque`, qui NOMME ce qui manque. On peut
    travailler une phase qui n'est pas prête ; on sait alors sur quoi on
    s'avance, et le piège de la phase le dit.
    """
    # UNE LISTE, ET RIEN D'AUTRE.
    #
    # `for x in (faites or [])` acceptait n'importe quel itérable : un
    # dictionnaire `{"cadrage": 1}` se lisait par ses CLÉS, et « cadrage »
    # devenait une phase faite. Personne ne l'avait décidé — c'est une
    # souplesse qui vient de Python, pas du contrat. Une chaîne, elle, se lit
    # caractère par caractère et ne donnait rien, ce qui masquait le premier
    # cas. Ma propre règle l'a trouvé.
    if not isinstance(faites, (list, tuple)):
        faites = []
    faites = {str(x) for x in faites if str(x) in _index()}
    lignes = []
    for p in PHASES:
        manque = [c for c in p["prealables"] if c not in faites]
        lignes.append({
            "cle": p["cle"],
            "titre": p["titre"],
            "question": p["question"],
            "faite": p["cle"] in faites,
            "prete": not manque,
            "manque": [{"cle": c, "titre": _index()[c]["titre"]}
                       for c in manque],
            "livrables": list(p["livrables"]),
            "ce_qui_se_decide": p["ce_qui_se_decide"],
            "piege": p["piege"],
        })
    # LA PHASE COURANTE EST LA PREMIÈRE NON FAITE, ET NON LA PREMIÈRE PRÊTE.
    # Prendre la première prête ferait sauter une phase qu'on a commencée et
    # pas finie — et c'est justement celle sur laquelle il faut revenir.
    courante = next((l for l in lignes if not l["faite"]), None)
    return {
        "version": VERSION,
        "phases": lignes,
        "courante": courante["cle"] if courante else None,
        "faites": sorted(faites),
        "achevee": courante is None,
        # CE QUI EST PROMIS ET QUI N'EXISTE PAS SORT AVEC L'ÉTAT. Sans cela,
        # une phase annoncerait un livrable retiré du catalogue et l'écran
        # afficherait un bouton qui ne mène nulle part.
        "promesses_mortes": [{"phase": c, "livrable": l}
                             for c, l in verifier_le_catalogue()],
    }


def livrables_de_phase(cle):
    """Les livrables d'une phase, tels que le catalogue les décrit.

    ON LIT LE CATALOGUE, ON NE RECOPIE PAS SES INTITULÉS. Deux tables des
    mêmes libellés divergent au premier renommage, et c'est la page qui
    afficherait alors un titre que plus aucune console ne porte.
    """
    import livrables                                              # noqa: PLC0415
    p = _index().get(str(cle or ""))
    if not p:
        return []
    out = []
    for lid in p["livrables"]:
        t = livrables.get_type(lid)
        if t:
            out.append({"id": lid, "label": t.get("label") or "",
                        "groupe": t.get("groupe") or "",
                        "desc": t.get("desc") or ""})
    return out


def phase_du_livrable(livrable_id):
    """La phase où ce livrable se produit — ou None.

    UN LIVRABLE PEUT SERVIR DANS PLUSIEURS PHASES ; on rend la PREMIÈRE, qui
    est celle où il se produit. Le business case est arbitré en décision, mais
    il s'écrit à la trajectoire : c'est là qu'il faut l'ouvrir.
    """
    for p in PHASES:
        if livrable_id in p["livrables"]:
            return p["cle"]
    return None
