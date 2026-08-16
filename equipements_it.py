"""Les équipements informatiques d'un centre de données : quantités, prix,
carbone de cycle de vie (scope 3) — et le levier de la durée de vie.

MODULE PARTAGÉ À L'IDENTIQUE entre conseilprevcyber et conseilprev
(Sentinel), comme moe_dc : l'enveloppe d'investissement et l'empreinte
environnementale doivent lire les MÊMES quantités. Deux nomenclatures pour
un même projet, c'est un écart qui se découvre en comité.

LE POINT DE PÉRIMÈTRE QUI COMMANDE TOUT
───────────────────────────────────────
L'enveloppe d'investissement d'un centre de données — celle que calcule
`finance_dc`, quatorze lots du foncier aux essais — NE CONTIENT PAS les
équipements informatiques. Le lot « aménagement des salles » couvre les
baies, le câblage et la distribution terminale ; les serveurs, le stockage
et les commutateurs sont un investissement SÉPARÉ.

Ce n'est pas un oubli, c'est le partage habituel des responsabilités :

  · en COLOCATION, l'exploitant construit la coque et les infrastructures,
    le client apporte ses machines. L'IT n'est ni dans son enveloppe, ni
    dans son bilan carbone d'exploitation — mais il est dans celui du
    client, et personne ne le porte si les deux se renvoient la balle ;
  · en centre PROPRE — entreprise, hyperscale —, les deux budgets sont
    portés par la même entité. L'IT pèse alors autant que le bâtiment, et
    l'ignorer sous-estime l'investissement total de moitié.

Le module rend donc DEUX pourcentages : la part de l'IT dans l'enveloppe
travaux (souvent zéro, et c'est juste), et sa part dans l'investissement
TOTAL du projet (bâtiment + IT), qui est le chiffre qu'un comité attend.

LE LEVIER : PROLONGER LA DURÉE DE VIE — ET SON POINT DE BASCULE
Allonger la durée de vie d'un serveur divise son carbone de fabrication par
le nombre d'années où il sert, et évite la fabrication d'un remplaçant. Le
gain est réel et immédiat. MAIS il n'est pas infini : un matériel ancien
consomme davantage à service rendu égal, et cette surconsommation finit par
annuler le gain. Le point de bascule dépend de l'intensité carbone du
réseau — sur un mix décarboné, prolonger reste payant très longtemps ; sur
un mix charbon, beaucoup moins. Le module le CALCULE plutôt que de
recommander « prolongez » sans réserve, ce qui serait de la plaquette.

Aucun modèle de langage n'intervient : deux dimensionnements identiques
rendent le même résultat.
"""

VERSION = "2026-08-a"

# L'INTENSITÉ CARBONE ET LE CARBONE INCORPORÉ SE LISENT AU MOTEUR LOCAL.
# Les deux sites ne portent pas le même : conseilprevcyber a `datacenter`,
# Sentinel a `empreinte_sites`. Recopier une table ici en ferait une TROISIÈME
# vérité, qui divergerait des deux autres au premier ajustement — et c'est
# celle-là que le lecteur verrait.
#
# Les deux référentiels ne s'accordent d'ailleurs pas exactement : la France
# vaut 56 g/kWh d'un côté (millésime réseau) et 45 de l'autre (séries Ember,
# approche production). L'écart est réel, documenté par chacun, et il ne se
# moyenne pas ici. Chaque site répond avec SON chiffre, et le module dit
# lequel il a lu.
_D = None
_MOTEUR = None
try:
    import datacenter as _D             # conseilprevcyber
    _MOTEUR = "datacenter"
except Exception:                       # noqa: BLE001
    try:
        import empreinte_sites as _D    # conseilprev / Sentinel
        _MOTEUR = "empreinte_sites"
    except Exception:                   # noqa: BLE001 — utilisable seul
        _D = None


def _intensite_pays(code):
    """L'intensité carbone du réseau, lue au moteur local — ou rien.

    Rendre None plutôt qu'une moyenne : le verdict de l'allongement dépend
    ENTIÈREMENT de ce chiffre, et une valeur de repli silencieuse ferait
    conclure sur un pays qu'on n'a pas.
    """
    if _D is None:
        return None
    c = str(code or "").upper()
    for nom in ("INTENSITE_RESEAU", "INTENSITE"):
        table = getattr(_D, nom, None)
        if isinstance(table, dict) and c in table:
            try:
                return float(table[c])
            except (TypeError, ValueError):
                return None
    return None


def pays_connus():
    """Les pays dont le moteur local publie l'intensité carbone."""
    if _D is None:
        return []
    for nom in ("INTENSITE_RESEAU", "INTENSITE"):
        table = getattr(_D, nom, None)
        if isinstance(table, dict) and table:
            return sorted(table)
    return []


def _fr(x, dec=None):
    if x is None:
        return "—"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if dec is None:
        dec = 0 if abs(v) >= 100 else (1 if abs(v) >= 10 else 2)
    s = ("%%.%df" % dec) % v
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s.replace(".", ",")


# ═══════════════════════════════════════════════════════════════════════════
#  1. LA NOMENCLATURE — dimensionnée par la puissance informatique
#
#  Chaque poste porte :
#   · sa RÈGLE de quantité, écrite et vérifiable — pas un nombre sorti d'un
#     tableur dont personne ne retrouve l'auteur ;
#   · son caractère INDISPENSABLE ou non : sans les indispensables, la salle
#     ne sert à rien le jour de la mise en service. Les « utiles » améliorent
#     l'exploitation et se négocient ;
#   · son prix unitaire indicatif, à ±40 % — un ordre de grandeur d'étude,
#     à remplacer par les devis ;
#   · son carbone de fabrication (scope 3, catégories 1 et 2 du GHG
#     Protocol) et sa durée de vie usuelle.
# ═══════════════════════════════════════════════════════════════════════════

