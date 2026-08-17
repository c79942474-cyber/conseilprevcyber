# -*- coding: utf-8 -*-
"""Data Center Sustainability & Decarbonisation — le cadre, et ce qu'on en calcule.

CE QUE CE MODULE APPORTE, ET POURQUOI IL EXISTE À PART

La page /datacenter portait un moteur de calcul et rien d'autre : trois
grandeurs couplées, leurs formules, leurs sources. C'est nécessaire et ce n'est
pas une démarche de développement durable — un calcul répond à « combien »,
jamais à « qu'est-ce qu'on vise, comment le prouve-t-on, et qui l'atteste ».

Ces trois questions sont exactement les trois sous-dossiers que la base
documentaire du cabinet range sous « Data center / Green Management » :
politique et objectifs, indicateurs et reporting, certifications et labels. Ce
module les porte, les relie à ce que le moteur calcule DÉJÀ, et nomme ce qu'il
ne calcule pas.

LA RÈGLE QUI GOUVERNE CE FICHIER

Un axe ne se déclare pas tout seul. Chacun cite :
  · le THÈME de la base documentaire qui le nourrit — et ce nom est VÉRIFIÉ
    contre `rag_store.THEMES` au chargement, de sorte qu'un dossier renommé
    fasse tomber le module au lieu de laisser une page pointer dans le vide ;
  · les TEXTES applicables, avec leur référence exacte ;
  · ce que le moteur produit pour cet axe, par la CLÉ du résultat — pas par une
    description qui pourrait décrire autre chose que ce qui sort ;
  · et ce qu'il ne produit pas. Un cadre qui ne dit que ses forces n'est pas un
    cadre, c'est une plaquette.

CE QUE CE MODULE NE FAIT PAS

Il ne sert aucun document. La base documentaire reste réservée aux comptes
connectés : ce sont les pièces de travail du cabinet et de ses clients. La page
publique reçoit le CADRE et la MÉTHODE ; les documents demandent un compte.
Confondre les deux publierait le fonds de commerce.
"""
from datetime import datetime, timezone

VERSION = "2026-08-a"

# La famille de thèmes dont dépend cette page. Écrite une fois.
FAMILLE = "Data center"
RACINE_VERTE = "Data center / Green Management"

# ═══════════════════════════════════════════════════════════════════════════
#  LES TROIS AXES — ceux-là mêmes que les trois sous-dossiers de la base
# ═══════════════════════════════════════════════════════════════════════════

