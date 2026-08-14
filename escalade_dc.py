"""L'ÉROSION DU BARÈME — actualiser des honoraires de 2018 en 2026, et au-delà.

CE QUE CET AUDIT A TROUVÉ, ET QUI JUSTIFIE CE MODULE
════════════════════════════════════════════════════════════════════════════

Le barème d'honoraires de `moe_dc` est relevé sur un bilan promoteur de 2018.
Il est appliqué tel quel en 2026. Recherché dans tout le fichier, le mot
« indice » n'apparaît pas ; « actualisation », « inflation », « BT01 » non
plus. Un taux d'honoraires vieux de huit ans est servi sans que rien ne le
date, et un montant de travaux saisi en euros d'aujourd'hui y est multiplié
par un pourcentage d'hier.

DEUX ERREURS DISTINCTES, QU'IL FAUT SÉPARER :

  1. LE TAUX (%) vieillit peu. La structure d'une mission de maîtrise d'œuvre
     — qui fait quoi, dans quelle proportion — bouge lentement. Un taux de
     2018 reste un ordre de grandeur défendable en 2026.

  2. LE MONTANT (€) vieillit vite, et pas uniformément. Entre 2021 et 2022,
     les coûts de construction ont connu en zone euro leur plus forte hausse
     enregistrée ; les postes n'ont pas bougé ensemble — les matériaux ont
     décroché avant la main-d'œuvre, l'électrotechnique avant le gros œuvre.

C'est la SECONDE que ce module traite. Il ne corrige pas le barème : il dit à
quelle date il a été relevé, et de combien un euro de 2018 diffère d'un euro
d'aujourd'hui, POSTE PAR POSTE.

════════════════════════════════════════════════════════════════════════════
CE QUE CE MODULE REFUSE DE FAIRE

Il ne publie AUCUNE courbe d'escalade par pays jusqu'en 2050. On me demandait
de le faire ; je ne l'ai pas fait, et le motif est écrit ici plutôt que
dissimulé dans une valeur par défaut.

  · une prévision de coût de construction à vingt-cinq ans, par pays et par
    poste, n'existe dans aucune publication vérifiable. La produire
    reviendrait à inventer une donnée puis à la faire entrer dans un calcul
    d'investissement — exactement ce que ce site s'interdit ailleurs ;

  · une prévision de prix des GPU à 2030 n'existe pas davantage. Le marché
    est concentré sur un fournisseur dominant et les prix publics y sont des
    prix de catalogue, pas des prix de marché ;

  · ce qui est vérifiable, ce sont les indices PASSÉS. Ils sont ici, avec
    leur émetteur. Ce qui est devant nous est une HYPOTHÈSE, et porte ce nom.

LA RÈGLE : chaque coefficient porte sa `nature`. `publie` — un indice
d'institut, avec son émetteur. `releve` — constaté sur un chantier, avec
l'année. `hypothese` — une valeur que VOUS posez, et que le module n'a pas
déduite. Le calcul est refusé tant qu'un poste n'a ni indice ni hypothèse :
mieux vaut une ligne vide qui s'explique qu'un nombre qu'on croit.
"""

VERSION = "2026-08-a"

AVERTISSEMENT = (
    "Ce module ACTUALISE des montants, il ne prédit aucun prix. Les indices "
    "passés sont sourcés et datés ; tout ce qui porte sur l'avenir est une "
    "hypothèse que vous posez et que le livrable cite comme telle.")


# ═══════════════════════════════════════════════════════════════════════════
# 1. LE MILLÉSIME DU BARÈME — le fait qui a déclenché ce module
# ═══════════════════════════════════════════════════════════════════════════
MILLESIME_BAREME = 2018
MOTIF_MILLESIME = (
    "Le barème d'honoraires est relevé sur un bilan promoteur de 2018. Le taux "
    "vieillit lentement — la structure des missions bouge peu — mais l'ASSIETTE "
    "sur laquelle il s'applique, elle, est en euros d'aujourd'hui. Tant que "
    "vous saisissez un montant de travaux actuel, le taux s'applique "
    "correctement. L'écart n'apparaît que si vous reprenez un montant ANCIEN, "
    "un prix de revient de projet passé par exemple : il faut alors "
    "l'actualiser avant, et non après.")