# Densité par baie, en kW. Le paramètre qui commande TOUT le dimensionnement :
# à 5 kW/baie il faut quatre fois plus de baies qu'à 20, et le nombre de baies
# commande les PDU, le câblage, les commutateurs de rangée et la surface.
DENSITES = {
    "classique": {"kw_baie": 5.0, "nom": "Classique (hébergement mixte)",
                  "note": "Densité courante des salles d'entreprise et de "
                          "colocation de génération précédente."},
    "dense": {"kw_baie": 12.0, "nom": "Dense (calcul et virtualisation)",
              "note": "Salles modernes à confinement, refroidissement à air "
                      "maîtrisé."},
    "ia_air": {"kw_baie": 40.0, "nom": "IA refroidie à l'air",
               "note": "Serveurs accélérés en refroidissement à air : la "
                       "limite pratique de l'air se situe dans cette zone."},
    "ia_liquide": {"kw_baie": 100.0, "nom": "IA à refroidissement liquide",
                   "note": "Plaques froides ou immersion : au-delà de "
                           "50 kW/baie, l'air ne suffit plus."},
}
DENSITE_DEFAUT = "dense"

INCERTITUDE_PRIX = 0.40      # ±40 % : un ordre de grandeur d'étude amont
INCERTITUDE_CARBONE = 0.50   # ±50 % : idem pour les facteurs sectoriels

POSTES = [
    {
        "cle": "baies",
        "nom": "Baies informatiques (racks 42-48 U)",
        "indispensable": True,
        "regle": "Puissance informatique / densité retenue par baie",
        "unite": "baie",
        "prix_unitaire": 1800,
        "carbone_kg": 600,
        "duree_vie": 15,
        "pourquoi": "Sans baie, rien ne s'installe. C'est aussi le poste qui "
                    "fixe la surface de salle et donc le gros œuvre.",
        "achat_durable": "Acier recyclé, démontabilité, réemploi des baies "
                         "existantes lors d'une reprise de site : une baie se "
                         "réemploie presque toujours, et c'est le geste le "
                         "plus rentable de la liste.",
    },
    {
        "cle": "serveurs",
        "nom": "Serveurs (calcul)",
        "indispensable": True,
        "regle": "Puissance informatique × part calcul / puissance unitaire",
        "unite": "serveur",
        "prix_unitaire": 9000,
        "carbone_kg": None,          # lu dans datacenter.INCORPORE
        "duree_vie": None,           # idem : une seule vérité
        "pourquoi": "Le cœur du service rendu — et le poste dont la durée de "
                    "vie décide de l'essentiel du carbone incorporé.",
        "achat_durable": "Exiger l'empreinte produit (PCF) du constructeur, "
                         "une garantie étendue au-delà de cinq ans, la "
                         "disponibilité des pièces, et évaluer le "
                         "reconditionné sur les usages qui le supportent.",
    },
    {
        "cle": "stockage",
        "nom": "Baies de stockage et disques",
        "indispensable": True,
        "regle": "Puissance informatique × part stockage / puissance unitaire",
        "unite": "châssis",
        "prix_unitaire": 22000,
        "carbone_kg": 2200,
        "duree_vie": 6,
        "pourquoi": "Indissociable du calcul : un serveur sans stockage "
                    "accessible ne rend aucun service.",
        "achat_durable": "Le stockage se prolonge mieux que le calcul — ses "
                         "performances vieillissent moins vite. C'est le "
                         "poste où l'allongement se négocie le plus "
                         "facilement.",
    },
    {
        "cle": "reseau_tor",
        "nom": "Commutateurs de baie (top-of-rack)",
        "indispensable": True,
        "regle": "Deux par baie — la redondance n'est pas une option sur le "
                 "réseau d'accès",
        "unite": "commutateur",
        "prix_unitaire": 12000,
        "carbone_kg": 900,
        "duree_vie": 8,
        "pourquoi": "Deux et non un : un commutateur d'accès unique fait de "
                    "chaque baie un point de défaillance unique, ce qui ruine "
                    "toute prétention de niveau de disponibilité.",
        "achat_durable": "Durée de vie longue et bien supportée par les mises "
                         "à jour logicielles : c'est le poste où le "
                         "remplacement est le plus souvent commercial plutôt "
                         "que technique.",
    },
    {
        "cle": "reseau_coeur",
        "nom": "Commutateurs de cœur et routeurs",
        "indispensable": True,
        "regle": "Deux, puis un de plus par tranche de 40 baies",
        "unite": "châssis",
        "prix_unitaire": 60000,
        "carbone_kg": 3500,
        "duree_vie": 10,
        "pourquoi": "L'agrégation et la sortie : sans elle, les baies ne "
                    "communiquent ni entre elles ni avec l'extérieur.",
        "achat_durable": "Modularité : un châssis dont on change les cartes "
                         "vit deux fois plus longtemps qu'un équipement "
                         "monolithique.",
    },
    {
        "cle": "pdu",
        "nom": "Bandeaux de prises intelligents (PDU)",
        "indispensable": True,
        "regle": "Deux par baie — voies A et B",
        "unite": "PDU",
        "prix_unitaire": 1400,
        "carbone_kg": 120,
        "duree_vie": 12,
        "pourquoi": "La double alimentation par baie est la condition de la "
                    "maintenance sans coupure. Les PDU mesurés fournissent en "
                    "outre la donnée de consommation par baie — sans quoi le "
                    "PUE partiel reste une estimation.",
        "achat_durable": "Choisir des PDU MESURÉS : ils conditionnent le "
                         "pilotage énergétique, donc l'ISO 50001 — et un "
                         "équipement qu'on ne mesure pas ne s'optimise pas.",
    },
    {
        "cle": "cablage",
        "nom": "Câblage cuivre et fibre, chemins de câbles",
        "indispensable": True,
        "regle": "Forfait par baie, cuivre et optique confondus",
        "unite": "baie câblée",
        "prix_unitaire": 2600,
        "carbone_kg": 180,
        "duree_vie": 15,
        "pourquoi": "Le poste qu'on découvre tard : reprendre un câblage en "
                    "salle occupée coûte plusieurs fois son prix initial.",
        "achat_durable": "Surdimensionner la fibre au premier passage : c'est "
                         "le seul poste où l'anticipation évite une "
                         "intervention entière quelques années plus tard.",
    },
    {
        "cle": "dcim",
        "nom": "Supervision d'infrastructure (DCIM) et métrologie IT",
        "indispensable": False,
        "regle": "Forfait par tranche de 50 baies",
        "unite": "lot",
        "prix_unitaire": 45000,
        "carbone_kg": 400,
        "duree_vie": 8,
        "pourquoi": "Non indispensable au démarrage — mais sans lui, aucune "
                    "des grandeurs de pilotage (PUE partiel, taux "
                    "d'occupation, dérive thermique) ne se constate.",
        "achat_durable": "C'est l'outil qui rend l'allongement de durée de "
                         "vie DÉFENDABLE : sans mesure, prolonger se décide "
                         "à l'aveugle.",
    },
    {
        "cle": "kvm",
        "nom": "Consoles, KVM sur IP et accès hors bande",
        "indispensable": False,
        "regle": "Un par tranche de 20 baies",
        "unite": "ensemble",
        "prix_unitaire": 5500,
        "carbone_kg": 220,
        "duree_vie": 10,
        "pourquoi": "Évite un déplacement sur site à chaque intervention de "
                    "bas niveau. Le calcul se fait sur le coût des "
                    "déplacements évités, pas sur le confort.",
        "achat_durable": "Poste à longue durée de vie, peu sensible à "
                         "l'obsolescence : à conserver lors des "
                         "renouvellements de serveurs.",
    },
]