AXES = [
    {
        "cle": "politique",
        "titre": "Politique & objectifs",
        "theme": RACINE_VERTE + " / Politique & objectifs",
        "question": "Qu'est-ce qu'on vise, et à quelle date ?",
        # La première version disait deux fois la même chose : « sans date ni
        # périmètre » puis la liste « ce qui est visé, sur quel périmètre, à
        # quelle échéance » — la deuxième phrase récrivait la première.
        "pourquoi":
            "Un objectif sans date ni périmètre n'engage personne et ne se "
            "vérifie pas. Le premier travail n'est pas technique : écrire la "
            "cible, le périmètre — site seul, ou site et chaîne amont — et "
            "l'échéance. Tout en découle, jusqu'au refroidissement : un "
            "arbitrage entre électricité et eau avant d'être une préférence "
            "technique.",
        "textes": [
            {"nom": "Directive (UE) 2023/1791 sur l'efficacité énergétique, art. 12",
             "porte": "déclaration annuelle obligatoire au-dessus de 500 kW de "
                      "puissance informatique installée ; l'instrumentation doit "
                      "être prévue dès la conception, pas ajoutée après"},
            {"nom": "Règlement délégué (UE) 2024/1364",
             "porte": "le format et les indicateurs de cette déclaration"},
            {"nom": "Climate Neutral Data Centre Pact",
             "porte": "engagement sectoriel VOLONTAIRE — des cibles de PUE, de "
                      "WUE et d'énergie sans carbone. Le verdict n'est pas "
                      "« conforme » mais « dans la cible » ou « à justifier »"},
        ],
        "calcule": [
            {"cle": "conformite", "quoi": "l'assujettissement au reporting européen, "
                                          "calculé depuis la puissance saisie"},
            {"cle": "energie.pue", "quoi": "le PUE, comparé au repère de marché du Pacte"},
        ],
        "non_calcule":
            "La trajectoire elle-même. Aucun moteur ne décide à la place d'une "
            "direction ce qu'elle vise en 2030 : il éclaire le coût de chaque "
            "cible, il ne la fixe pas.",
    },
    {
        "cle": "indicateurs",
        "titre": "Indicateurs & reporting",
        "theme": RACINE_VERTE + " / Indicateurs & reporting",
        "question": "Comment le prouve-t-on, et avec quelle incertitude ?",
        "pourquoi":
            "Quatre indicateurs normalisés : PUE pour l'énergie, WUE pour "
            "l'eau, CUE pour le carbone, ERE pour la chaleur réutilisée. Ils "
            "ne se lisent pas séparément : un PUE excellent obtenu par "
            "évaporation déplace la charge sur le WUE, et un rejet sec "
            "reporte l'eau en amont, sur celle qu'exige l'électricité "
            "supplémentaire. C'est tout l'objet du calcul couplé.",
        "textes": [
            {"nom": "ISO/IEC 30134 (séries -2 PUE, -4 ITEEsv, -5 ITEUsv, -6 ERF, -9 WUE)",
             "porte": "la définition normalisée de chaque indicateur — sans "
                      "laquelle deux chiffres ne se comparent pas"},
            {"nom": "EN 50600-4-2 et -4-3",
             "porte": "PUE et taux d'énergie renouvelable, dans le cadre "
                      "européen des installations"},
            {"nom": "Directive (UE) 2022/2464 (CSRD)",
             "porte": "le rapportage de durabilité, qui exige le carbone "
                      "INCORPORÉ et non le seul carbone d'exploitation"},
        ],
        "calcule": [
            {"cle": "energie", "quoi": "PUE, énergie informatique et totale, "
                                       "avec la pénalité de charge partielle"},
            {"cle": "eau", "quoi": "WUE de site ET WUE de source — celui qui "
                                   "intègre l'eau consommée pour produire "
                                   "l'électricité, toujours supérieur au premier"},
            {"cle": "carbone", "quoi": "CUE et tonnes de CO₂e, sur l'intensité "
                                       "du réseau du pays retenu"},
            {"cle": "chaleur", "quoi": "ERE et ERF — ce que la chaleur fatale "
                                       "valorisée retire au bilan"},
        ],
        "non_calcule":
            "Le carbone incorporé de la construction et des serveurs. Il pèse "
            "lourd et il dépend de choix de lots que ce moteur ne connaît pas ; "
            "l'annoncer chiffré ici serait une précision empruntée.",
    },
    {
        "cle": "certifications",
        "titre": "Certifications & labels",
        "theme": RACINE_VERTE + " / Certifications & labels",
        "question": "Qui l'atteste, et devant qui cela tient-il ?",
        "pourquoi":
            "Un chiffre produit par l'exploitant n'a pas le poids d'un chiffre "
            "audité. Et les référentiels ne se valent pas : certains attestent "
            "un SYSTÈME DE MANAGEMENT — l'organisation s'améliore —, d'autres "
            "une PERFORMANCE mesurée, d'autres un BÂTIMENT à sa livraison. Les "
            "confondre dans un dossier d'appel d'offres se voit immédiatement.",
        "textes": [
            {"nom": "ISO 50001 — management de l'énergie",
             "porte": "atteste un SYSTÈME, pas un niveau de performance"},
            {"nom": "ISO 14001 — management environnemental",
             "porte": "même nature : le processus, pas le résultat"},
            {"nom": "EU Code of Conduct for Data Centres (Energy Efficiency)",
             "porte": "programme volontaire de la Commission — participant ou "
                      "endosseur, avec des pratiques attendues"},
            {"nom": "LEED, BREEAM, HQE",
             "porte": "le BÂTIMENT, à sa conception et à sa livraison — muets "
                      "sur l'exploitation qui suit"},
        ],
        "calcule": [
            {"cle": "conformite", "quoi": "la position vis-à-vis des repères du "
                                          "Pacte, avec le statut « dans la "
                                          "cible » ou « à justifier »"},
        ],
        "non_calcule":
            "L'obtention d'un label. Aucun calcul ne remplace un audit, et "
            "prétendre le contraire exposerait le dossier à la première "
            "vérification.",
    },
]

# ═══════════════════════════════════════════════════════════════════════════
#  CE QUE LA PAGE PUBLIQUE MONTRE, ET CE QU'ELLE RÉSERVE
# ═══════════════════════════════════════════════════════════════════════════