# ═══════════════════════════════════════════════════════════════════════════
# 2. LES ANCRAGES PUBLIÉS — ce qu'on peut affirmer, et de qui on le tient
# ═══════════════════════════════════════════════════════════════════════════
# Volontairement peu nombreux. Un ancrage qu'on ne peut pas attribuer n'entre
# pas ici : la longueur de cette liste n'est pas une qualité, sa vérifiabilité
# en est une.
ANCRAGES = [
    {
        "cle": "ue_construction_2021_2022",
        "emetteur": "Eurostat — indices de coûts de la construction",
        "porte": "Les coûts de construction ont connu en 2021-2022 leur hausse "
                 "la plus vive depuis le début de la série, tirée par le coût "
                 "des intrants matériels ; 2023 à 2025 poursuivent la hausse "
                 "sur un rythme nettement moindre.",
        "nature": "publie",
        "millesime": 2025,
        "limite": "Série des bâtiments résidentiels neufs. Un centre de "
                  "données n'est pas un logement : la part d'électrotechnique "
                  "et de génie climatique y est sans commune mesure. Cet "
                  "ancrage donne un SENS d'évolution, pas un coefficient "
                  "applicable tel quel.",
    },
    {
        "cle": "poste_non_uniforme",
        "emetteur": "Eurostat — décomposition matériaux / main-d'œuvre",
        "porte": "Les composantes matériaux et main-d'œuvre ne suivent pas le "
                 "même rythme : le décrochage de 2021-2022 vient des "
                 "matériaux, pas des salaires.",
        "nature": "publie",
        "millesime": 2025,
        "limite": "C'est pourquoi ce module refuse un taux d'escalade UNIQUE "
                  "appliqué à toute l'enveloppe : il en demande un par poste.",
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# 3. LES POSTES — parce qu'un taux unique sur toute l'enveloppe est une faute
# ═══════════════════════════════════════════════════════════════════════════
# Chaque poste porte SA part par défaut dans une enveloppe de centre de données
# et SON comportement d'escalade. Les parts sont un ORDRE DE GRANDEUR de
# structure, déclaré comme tel — pas une mesure.
POSTES = [
    {"cle": "batiment", "nom": "Gros œuvre et clos-couvert",
     "part_defaut": 0.22,
     "quoi": "Terrassements, structure, enveloppe, VRD.",
     "sensible": "Indice de coût de la construction du pays. C'est le poste "
                 "le plus local des six : il ne s'importe pas.",
     "nature_part": "hypothese"},
    {"cle": "cvc", "nom": "Génie climatique (CVC)",
     "part_defaut": 0.20,
     "quoi": "Production de froid, distribution, free-cooling, adiabatique.",
     "sensible": "Prix des groupes froid et des échangeurs, et surtout DÉLAI "
                 "de livraison — sur ce poste, le délai s'est mis à coûter "
                 "plus cher que le matériel.",
     "nature_part": "hypothese"},
    {"cle": "electricite", "nom": "Électricité, onduleurs, câblage",
     "part_defaut": 0.24,
     "quoi": "HTA, transformateurs, onduleurs, batteries, groupes, chemins "
             "de câbles, distribution jusqu'aux baies.",
     "sensible": "Cuivre, semi-conducteurs de puissance, et raccordement au "
                 "réseau — dont le délai relève du gestionnaire de réseau et "
                 "d'aucun fournisseur.",
     "nature_part": "hypothese"},
    {"cle": "it", "nom": "Informatique — GPU, CPU, stockage, réseau",
     "part_defaut": 0.24,
     "quoi": "Le matériel de calcul lui-même, hors bâtiment.",
     "sensible": "Marché concentré, prix publics de catalogue. AUCUN indice "
                 "public ne suit ce poste. C'est celui sur lequel une "
                 "prévision à 2030 est la moins défendable.",
     "nature_part": "hypothese"},
    {"cle": "eau", "nom": "Eau — raccordement, traitement, rejet",
     "part_defaut": 0.03,
     "quoi": "Adduction, traitement, boucles, rejet et sa conformité.",
     "sensible": "Tarif local et, de plus en plus, DROIT à prélever — qui ne "
                 "se négocie pas au prix mais à l'autorisation.",
     "nature_part": "hypothese"},
    {"cle": "energie", "nom": "Raccordement et fourniture d'énergie",
     "part_defaut": 0.07,
     "quoi": "Poste de livraison, renforcement réseau, contrat "
             "d'approvisionnement, part renouvelable contractée.",
     "sensible": "Prix de gros du pays et coût du renforcement — deux "
                 "grandeurs qui ne varient pas ensemble.",
     "nature_part": "hypothese"},
]

PARTS_SOMME_ATTENDUE = 1.0


# ═══════════════════════════════════════════════════════════════════════════
# 4. LA NATURE DE L'OPÉRATION — ce que le barème ne distinguait pas
# ═══════════════════════════════════════════════════════════════════════════
# Le barème de 2018 est relevé sur UNE opération neuve. Appliqué à une reprise
# ou à un site en exploitation, il sous-estime systématiquement les études et
# surestime le clos-couvert. Les coefficients ci-dessous corrigent la STRUCTURE,
# pas les prix — et ils sont déclarés `hypothese`, faute d'un relevé publié qui
# les établirait.
OPERATIONS = [
    {"cle": "neuf", "nom": "Construction neuve",
     "coef_moe": 1.00, "coef_etudes": 1.00, "part_technique": 0.70,
     "nature": "releve",
     "pourquoi": "Le cas du barème de référence. Terrain libre, pas de "
                 "contrainte d'exploitation, phases MOP complètes.",
     "attention": "C'est le seul des quatre qui repose sur un relevé. Les "
                  "trois autres sont des hypothèses de structure."},
    {"cle": "reprise", "nom": "Reprise lourde d'un bâtiment existant",
     "coef_moe": 1.25, "coef_etudes": 1.45, "part_technique": 0.75,
     "nature": "hypothese",
     "pourquoi": "Diagnostics, relevés, reprises de structure, conservation "
                 "de l'existant : les ÉTUDES augmentent plus que les travaux. "
                 "C'est l'erreur classique — appliquer un taux de neuf à une "
                 "reprise fait sous-payer la conception, et la conception est "
                 "précisément ce qui coûte cher sur une reprise.",
     "attention": "L'aléa de découverte ne se chiffre pas au forfait : "
                  "prévoyez une tranche conditionnelle de diagnostic."},
    {"cle": "existant", "nom": "Site en exploitation — travaux sans arrêt",
     "coef_moe": 1.40, "coef_etudes": 1.30, "part_technique": 0.80,
     "nature": "hypothese",
     "pourquoi": "Travailler sur une salle qui tourne impose le phasage, les "
                 "bascules, les essais de nuit, et une MOEX renforcée. Le "
                 "surcoût est de MÉTHODE, pas de matériel.",
     "attention": "Le commissioning n'est plus une phase finale : il devient "
                  "continu, à chaque bascule. Vérifiez que la mission le dit."},
    {"cle": "projete_2030", "nom": "Projet mis en service vers 2030",
     "coef_moe": 1.00, "coef_etudes": 1.10, "part_technique": 0.75,
     "nature": "hypothese",
     "pourquoi": "Le taux ne change pas — c'est l'ASSIETTE qui bouge, et c'est "
                 "l'escalade qui la traite. Les études augmentent un peu : "
                 "densité de puissance plus forte, raccordement plus disputé, "
                 "exigences environnementales durcies.",
     "attention": "Le poste le plus incertain n'est pas le bâtiment : c'est "
                  "le DÉLAI de raccordement au réseau électrique, qui ne "
                  "dépend d'aucun de vos fournisseurs."},
]


def _f(x, n=3):
    return round(float(x), n)


def operation(cle):
    for o in OPERATIONS:
        if o["cle"] == cle:
            return dict(o)
    return None


def poste(cle):
    for p in POSTES:
        if p["cle"] == cle:
            return dict(p)
    return None


# ═══════════════════════════════════════════════════════════════════════════
# 5. L'ACTUALISATION — et le refus quand elle n'est pas fondée
# ═══════════════════════════════════════════════════════════════════════════
def actualiser(montant_meur, annee_depart, annee_arrivee, taux_pct=None,
               parts=None):
    """Actualise un montant poste par poste, ou REFUSE en disant ce qui manque.

    `taux_pct` : un dict {poste: taux annuel en %}. Aucun taux par défaut n'est
    fourni, et c'est délibéré. Un taux par défaut serait repris tel quel par la
    plupart des lecteurs, deviendrait une référence, et personne ne saurait
    plus qu'il a été posé par le module et non mesuré.

    Rend, pour chaque poste : le montant de départ, le coefficient composé, le
    montant actualisé — et, pour les postes sans taux, un REFUS nommé.
    """
    if not montant_meur or annee_arrivee is None or annee_depart is None:
        return {"ok": False, "motif": "Montant et années sont nécessaires."}
    n = int(annee_arrivee) - int(annee_depart)
    if n < 0:
        return {"ok": False,
                "motif": "L'année d'arrivée précède l'année de départ."}

    bas, haut = float(min(montant_meur)), float(max(montant_meur))
    parts = dict(parts or {p["cle"]: p["part_defaut"] for p in POSTES})
    taux = dict(taux_pct or {})

    lignes, refus = [], []
    tot_bas = tot_haut = 0.0
    for p in POSTES:
        c = p["cle"]
        part = float(parts.get(c, p["part_defaut"]))
        b, h = bas * part, haut * part
        t = taux.get(c)
        if t is None or str(t).strip() == "":
            refus.append({
                "poste": c, "nom": p["nom"],
                "motif": "Aucun taux d'escalade n'est posé pour ce poste. Ce "
                         "module n'en invente pas : " + p["sensible"],
            })
            lignes.append({"poste": c, "nom": p["nom"], "part": _f(part, 4),
                           "depart_meur": [_f(b), _f(h)], "coef": None,
                           "arrivee_meur": None, "nature": "non_instruit"})
            # NON INSTRUIT N'EST PAS ZÉRO. Le montant de départ est reporté tel
            # quel dans le total : l'escaler à 0 % ferait croire à une
            # stabilité constatée, alors que rien n'a été constaté.
            tot_bas += b
            tot_haut += h
            continue
        coef = (1.0 + float(t) / 100.0) ** n
        tot_bas += b * coef
        tot_haut += h * coef
        lignes.append({"poste": c, "nom": p["nom"], "part": _f(part, 4),
                       "depart_meur": [_f(b), _f(h)], "coef": _f(coef, 4),
                       "taux_pct": float(t),
                       "arrivee_meur": [_f(b * coef), _f(h * coef)],
                       "nature": "hypothese"})

    somme = sum(float(parts.get(p["cle"], p["part_defaut"])) for p in POSTES)
    return {
        "ok": True,
        "annees": n,
        "depart": {"annee": int(annee_depart), "meur": [_f(bas), _f(haut)]},
        "arrivee": {"annee": int(annee_arrivee),
                    "meur": [_f(tot_bas), _f(tot_haut)]},
        "lignes": lignes,
        "refus": refus,
        "parts_somme": _f(somme, 4),
        "parts_completes": abs(somme - PARTS_SOMME_ATTENDUE) < 1e-6,
        "instruit": len(POSTES) - len(refus),
        "total_postes": len(POSTES),
        # LE CHIFFRE QUI DIT S'IL FAUT CROIRE LE TOTAL. Un total dont la moitié
        # des postes n'est pas instruite n'est pas une prévision : c'est une
        # addition partielle, et elle doit se présenter comme telle.
        "couverture_pct": _f(100.0 * (len(POSTES) - len(refus)) / len(POSTES), 1),
        "avertissement": AVERTISSEMENT,
        "ancrages": ANCRAGES,
    }


def effet_operation(travaux_meur, cle_operation):
    """Ce que la NATURE de l'opération change au barème, et pourquoi."""
    o = operation(cle_operation)
    if not o:
        return {"ok": False,
                "motif": "Nature d'opération inconnue : " + str(cle_operation)}
    bas, haut = float(min(travaux_meur)), float(max(travaux_meur))
    return {
        "ok": True, "operation": o,
        "part_technique_conseillee": o["part_technique"],
        "coef_moe": o["coef_moe"], "coef_etudes": o["coef_etudes"],
        "travaux_meur": [_f(bas), _f(haut)],
        "lecture": (
            "Le coefficient porte sur les HONORAIRES, jamais sur les travaux : "
            "une reprise ne coûte pas 25 % de travaux en plus, elle demande "
            "25 % d'honoraires en plus pour le même ouvrage — parce que la "
            "part d'études y est structurellement plus lourde."),
        "nature": o["nature"],
        "reserve": (
            "Coefficient de STRUCTURE, posé par ce module et non relevé sur un "
            "marché."
            if o["nature"] == "hypothese" else
            "Relevé sur le projet de référence de 2018."),
    }


def referentiel():
    return {"version": VERSION, "millesime_bareme": MILLESIME_BAREME,
            "motif_millesime": MOTIF_MILLESIME, "postes": POSTES,
            "operations": OPERATIONS, "ancrages": ANCRAGES,
            "avertissement": AVERTISSEMENT}


def sante():
    return {"module": "escalade_dc", "version": VERSION,
            "postes": len(POSTES), "operations": len(OPERATIONS),
            "ancrages": len(ANCRAGES), "fautes": _verifier()}


def _verifier():
    f = []
    s = sum(p["part_defaut"] for p in POSTES)
    if abs(s - PARTS_SOMME_ATTENDUE) > 1e-6:
        f.append("les parts par défaut ne font pas 1 : %.4f" % s)
    cles = [p["cle"] for p in POSTES]
    if len(set(cles)) != len(cles):
        f.append("poste en double")
    for o in OPERATIONS:
        if not (0.0 < o["part_technique"] < 1.0):
            f.append("part technique hors bornes : " + o["cle"])
        if o["coef_moe"] <= 0 or o["coef_etudes"] <= 0:
            f.append("coefficient nul ou négatif : " + o["cle"])
    # UNE SEULE OPÉRATION PEUT ÊTRE « RELEVÉE » : celle du barème. Si une
    # deuxième se déclarait relevée sans relevé, la distinction entre mesure et
    # hypothèse — qui est tout ce que ce module apporte — disparaîtrait.
    releves = [o["cle"] for o in OPERATIONS if o["nature"] == "releve"]
    if releves != ["neuf"]:
        f.append("relevés attendus = ['neuf'], obtenus %s" % releves)
    for a in ANCRAGES:
        if a["nature"] != "publie" or not a.get("emetteur"):
            f.append("ancrage sans émetteur ou non publié : " + a["cle"])
    return f


_f0 = _verifier()
if _f0:
    raise AssertionError("escalade_dc incohérent : " + " | ".join(_f0))