_CLES = [p["cle"] for p in POSTES]

# Répartition de la puissance informatique entre calcul et stockage. Le reste
# (réseau, divers) est porté par les postes dédiés.
PART_CALCUL = 0.80
PART_STOCKAGE = 0.15
# Puissance unitaire moyenne, en kW. Elle dépend de la densité retenue : un
# serveur de salle IA n'est pas un serveur de salle classique.
PUISSANCE_SERVEUR = {"classique": 0.5, "dense": 0.8, "ia_air": 6.0,
                     "ia_liquide": 10.0}
PUISSANCE_STOCKAGE_CHASSIS = 3.0

PRIX_SOURCE = ("Ordres de grandeur de marché européen, hors remise "
               "constructeur et hors options. À REMPLACER par les devis dès "
               "la consultation : l'écart entre un prix catalogue et un prix "
               "négocié atteint couramment 40 % sur le calcul.")
CARBONE_SOURCE = ("Empreintes produit (PCF) publiées par les constructeurs et "
                  "base ouverte Boavizta, complétées par les ordres de "
                  "grandeur sectoriels du moteur. Scope 3 du GHG Protocol, "
                  "catégories 1 (biens et services achetés) et 2 (biens "
                  "d'équipement).")


# Repli quand le moteur local ne publie pas de facteur par serveur — c'est le
# cas de Sentinel, dont l'empreinte est exprimée par MWh informatique et non
# par machine. Ce n'est pas une seconde table : c'est UNE valeur, nommée comme
# repli, et la provenance effective est servie avec le résultat.
SERVEUR_REPLI_KG = 1200.0
SERVEUR_REPLI_ANS = 5.0
SERVEUR_REPLI_SOURCE = ("Ordre de grandeur d'un serveur biprocesseur de volume "
                        "(fabrication et transport), d'après les empreintes "
                        "produit constructeurs et la base ouverte Boavizta. "
                        "Repli utilisé faute de facteur publié par le moteur "
                        "local — à remplacer par le PCF du matériel retenu.")


def _facteur_serveur():
    """Le carbone et la durée de vie d'un serveur, et D'OÙ ils viennent.

    Lus au moteur local quand il les publie — c'est alors la même grandeur
    que celle de l'étude d'empreinte, et les deux ne peuvent pas diverger.
    """
    if _D is not None:
        s = getattr(_D, "INCORPORE", {}).get("serveur_kgCO2e") or {}
        if s.get("valeur"):
            return (float(s["valeur"]), float(s.get("duree_vie_ans") or 5),
                    "moteur %s (carbone incorporé de l'étude d'empreinte)"
                    % _MOTEUR)
    return SERVEUR_REPLI_KG, SERVEUR_REPLI_ANS, SERVEUR_REPLI_SOURCE