# La phrase disait deux fois la meme opposition : « publier les premieres
# servirait le lecteur » redit ce que « le cadre, la methode et le calcul sont
# ouverts » vient d'etablir. On garde la frontiere et sa RAISON, qui elle ne se
# devine pas : ce qui est ferme l'est parce qu'il appartient aux clients.
OUVERT = (
    "Le cadre, la méthode et le calcul sont ouverts : une étude complète se lance "
    "sans compte, et chaque formule se vérifie. Le compte n'ouvre que les pièces "
    "— base documentaire du cabinet, livrables rédigés, suivi de projet : les "
    "publier reviendrait à publier le travail des clients.")

# ═══════════════════════════════════════════════════════════════════════════
#  CONTRÔLE D'INTÉGRITÉ AU CHARGEMENT
#
#  Les thèmes cités ici sont des chaînes. Un sous-dossier renommé dans la base
#  laisserait la page pointer vers un thème qui n'existe plus — sans erreur,
#  sans trace, et personne ne le verrait avant qu'un lecteur ne le signale. On
#  refuse donc de se charger plutôt que de servir un renvoi mort.
# ═══════════════════════════════════════════════════════════════════════════

def _verifier():
    fautes = []
    try:
        import rag_store
        connus = set(rag_store.THEMES)
    except Exception as e:                                       # noqa: BLE001
        return ["base documentaire illisible : %s" % str(e)[:80]]
    if RACINE_VERTE not in connus:
        fautes.append("thème racine absent : %s" % RACINE_VERTE)
    for a in AXES:
        if a["theme"] not in connus:
            fautes.append("thème absent de la base : %s" % a["theme"])
    # Le nombre compte aussi : un QUATRIÈME sous-dossier ajouté à la base sans
    # être repris ici donnerait une page qui en annonce trois et en oublie un.
    sous = [t for t in connus if t.startswith(RACINE_VERTE + " / ")]
    if len(sous) != len(AXES):
        fautes.append("la base porte %d sous-dossiers verts, ce module en "
                      "décrit %d — ils doivent coïncider : %s"
                      % (len(sous), len(AXES), sorted(sous)))
    return fautes


_FAUTES = _verifier()
if _FAUTES:
    raise RuntimeError("durabilite — cadre incohérent : " + " ; ".join(_FAUTES))


# ═══════════════════════════════════════════════════════════════════════════
#  LECTURE
# ═══════════════════════════════════════════════════════════════════════════

def _cle_presente(etude, chemin):
    """La clé annoncée existe-t-elle VRAIMENT dans un résultat d'étude ?

    C'est ce qui empêche la page de promettre « le moteur calcule ceci pour cet
    axe » d'après une description écrite un jour et jamais revérifiée."""
    noeud = etude
    for p in chemin.split("."):
        if not isinstance(noeud, dict) or p not in noeud:
            return False
        noeud = noeud[p]
    return noeud is not None


def cadre(etude=None):
    """Les trois axes, prêts à afficher.

    Si une étude est fournie, chaque grandeur annoncée est CONFRONTÉE au
    résultat réel : celles qui n'y figurent pas sont marquées, au lieu d'être
    affirmées sur la foi d'un texte.
    """
    axes = []
    for a in AXES:
        calcule = []
        for c in a["calcule"]:
            calcule.append({
                "cle": c["cle"], "quoi": c["quoi"],
                "present": _cle_presente(etude, c["cle"]) if etude else None,
            })
        axes.append({
            "cle": a["cle"], "titre": a["titre"], "theme": a["theme"],
            "question": a["question"], "pourquoi": a["pourquoi"],
            "textes": a["textes"], "calcule": calcule,
            "non_calcule": a["non_calcule"],
        })
    return {
        "version": VERSION,
        "genere": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "racine": RACINE_VERTE,
        "axes": axes,
        "ouvert": OUVERT,
        "avertissement":
            "Ce cadre situe une démarche et relie les calculs aux textes qui les "
            "rendent opposables. Il ne remplace ni un audit, ni une étude "
            "thermique de site, ni un avis d'organisme certificateur.",
    }


def sante():
    return {"module": "durabilite", "version": VERSION,
            "axes": len(AXES),
            "themes": [a["theme"] for a in AXES],
            "textes": sum(len(a["textes"]) for a in AXES),
            "grandeurs_annoncees": sum(len(a["calcule"]) for a in AXES),
            "problemes": _verifier()}