def nomenclature(puissance_it_kw, densite=None, duree_vie_serveur=None):
    """Les équipements, dimensionnés — quantités, prix, carbone de fabrication.

    `duree_vie_serveur` : la durée de vie RETENUE pour le calcul. Elle change
    l'empreinte annualisée, jamais les quantités : prolonger n'achète pas
    moins de serveurs le premier jour, cela en achète moins ENSUITE.
    """
    try:
        p_it = float(puissance_it_kw or 0)
    except (TypeError, ValueError):
        p_it = 0.0
    if p_it <= 0:
        return {"ok": False,
                "motif": "La puissance informatique installée est nécessaire : "
                         "toutes les quantités en dépendent."}
    d = str(densite or DENSITE_DEFAUT)
    if d not in DENSITES:
        return {"ok": False,
                "motif": "Densité inconnue : %s. Connues : %s"
                         % (d, ", ".join(sorted(DENSITES)))}

    kw_baie = DENSITES[d]["kw_baie"]
    n_baies = max(1, int(round(p_it / kw_baie + 0.4999)))
    p_serveur = PUISSANCE_SERVEUR.get(d, 0.8)
    n_serveurs = max(1, int(round(p_it * PART_CALCUL / p_serveur)))
    n_stockage = max(1, int(round(p_it * PART_STOCKAGE / PUISSANCE_STOCKAGE_CHASSIS)))
    c_serveur, dv_serveur_ref, src_serveur = _facteur_serveur()
    dv_serveur = float(duree_vie_serveur or dv_serveur_ref)

    quantites = {
        "baies": n_baies,
        "serveurs": n_serveurs,
        "stockage": n_stockage,
        "reseau_tor": n_baies * 2,
        "reseau_coeur": 2 + max(0, (n_baies - 1) // 40),
        "pdu": n_baies * 2,
        "cablage": n_baies,
        "dcim": max(1, int(round(n_baies / 50.0 + 0.4999))),
        "kvm": max(1, int(round(n_baies / 20.0 + 0.4999))),
    }

    lignes, total_eur, total_kg, total_kg_an = [], 0.0, 0.0, 0.0
    for poste in POSTES:
        q = quantites.get(poste["cle"], 0)
        c_u = poste["carbone_kg"]
        dv = poste["duree_vie"]
        if poste["cle"] == "serveurs":
            c_u, dv = c_serveur, dv_serveur
        eur = q * poste["prix_unitaire"]
        kg = q * (c_u or 0)
        kg_an = kg / dv if dv else 0.0
        total_eur += eur
        total_kg += kg
        total_kg_an += kg_an
        lignes.append({
            "cle": poste["cle"], "nom": poste["nom"],
            "indispensable": poste["indispensable"], "regle": poste["regle"],
            "unite": poste["unite"], "quantite": q,
            "prix_unitaire": poste["prix_unitaire"],
            "prix_total_eur": round(eur),
            "carbone_unitaire_kg": c_u, "duree_vie_ans": dv,
            "carbone_total_kg": round(kg),
            "carbone_annualise_kg": round(kg_an, 1),
            "pourquoi": poste["pourquoi"],
            "achat_durable": poste["achat_durable"],
        })

    indisp = sum(l["prix_total_eur"] for l in lignes if l["indispensable"])
    return {
        "ok": True, "puissance_it_kw": p_it,
        "densite": d, "densite_nom": DENSITES[d]["nom"],
        "densite_note": DENSITES[d]["note"], "kw_par_baie": kw_baie,
        "baies": n_baies,
        "lignes": lignes,
        "total_eur": round(total_eur),
        "total_indispensable_eur": round(indisp),
        "total_utile_eur": round(total_eur - indisp),
        "eur_par_kw_it": round(total_eur / p_it),
        "carbone_total_t": round(total_kg / 1000.0, 1),
        "carbone_annualise_t": round(total_kg_an / 1000.0, 1),
        "incertitude_prix_pct": INCERTITUDE_PRIX * 100,
        "incertitude_carbone_pct": INCERTITUDE_CARBONE * 100,
        "prix_source": PRIX_SOURCE,
        "carbone_source": CARBONE_SOURCE,
        "serveur_source": src_serveur,
        "moteur_lu": _MOTEUR,
        "duree_vie_serveur_ans": dv_serveur,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  2. LA PART DANS L'INVESTISSEMENT — deux chiffres, deux périmètres
# ═══════════════════════════════════════════════════════════════════════════

# Le constat qui commande tout ce chapitre : les quatorze lots de l'enveloppe
# travaux ne contiennent AUCUN équipement informatique. Le lot « Aménagement
# des salles informatiques » couvre les planchers techniques, les chemins de
# câbles, le confinement et la distribution terminale — pas les serveurs, pas
# les baies actives, pas le réseau. L'informatique est un budget séparé, et
# ce qui change d'un périmètre à l'autre, ce n'est pas son appartenance aux
# lots : c'est QUI le porte.
LOTS_SANS_IT = ("Les lots de l'enveloppe travaux ne contiennent aucun "
                "équipement informatique : le lot d'aménagement des salles "
                "couvre les planchers, chemins de câbles, confinement et "
                "distribution terminale — pas les serveurs, pas le réseau. "
                "La part de l'informatique DANS l'enveloppe travaux est donc "
                "nulle dans tous les périmètres, et c'est exact. La question "
                "utile n'est pas celle-là : c'est sa part dans "
                "l'investissement total, et qui le finance.")

PERIMETRES = {
    "colocation": {
        "nom": "Colocation — l'exploitant loue de la puissance et des mètres carrés",
        "meme_maitre_ouvrage": False,
        "avec_travaux": True,
        "porteur_it": "le client hébergé",
        "dit": "Les équipements informatiques appartiennent au CLIENT : ils "
               "ne sont ni dans l'enveloppe travaux de l'exploitant, ni dans "
               "son bilan carbone. Ils existent pourtant, et leur carbone est "
               "le plus lourd des trois postes — il figure au scope 3 du "
               "client. Si aucun des deux ne le porte, il disparaît des deux "
               "bilans, ce qui est exactement le trou que la CSRD cherche à "
               "fermer.",
    },
    "propre": {
        "nom": "Centre propre — entreprise, hyperscale, souverain",
        "meme_maitre_ouvrage": True,
        "avec_travaux": True,
        "porteur_it": "le maître d'ouvrage, comme les travaux",
        "dit": "Bâtiment et informatique sont portés par la même entité : "
               "l'investissement total additionne les deux, et l'IT en "
               "représente couramment la moitié. Le raisonner sur la seule "
               "enveloppe travaux sous-estime le projet d'autant — et fait "
               "arbitrer des économies de génie civil pendant que le poste "
               "le plus lourd passe sans discussion.",
    },
    "heberge": {
        "nom": "Hébergement dans un centre tiers — l'IT sans le bâtiment",
        "meme_maitre_ouvrage": False,
        "avec_travaux": False,
        "porteur_it": "vous, et vous seul",
        "dit": "Aucune enveloppe travaux de votre côté : l'investissement se "
               "réduit aux équipements, et le carbone du bâtiment est porté "
               "par l'hébergeur. À demander dans le contrat, sinon il "
               "manquera au bilan sans que personne s'en aperçoive.",
    },
}


def part_investissement(nomen, enveloppe_travaux_eur=None, perimetre="propre"):
    """La place de l'informatique dans l'investissement — selon le périmètre.

    Trois chiffres, et un seul est une « part de budget » :

    - part_lots_pct  : toujours 0. Les lots travaux ne portent pas d'IT.
    - part_total_pct : la part de l'investissement TOTAL — calculée seulement
                       quand le même maître d'ouvrage porte les deux. Ailleurs,
                       additionner reviendrait à mélanger deux bilans.
    - rapport_it_travaux : un RAPPORT (l'IT pèse tant de fois les travaux),
                       lisible même quand les deux budgets sont portés par des
                       acteurs différents — à condition de le nommer rapport
                       et non pourcentage d'un budget.
    """
    if not nomen or not nomen.get("ok"):
        return {"ok": False, "motif": "Nomenclature indisponible."}
    cle = str(perimetre or "propre")
    per = PERIMETRES.get(cle)
    if per is None:
        return {"ok": False,
                "motif": ("Périmètre « %s » inconnu. Périmètres traités : %s."
                          % (cle, ", ".join(sorted(PERIMETRES))))}
    it = float(nomen["total_eur"])
    try:
        env = float(enveloppe_travaux_eur or 0)
    except (TypeError, ValueError):
        env = 0.0

    base = {"ok": True, "perimetre": cle, "perimetre_nom": per["nom"],
            "porteur_it": per["porteur_it"], "it_eur": round(it),
            "part_lots_pct": 0.0, "lots_dit": LOTS_SANS_IT,
            "dit": per["dit"]}

    # Hébergement : il n'y a pas d'enveloppe travaux de ce côté. En accepter
    # une et l'additionner fabriquerait un investissement qui n'existe pas.
    if not per["avec_travaux"]:
        base.update({"enveloppe_travaux_eur": None, "rapport_it_travaux": None,
                     "total_projet_eur": round(it), "part_total_pct": 100.0,
                     "lecture": ("Investissement %s M€, entièrement "
                                 "informatique : dans ce périmètre il n'y a "
                                 "pas d'enveloppe travaux de votre côté. Si "
                                 "un montant de travaux vous est présenté, il "
                                 "est celui de l'hébergeur — il ne s'ajoute "
                                 "pas au vôtre." % _fr(it / 1e6, 2))})
        return base

    if env <= 0:
        base.update({"enveloppe_travaux_eur": None, "rapport_it_travaux": None,
                     "total_projet_eur": None, "part_total_pct": None,
                     "lecture": ("Enveloppe travaux non renseignée : la part "
                                 "de l'informatique dans l'investissement "
                                 "total ne peut pas être calculée. Lancez "
                                 "l'étude d'enveloppe — dans Sentinel — et "
                                 "reportez son montant ici.")})
        return base

    rapport = it / env
    lecture = ("Informatique %s M€ face à une enveloppe travaux de %s M€ : "
               "l'informatique pèse %s fois les travaux."
               % (_fr(it / 1e6, 2), _fr(env / 1e6, 2), _fr(rapport, 2)))

    if per["meme_maitre_ouvrage"]:
        total = env + it
        part_totale = it / total * 100.0
        lecture += (" Le même maître d'ouvrage porte les deux : "
                    "l'investissement total est de %s M€, dont %s %% "
                    "d'informatique." % (_fr(total / 1e6, 2),
                                         _fr(part_totale, 1)))
        if part_totale > 45:
            lecture += (" Au-delà de 45 %, c'est le poste à arbitrer en "
                        "premier : une économie de 5 % sur l'informatique "
                        "pèse plus qu'une économie de 5 % sur le génie "
                        "civil, qui porte sur une base plus petite.")
        base.update({"enveloppe_travaux_eur": round(env),
                     "rapport_it_travaux": round(rapport, 2),
                     "total_projet_eur": round(total),
                     "part_total_pct": round(part_totale, 1),
                     "lecture": lecture})
        return base

    lecture += (" Les deux budgets sont portés par des acteurs différents : "
                "aucun pourcentage d'un investissement total n'est calculé "
                "ici, car les additionner mélangerait deux bilans. Le "
                "rapport, lui, se lit — et il dit lequel des deux commande.")
    base.update({"enveloppe_travaux_eur": round(env),
                 "rapport_it_travaux": round(rapport, 2),
                 "total_projet_eur": None, "part_total_pct": None,
                 "lecture": lecture})
    return base


# ═══════════════════════════════════════════════════════════════════════════
#  3. PROLONGER LA DURÉE DE VIE — le gain, et son point de bascule
#
#  Le message est juste : allonger la durée de vie allège le bilan carbone et
#  évite la fabrication d'actifs neufs. Mais il a une limite qu'une plaquette
#  ne dit jamais — un matériel ancien consomme plus à service rendu égal, et
#  cette surconsommation finit par manger le gain. Le point de bascule dépend
#  de l'intensité carbone du réseau : sur un mix décarboné, prolonger reste
#  payant très longtemps ; sur un mix charbon, beaucoup moins.
# ═══════════════════════════════════════════════════════════════════════════

# Perte d'efficacité annuelle d'un serveur face à la génération courante :
# à service rendu égal, un matériel de N ans consomme davantage que le
# matériel neuf du moment. L'ordre de grandeur retenu est PRUDENT — les sauts
# de génération observés sur les processeurs de serveur valent couramment
# davantage. Un chiffre prudent ici joue en faveur de l'allongement : le
# module ne force donc pas la conclusion qu'il annonce.
DERIVE_EFFICACITE_AN = 0.06
DERIVE_SOURCE = ("Ordre de grandeur de la perte d'efficacité énergétique "
                 "annuelle d'un serveur face à la génération courante, à "
                 "service rendu égal. Prudent et à confronter aux mesures du "
                 "parc : le rythme réel dépend de la charge, de la "
                 "virtualisation et du cycle des processeurs. Un BE qui "
                 "dispose de sa propre mesure doit la substituer — c'est le "
                 "paramètre qui commande le résultat.")

# Les deux politiques comparées ne sont pas « parc vieux » contre « parc
# neuf » : ce sont deux CYCLES de renouvellement en régime établi. Sur un
# cycle de longueur L, l'âge moyen du parc vaut L/2 ; allonger de B à C
# années fait donc vieillir le parc de (C−B)/2 en moyenne, pas de (C−B).
# C'est cet écart-là, et lui seul, qui se paie en consommation.
MODELE_PROLONGATION = (
    "Deux cycles de renouvellement en régime établi sont comparés, pas un "
    "parc ancien contre un parc neuf. Sur un cycle de L années, l'âge moyen "
    "du parc vaut L/2 : passer de B à C années vieillit le parc de (C−B)/2 "
    "en moyenne. Gain annuel = carbone de fabrication × (1/B − 1/C). Coût "
    "annuel = intensité × PUE × puissance informatique × heures × dérive × "
    "(C−B)/2. Les deux termes sont des grandeurs ANNUELLES : c'est ce qui "
    "les rend comparables.")


def prolongation(puissance_it_kw, duree_base=None, duree_cible=None,
                 pays="FR", intensite_g=None, densite=None, heures_an=8760,
                 pue=1.0, derive_an=None):
    """Ce que gagne — et ce que coûte — l'allongement de la durée de vie.

    Le gain : le carbone de fabrication s'amortit sur plus d'années. Le
    coût : à service rendu égal, un parc dont l'âge moyen augmente consomme
    davantage, et cette consommation a un carbone. Le module rend le bilan
    net ANNUEL, l'intensité carbone de bascule, et la durée maximale au-delà
    de laquelle l'allongement cesse de payer sur ce réseau.

    L'intensité de bascule ne dépend pas de la taille du centre : la
    puissance informatique se simplifie entre le gain et le coût. Deux
    projets de 500 kW et de 5 MW trouvent le même seuil — c'est une propriété
    du calcul, et elle se vérifie.
    """
    n_base = nomenclature(puissance_it_kw, densite)
    if not n_base.get("ok"):
        return {"ok": False, "motif": n_base.get("motif")}
    c_serveur, dv_ref, _ = _facteur_serveur()
    d0 = float(duree_base or dv_ref)
    d1 = float(duree_cible or (d0 + 2))
    if d0 <= 0:
        return {"ok": False, "motif": "La durée actuelle doit être positive."}
    if d1 <= d0:
        return {"ok": False,
                "motif": "La durée cible doit dépasser la durée actuelle : "
                         "ce calcul mesure un ALLONGEMENT."}
    if d1 > 15:
        return {"ok": False,
                "motif": "Au-delà de quinze ans, le calcul sort de son "
                         "domaine : support constructeur, sécurité et pièces "
                         "détachées deviennent les facteurs limitants, et ils "
                         "ne se chiffrent pas ici."}
    try:
        pue_v = float(pue or 1.0)
    except (TypeError, ValueError):
        pue_v = 1.0
    if pue_v < 1.0:
        return {"ok": False,
                "motif": "Un PUE inférieur à 1 est physiquement impossible : "
                         "le site ne peut pas consommer moins que ses "
                         "équipements informatiques."}
    derive = float(derive_an if derive_an is not None else DERIVE_EFFICACITE_AN)
    if derive < 0:
        return {"ok": False,
                "motif": "Une dérive d'efficacité négative signifierait qu'un "
                         "matériel s'améliore en vieillissant."}

    # L'intensité carbone : celle du moteur pour le pays, ou celle fournie.
    inten = intensite_g
    if inten is None:
        inten = _intensite_pays(pays)
    if inten is None:
        return {"ok": False,
                "motif": ("Intensité carbone inconnue pour « %s ». Le résultat "
                          "dépend entièrement de ce chiffre : le module ne le "
                          "suppose pas." % str(pays or "FR").upper())}
    inten = float(inten)

    serveurs = [l for l in n_base["lignes"] if l["cle"] == "serveurs"][0]
    kg_fab = float(serveurs["carbone_total_kg"])
    p_it = float(puissance_it_kw)

    # ── Le gain : le même carbone de fabrication réparti sur plus d'années.
    gain_fab_an = kg_fab * (1.0 / d0 - 1.0 / d1)

    # ── Le coût : le vieillissement MOYEN du parc, (C−B)/2, et non (C−B).
    vieillissement_moyen = (d1 - d0) / 2.0
    kwh_sup_an = p_it * heures_an * derive * vieillissement_moyen * pue_v
    cout_expl_an = kwh_sup_an * inten / 1000.0          # g → kg

    net_an = gain_fab_an - cout_expl_an

    # ── L'intensité de bascule : le mix au-delà duquel allonger ne paie plus.
    inten_bascule = (gain_fab_an / kwh_sup_an * 1000.0) if kwh_sup_an > 0 else None

    # ── La durée maximale payante sur CE réseau. Le net s'annule pour
    #    C* = 2 × F / (B × I × P × h × d × PUE) — résolution exacte, pas un
    #    balayage : le lecteur peut la refaire.
    denom = d0 * inten / 1000.0 * p_it * heures_an * derive * pue_v
    duree_max = (2.0 * kg_fab / denom) if denom > 0 else None

    if net_an >= 0:
        verdict = "favorable"
        lecture = ("Allonger de %s à %s ans est FAVORABLE sur ce mix "
                   "électrique (%s g/kWh) : %s tCO2e évitées par an. Le "
                   "carbone de fabrication économisé (%s t/an) dépasse la "
                   "surconsommation du parc vieillissant (%s t/an)."
                   % (_fr(d0), _fr(d1), _fr(inten), _fr(net_an / 1000.0, 1),
                      _fr(gain_fab_an / 1000.0, 1),
                      _fr(cout_expl_an / 1000.0, 1)))
    else:
        verdict = "defavorable"
        lecture = ("Allonger de %s à %s ans est DÉFAVORABLE sur ce mix "
                   "électrique (%s g/kWh) : %s tCO2e de PLUS par an. La "
                   "surconsommation du parc vieillissant (%s t/an) dépasse le "
                   "carbone de fabrication économisé (%s t/an). Sur un réseau "
                   "carboné, le levier n'est pas d'étirer le matériel : c'est "
                   "de décarboner l'alimentation."
                   % (_fr(d0), _fr(d1), _fr(inten), _fr(-net_an / 1000.0, 1),
                      _fr(cout_expl_an / 1000.0, 1),
                      _fr(gain_fab_an / 1000.0, 1)))
    if inten_bascule is not None:
        lecture += (" Bascule à %s g/kWh : en dessous, allonger paie ; "
                    "au-dessus, non." % _fr(inten_bascule, 0))
    if duree_max is not None:
        if duree_max <= d0:
            lecture += (" Sur ce réseau, AUCUN allongement au-delà de %s ans "
                        "ne se justifie par le carbone."
                        % _fr(d0))
        elif duree_max >= 15:
            lecture += (" Sur ce réseau, l'allongement reste payant au-delà de "
                        "quinze ans — c'est alors le support constructeur et "
                        "la sécurité qui fixent la limite, pas le carbone.")
        else:
            lecture += (" Durée maximale payante sur ce réseau : %s ans."
                        % _fr(duree_max, 1))

    return {
        "ok": True, "duree_base": d0, "duree_cible": d1,
        "pays": str(pays or "FR").upper(), "intensite_g": inten,
        "pue": pue_v, "derive_an": derive,
        "carbone_fabrication_kg": round(kg_fab),
        "vieillissement_moyen_ans": round(vieillissement_moyen, 2),
        "gain_fabrication_kg_an": round(gain_fab_an),
        "cout_exploitation_kg_an": round(cout_expl_an),
        "kwh_supplementaires_an": round(kwh_sup_an),
        "net_kg_an": round(net_an), "net_t_an": round(net_an / 1000.0, 2),
        "intensite_bascule_g": (round(inten_bascule, 1)
                                if inten_bascule is not None else None),
        "duree_max_payante_ans": (round(duree_max, 1)
                                  if duree_max is not None else None),
        "verdict": verdict, "lecture": lecture,
        "modele": MODELE_PROLONGATION,
        "derive_source": DERIVE_SOURCE,
        "formules": [
            "Gain (kgCO2e/an) = Carbone de fabrication × (1/durée actuelle − 1/durée cible)",
            "Vieillissement moyen (ans) = (durée cible − durée actuelle) / 2",
            "Coût (kgCO2e/an) = Puissance IT × heures × dérive × vieillissement moyen × PUE × intensité / 1000",
            "Intensité de bascule (g/kWh) = Gain / kWh supplémentaires × 1000",
            "Durée maximale payante (ans) = 2 × Carbone de fabrication / (durée actuelle × intensité/1000 × Puissance IT × heures × dérive × PUE)",
        ],
        "reserve": "Ce bilan ne porte QUE sur le carbone, et à service rendu "
                   "constant. Il ne dit rien d'un parc remplacé parce que la "
                   "capacité manque. La décision d'allonger engage aussi le "
                   "support constructeur, les pièces détachées, la surface "
                   "d'attaque de sécurité d'un matériel qui ne reçoit plus de "
                   "correctifs, et la performance rendue aux applications. Un "
                   "gain carbone ne justifie pas de garder un serveur qui ne "
                   "se met plus à jour.",
    }


# ═══════════════════════════════════════════════════════════════════════════
#  4. LE SCOPE 3 — ce que ces équipements pèsent au GHG Protocol
# ═══════════════════════════════════════════════════════════════════════════

SCOPE3_CATEGORIES = {
    "1": {"nom": "Biens et services achetés",
          "porte": "Le carbone de fabrication des équipements consommables et "
                   "des prestations — câblage, petit matériel, services."},
    "2": {"nom": "Biens d'équipement",
          "porte": "Le carbone de fabrication des immobilisations : serveurs, "
                   "stockage, commutateurs, baies. C'est la catégorie "
                   "dominante d'un centre de données, et celle que ce module "
                   "chiffre."},
    "11": {"nom": "Utilisation des produits vendus",
           "porte": "Pour un exploitant de colocation : la consommation des "
                    "équipements de ses clients. Souvent oubliée, et "
                    "structurante quand le parc hébergé est grand."},
}


def bilan_scope3(nomen, prolong=None):
    """Ce que la nomenclature pèse au scope 3, et ce qu'elle NE couvre pas.

    Un bilan qui ne dit pas ses trous se lit comme un bilan complet — c'est
    la faute la plus fréquente des déclarations volontaires.
    """
    if not nomen or not nomen.get("ok"):
        return {"ok": False, "motif": "Nomenclature indisponible."}
    cat2 = sum(l["carbone_total_kg"] for l in nomen["lignes"]
               if l["cle"] != "cablage")
    cat1 = sum(l["carbone_total_kg"] for l in nomen["lignes"]
               if l["cle"] == "cablage")

    # L'allongement de la durée de vie ne change pas le carbone TOTAL de
    # fabrication : il change sa répartition annuelle, et c'est l'annualisé
    # qui se déclare chaque année. Le chapitre précédent est donc branché
    # ici, pas seulement voisin.
    effet = None
    if prolong and prolong.get("ok"):
        gain = float(prolong.get("gain_fabrication_kg_an") or 0.0)
        net = float(prolong.get("net_kg_an") or 0.0)
        base_an = float(nomen["carbone_annualise_t"]) * 1000.0
        effet = {
            "duree_base": prolong.get("duree_base"),
            "duree_cible": prolong.get("duree_cible"),
            "annualise_apres_t": round(max(0.0, base_an - gain) / 1000.0, 1),
            "verdict": prolong.get("verdict"),
            "dit": ("L'allongement de %s à %s ans ne change pas le carbone "
                    "total de fabrication : il l'étale. La catégorie 2 "
                    "annualisée passe de %s à %s tCO2e/an. Mais le bilan "
                    "complet doit retrancher la surconsommation du parc "
                    "vieillissant, comptée au scope 2 : net %s tCO2e/an."
                    % (_fr(prolong.get("duree_base")),
                       _fr(prolong.get("duree_cible")),
                       _fr(base_an / 1000.0, 1),
                       _fr(max(0.0, base_an - gain) / 1000.0, 1),
                       _fr(net / 1000.0, 1))),
            "avertissement": ("Le gain d'annualisation se lit au scope 3 et "
                              "la surconsommation au scope 2 : ne présenter "
                              "que le premier montre une amélioration là où "
                              "le bilan complet peut se dégrader."),
        }

    return {
        "ok": True,
        "categorie_2_t": round(cat2 / 1000.0, 1),
        "categorie_1_t": round(cat1 / 1000.0, 1),
        "total_t": round((cat1 + cat2) / 1000.0, 1),
        "annualise_t": nomen["carbone_annualise_t"],
        "effet_prolongation": effet,
        "categories": SCOPE3_CATEGORIES,
        "incertitude_pct": INCERTITUDE_CARBONE * 100,
        "source": CARBONE_SOURCE,
        "complement": "Ce chiffre COMPLÈTE les scopes 1 et 2 de l'étude "
                      "d'empreinte — combustion des groupes de secours et "
                      "fluides frigorigènes pour le scope 1, électricité "
                      "achetée pour le scope 2. Les trois ensemble font le "
                      "bilan ; l'un des trois seul se présente rarement de "
                      "bonne foi.",
        "non_couvert": [
            "le transport amont des équipements (catégorie 4) — dépend des "
            "sites de fabrication, à demander aux constructeurs",
            "la fin de vie et le traitement des déchets d'équipements "
            "(catégorie 12), à instruire avec l'éco-organisme",
            "les déplacements des équipes d'exploitation et de maintenance "
            "(catégories 6 et 7)",
            "pour un exploitant de colocation : la consommation des "
            "équipements de ses clients (catégorie 11), souvent le poste "
            "le plus lourd de son bilan",
        ],
    }


def _verifier():
    f = []
    if len(set(_CLES)) != len(_CLES):
        f.append("clés de postes en double")
    for p in POSTES:
        for champ in ("regle", "pourquoi", "achat_durable"):
            if not str(p.get(champ, "")).strip():
                f.append("poste incomplet : %s.%s" % (p["cle"], champ))
        if p["cle"] != "serveurs" and not p.get("carbone_kg"):
            f.append("poste sans carbone : " + p["cle"])
    if not any(p["indispensable"] for p in POSTES):
        f.append("aucun poste indispensable : la distinction perdrait son sens")
    for d in DENSITES:
        if d not in PUISSANCE_SERVEUR:
            f.append("densité sans puissance serveur : " + d)
    if abs(PART_CALCUL + PART_STOCKAGE - 0.95) > 0.11:
        f.append("répartition calcul/stockage invraisemblable")

    # Les baies posées doivent pouvoir accueillir la puissance demandée.
    n = nomenclature(1000.0)
    if n.get("ok"):
        if n["baies"] * n["kw_par_baie"] < 1000.0:
            f.append("baies insuffisantes pour la puissance demandée")
    else:
        f.append("nomenclature de référence en échec : " + str(n.get("motif")))

    # L'intensité de bascule ne doit pas dépendre de la taille du centre :
    # la puissance informatique se simplifie entre le gain et le coût. Si
    # cette propriété tombe, une formule a été modifiée de travers.
    a = prolongation(500.0, 5, 8, "FR")
    b = prolongation(5000.0, 5, 8, "FR")
    if not (a.get("ok") and b.get("ok")):
        f.append("prolongation de référence en échec")
    elif abs(a["intensite_bascule_g"] - b["intensite_bascule_g"]) > 0.05:
        f.append("l'intensité de bascule dépend de la taille du centre : "
                 "%s contre %s" % (a["intensite_bascule_g"],
                                   b["intensite_bascule_g"]))
    return f


_f = _verifier()
if _f:
    raise AssertionError("equipements_it incohérent : " + " ; ".join(_f))
del _f


def referentiel():
    return {"version": VERSION, "postes": POSTES, "densites": DENSITES,
            "densite_defaut": DENSITE_DEFAUT, "perimetres": PERIMETRES,
            "scope3": SCOPE3_CATEGORIES,
            "part_calcul": PART_CALCUL, "part_stockage": PART_STOCKAGE,
            "derive_efficacite_an": DERIVE_EFFICACITE_AN,
            "derive_source": DERIVE_SOURCE,
            "prix_source": PRIX_SOURCE, "carbone_source": CARBONE_SOURCE,
            "serveur_source": _facteur_serveur()[2],
            "moteur_lu": _MOTEUR, "pays_connus": pays_connus(),
            "incertitude_prix_pct": INCERTITUDE_PRIX * 100,
            "incertitude_carbone_pct": INCERTITUDE_CARBONE * 100}


def sante():
    return {"module": "equipements_it", "version": VERSION,
            "postes": len(POSTES),
            "indispensables": sum(1 for p in POSTES if p["indispensable"]),
            "densites": len(DENSITES), "perimetres": len(PERIMETRES),
            "moteur_lie": _D is not None, "problemes": _verifier()}
