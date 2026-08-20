# -*- coding: utf-8 -*-
"""ÉCONOMISTE DE LA CONSTRUCTION — chiffrer une opération de centre de données.

CE QUE CE MODULE FAIT, ET CE QU'IL REFUSE DE FAIRE

Il chiffre une opération à partir de QUANTITÉS et de PRIX UNITAIRES. Il ne
porte aucun ratio de coût, et c'est un choix, pas un manque.

POURQUOI AUCUN RATIO. La demande était de « s'appuyer sur des projets déjà
exécutés ». Le référentiel du cabinet a été recompté pour l'occasion :

    249 centres de données référencés
      0 publient leur capacité informatique
      2 publient un montant d'investissement
      0 publient les DEUX

Il n'existe donc, dans ce dépôt, aucune base d'opérations exécutées permettant
de calibrer un euro par kilowatt ou un euro par mètre carré. Un ratio affiché
ici serait une invention habillée en référentiel — et il serait crédible, ce
qui est pire. Le module prend donc les prix EN ENTRÉE : votre bordereau, vos
marchés notifiés, vos opérations livrées. Il fournit la structure qui les
reçoit, et il tient le compte de ce qui n'est pas encore chiffré.

CE QU'IL APPORTE À LA PLACE, ET QUI DÉCIDE VRAIMENT

  1. CINQ NATURES D'OPÉRATION, et ce qui change entre elles. Un neuf, une
     extension, une réhabilitation de lots techniques, une reprise de chantier
     et un contrat de maintenance ne se chiffrent pas de la même façon — pas
     parce qu'on leur applique un coefficient, mais parce qu'ils n'ont pas les
     mêmes postes. C'est le cœur du module.

  2. LES POSTES PROPRES À L'EXISTANT, que le neuf ne connaît pas. Dépose,
     curage, évacuation, coupures programmées, coactivité, travaux en site
     occupé, horaires décalés, constat contradictoire, reprise de malfaçons.
     Ce sont eux qui font déraper une opération sur existant, et un chiffrage
     bâti sur un ratio de neuf ne les voit pas — il ne les sous-estime pas, il
     les IGNORE.

  3. UN ORDRE, LÀ OÙ ON ATTENDRAIT UN COEFFICIENT. Le module refuse d'écrire
     « une réhabilitation vaut 0,6 fois un neuf ». Il écrit en revanche que la
     provision pour aléas d'une opération sur existant ne peut pas être
     INFÉRIEURE à celle d'un neuf, parce que l'inconnu y est structurellement
     plus grand. Une relation d'ordre se défend ; un coefficient inventé, non.

  4. LE COMPTE DE CE QUI MANQUE. Toute ligne sans prix unitaire ressort
     `non_chiffree`, avec sa raison, et la part non chiffrée de l'opération est
     publiée. Au-delà d'un certain point, un total cesse d'être une estimation
     pour devenir l'addition de ce qu'on savait déjà.

CE QU'IL NE FAIT PAS

Il ne dimensionne rien, ne vérifie aucune quantité, et ne remplace ni un
métré, ni une consultation d'entreprises, ni l'avis d'un économiste. Il met en
ordre et il compte. Les quantités qu'on lui donne, il les croit.
"""

VERSION = "2026-08-a"

# ═══════════════════════════════════════════════════════════════════════════
#  1. LES QUANTITÉS — et où un client les trouve réellement
#
#     Une entrée qu'on ne sait pas où chercher est une entrée qui sera
#     inventée. Chacune porte donc sa source concrète.
# ═══════════════════════════════════════════════════════════════════════════

QUANTITES = {
    "puissance_it_kw": {
        "nom": "Puissance informatique", "unite": "kW",
        "ou": "Bilan de puissance du lot courants forts, ou somme des calibres "
              "des départs onduleurs. Jamais la puissance souscrite, qui "
              "comprend le refroidissement.",
    },
    "surface_salle_m2": {
        "nom": "Surface des salles informatiques", "unite": "m²",
        "ou": "Plans de niveau, surface utile intérieure des salles seules — "
              "hors locaux techniques, hors circulations.",
    },
    "surface_technique_m2": {
        "nom": "Surface des locaux techniques", "unite": "m²",
        "ou": "Plans de niveau : locaux onduleurs, TGBT, groupes froids, "
              "groupes électrogènes, locaux fluides.",
    },
    "surface_batiment_m2": {
        "nom": "Surface totale du bâtiment", "unite": "m²",
        "ou": "Surface de plancher du permis, ou surface hors œuvre du DOE "
              "pour un bâtiment existant.",
    },
    "nombre_baies": {
        "nom": "Nombre de baies", "unite": "baie",
        "ou": "Plan d'implantation des salles. À défaut, la puissance "
              "informatique divisée par la densité retenue.",
    },
    "surface_a_deposer_m2": {
        "nom": "Surface concernée par la dépose", "unite": "m²",
        "ou": "Relevé de l'existant. C'est la surface RÉELLEMENT touchée, pas "
              "celle du bâtiment.",
    },
    "montant_marche_repris_eur": {
        "nom": "Montant du marché repris", "unite": "€ HT",
        "ou": "Acte d'engagement du marché initial et derniers états "
              "d'acompte. Un chantier repris se chiffre sur ce qui RESTE.",
    },
    "duree_contrat_ans": {
        "nom": "Durée du contrat", "unite": "an",
        "ou": "Cahier des charges de maintenance.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  2. LES POSTES — ce qui se chiffre, et sur quelle quantité
#
#     Un poste ne s'invente pas une assiette : il déclare LA quantité qui le
#     porte. Deux postes qui prétendraient au même euro se verraient.
# ═══════════════════════════════════════════════════════════════════════════

POSTES = {
    # ── Ce qui existe dans presque toute opération ──────────────────────────
    "clos_couvert": {
        "nom": "Gros œuvre, clos et couvert", "assiette": "surface_batiment_m2",
        "famille": "batiment",
        "quoi": "Fondations, structure, façades, couverture, dallage.",
    },
    "amenagement_salle": {
        "nom": "Aménagement des salles informatiques", "assiette": "surface_salle_m2",
        "famille": "batiment",
        "quoi": "Plancher technique, cloisonnement coupe-feu, confinement, "
                "peintures, faux plafonds techniques.",
    },
    "poste_livraison": {
        "nom": "Raccordement et poste de livraison", "assiette": "puissance_it_kw",
        "famille": "technique",
        "quoi": "Poste HTA, transformateurs, cellules, liaison au réseau.",
    },
    "distribution_secours": {
        "nom": "Distribution électrique et secours", "assiette": "puissance_it_kw",
        "famille": "technique",
        "quoi": "TGBT, onduleurs, batteries, groupes électrogènes, cuves, "
                "distribution jusqu'aux baies.",
    },
    "froid": {
        "nom": "Production et distribution de froid", "assiette": "puissance_it_kw",
        "famille": "technique",
        "quoi": "Groupes froids, pompes, réseaux hydrauliques, terminaux, "
                "traitement d'air.",
    },
    "fluides": {
        "nom": "Eau, fluides et traitement", "assiette": "puissance_it_kw",
        "famille": "technique",
        "quoi": "Adduction, traitement d'eau, réseaux, rejets.",
    },
    "incendie": {
        "nom": "Sécurité incendie", "assiette": "surface_batiment_m2",
        "famille": "technique",
        "quoi": "Détection, désenfumage, extinction, compartimentage, SSI.",
    },
    "surete": {
        "nom": "Sûreté et contrôle d'accès", "assiette": "surface_batiment_m2",
        "famille": "technique",
        "quoi": "Contrôle d'accès, vidéoprotection, détection d'intrusion, "
                "clôtures.",
    },
    "gtb_dcim": {
        "nom": "GTB, GTC, DCIM et courants faibles", "assiette": "surface_batiment_m2",
        "famille": "technique",
        "quoi": "Supervision technique, comptage divisionnaire, câblage.",
    },
    "essais_mise_en_service": {
        "nom": "Essais et mise en service", "assiette": "puissance_it_kw",
        "famille": "technique",
        "quoi": "Essais individuels, essais de charge, mise en service, "
                "réception des installations.",
    },
    # ── LES POSTES DE L'EXISTANT, que le neuf ne connaît pas ────────────────
    "depose_curage": {
        "nom": "Dépose, curage et évacuation", "assiette": "surface_a_deposer_m2",
        "famille": "existant",
        "quoi": "Dépose des installations conservées ou non, curage, "
                "évacuation et traitement des déchets, tri.",
    },
    "mise_en_securite": {
        "nom": "Mise en sécurité et travaux préalables",
        "assiette": "surface_a_deposer_m2", "famille": "existant",
        "quoi": "Consignations, protections, cloisonnements provisoires, "
                "repérages avant travaux.",
    },
    "raccordement_existant": {
        "nom": "Raccordement sur installations existantes",
        "assiette": "puissance_it_kw", "famille": "existant",
        "quoi": "Piquages, reprises de réseaux, adaptation des tableaux et de "
                "la supervision existants, remise à niveau des interfaces.",
    },
    "site_occupe": {
        "nom": "Contraintes de site occupé", "assiette": "surface_a_deposer_m2",
        "famille": "existant",
        "quoi": "Phasage, coactivité, horaires décalés, coupures programmées, "
                "moyens provisoires pour maintenir l'exploitation.",
    },
    "constat_reprise": {
        "nom": "Constat, expertise et reprise de l'exécuté",
        "assiette": "montant_marche_repris_eur", "famille": "existant",
        "quoi": "Constat contradictoire, expertise de ce qui est réalisé, "
                "reprise des malfaçons, requalification des garanties.",
    },
    # ── L'EXPLOITATION ─────────────────────────────────────────────────────
    "maintenance_preventive": {
        "nom": "Maintenance préventive", "assiette": "puissance_it_kw",
        "famille": "exploitation",
        "quoi": "Visites périodiques, contrôles réglementaires, essais "
                "périodiques des groupes et des onduleurs.",
    },
    "gros_entretien": {
        "nom": "Gros entretien et renouvellement", "assiette": "puissance_it_kw",
        "famille": "exploitation",
        "quoi": "Remplacement des composants à durée de vie courte : "
                "batteries, filtres, compresseurs, vannes.",
    },
}

FAMILLES = {
    "batiment": "Bâtiment, clos-couvert et aménagements",
    "technique": "Lots techniques",
    "existant": "Sujétions propres à l'existant",
    "exploitation": "Exploitation et renouvellement",
}


# ═══════════════════════════════════════════════════════════════════════════
#  3. LES CINQ NATURES D'OPÉRATION
#
#     CE QUI CHANGE N'EST PAS UN COEFFICIENT, C'EST LA LISTE DES POSTES.
#     Un chiffrage de réhabilitation bâti sur un ratio de neuf ne sous-estime
#     pas les postes d'existant : il ne les porte pas du tout.
# ═══════════════════════════════════════════════════════════════════════════

OPERATIONS = {
    "neuf": {
        "nom": "Construction neuve",
        "objet": "Bâtiment et installations créés sur terrain nu ou après "
                 "démolition complète.",
        "postes": ["clos_couvert", "amenagement_salle", "poste_livraison",
                   "distribution_secours", "froid", "fluides", "incendie",
                   "surete", "gtb_dcim", "essais_mise_en_service"],
        "sans_objet": {
            "depose_curage": "il n'y a rien à déposer",
            "mise_en_securite": "aucune installation en service à protéger",
            "raccordement_existant": "aucun existant à raccorder",
            "site_occupe": "le site n'est pas exploité pendant les travaux",
            "constat_reprise": "aucun marché antérieur à reprendre",
            "maintenance_preventive": "relève de l'exploitation, pas de l'investissement",
            "gros_entretien": "relève de l'exploitation, pas de l'investissement",
        },
        "rang_alea": 1,
        "dit": "La seule nature où un ratio de filière garde un sens — et "
               "encore, à condition que le lot technique soit chiffré au "
               "kilowatt et non au mètre carré.",
    },
    "extension": {
        "nom": "Extension d'un site en exploitation",
        "objet": "Création de capacité nouvelle accolée ou raccordée à un site "
                 "qui continue de fonctionner.",
        "postes": ["clos_couvert", "amenagement_salle", "poste_livraison",
                   "distribution_secours", "froid", "fluides", "incendie",
                   "surete", "gtb_dcim", "essais_mise_en_service",
                   "raccordement_existant", "site_occupe"],
        "sans_objet": {
            "depose_curage": "l'extension crée, elle ne dépose pas — sauf "
                             "démolition partielle, à traiter alors en "
                             "réhabilitation",
            "mise_en_securite": "à requalifier si les travaux touchent des "
                                "locaux en service",
            "constat_reprise": "aucun marché antérieur à reprendre",
            "maintenance_preventive": "relève de l'exploitation",
            "gros_entretien": "relève de l'exploitation",
        },
        "rang_alea": 2,
        "dit": "LE PIÈGE DE L'EXTENSION : le neuf y est simple, c'est la "
               "COUTURE qui coûte. Raccorder sans couper, reprendre une GTB "
               "d'une génération antérieure, tenir les coupures dans des "
               "fenêtres d'exploitation — rien de cela n'apparaît dans un "
               "ratio au kilowatt.",
    },
    "rehabilitation_technique": {
        "nom": "Réhabilitation des lots techniques",
        "objet": "Bâtiment conservé, installations techniques déposées et "
                 "reconstruites — remise à niveau de capacité, de "
                 "disponibilité ou de performance.",
        "postes": ["amenagement_salle", "poste_livraison",
                   "distribution_secours", "froid", "fluides", "incendie",
                   "surete", "gtb_dcim", "essais_mise_en_service",
                   "depose_curage", "mise_en_securite",
                   "raccordement_existant", "site_occupe"],
        "sans_objet": {
            "clos_couvert": "le bâtiment est conservé — s'il ne l'est pas, "
                            "l'opération est une construction neuve après "
                            "démolition",
            "constat_reprise": "aucun marché antérieur à reprendre",
            "maintenance_preventive": "relève de l'exploitation",
            "gros_entretien": "relève de l'exploitation",
        },
        "rang_alea": 3,
        "dit": "LA NATURE LA PLUS EXPOSÉE À LA DÉCOUVERTE. Ce qu'on trouve en "
               "déposant n'est pas dans le DOE : réseaux non repérés, "
               "amiante, structures qui ne portent plus ce qu'on veut y "
               "mettre. La provision n'y est pas une prudence, c'est une "
               "ligne de chiffrage.",
    },
    "reprise_travaux": {
        "nom": "Reprise d'un chantier interrompu",
        "objet": "Achèvement d'une opération commencée par un tiers — "
                 "défaillance d'entreprise, résiliation, arrêt prolongé.",
        "postes": ["clos_couvert", "amenagement_salle", "poste_livraison",
                   "distribution_secours", "froid", "fluides", "incendie",
                   "surete", "gtb_dcim", "essais_mise_en_service",
                   "constat_reprise", "mise_en_securite", "site_occupe"],
        "sans_objet": {
            "depose_curage": "à requalifier : une reprise dépose parfois ce "
                             "qui a été mal exécuté",
            "raccordement_existant": "à requalifier selon l'avancement atteint",
            "maintenance_preventive": "relève de l'exploitation",
            "gros_entretien": "relève de l'exploitation",
        },
        "rang_alea": 4,
        "dit": "LA NATURE OÙ LE CHIFFRAGE EST LE PLUS FRAGILE, et il faut le "
               "dire au maître d'ouvrage avant de commencer. On chiffre ce "
               "qui RESTE, sur un existant qu'on n'a pas construit, sans les "
               "garanties de celui qui l'a fait. Tant que le constat "
               "contradictoire n'est pas dressé, aucun total n'a de valeur.",
    },
    "maintenance": {
        "nom": "Maintenance et renouvellement",
        "objet": "Coût annuel d'exploitation technique d'une installation en "
                 "service.",
        "postes": ["maintenance_preventive", "gros_entretien"],
        "sans_objet": {
            "clos_couvert": "aucun ouvrage neuf",
            "amenagement_salle": "aucun ouvrage neuf",
            "poste_livraison": "aucun ouvrage neuf",
            "distribution_secours": "aucun ouvrage neuf",
            "froid": "aucun ouvrage neuf",
            "fluides": "aucun ouvrage neuf",
            "incendie": "aucun ouvrage neuf",
            "surete": "aucun ouvrage neuf",
            "gtb_dcim": "aucun ouvrage neuf",
            "essais_mise_en_service": "aucun ouvrage neuf",
            "depose_curage": "aucun ouvrage neuf",
            "mise_en_securite": "aucun ouvrage neuf",
            "raccordement_existant": "aucun ouvrage neuf",
            "site_occupe": "aucun ouvrage neuf",
            "constat_reprise": "aucun ouvrage neuf",
        },
        "rang_alea": 1,
        "annuel": True,
        "dit": "SEULE NATURE DONT LE RÉSULTAT EST ANNUEL, et le module le "
               "marque : additionner une maintenance annuelle à un "
               "investissement produirait un nombre qui ne veut rien dire.",
    },
}

ORDRE_OPERATIONS = ["neuf", "extension", "rehabilitation_technique",
                    "reprise_travaux", "maintenance"]


# ═══════════════════════════════════════════════════════════════════════════
#  4. LES OPÉRATIONS DE RÉFÉRENCE — la place est faite, elle est vide
#
#     C'est ici que viennent les opérations RÉELLEMENT livrées par le cabinet,
#     avec leurs prix unitaires constatés. La liste est vide aujourd'hui, et
#     `sante()` le dit. Une liste vide qui se déclare vaut mieux qu'une liste
#     remplie d'ordres de grandeur trouvés ailleurs et présentés comme des
#     références maison.
# ═══════════════════════════════════════════════════════════════════════════

FORME_REFERENCE = {
    "reference": "identifiant interne de l'opération",
    "operation": "une clé de OPERATIONS",
    "annee_reception": "année de réception des travaux",
    "quantites": "les quantités constatées, clés de QUANTITES",
    "prix_unitaires": "les prix unitaires constatés, clés de POSTES, en € HT",
    "source": "marché notifié, décompte général définitif, ou état d'acompte",
}

REFERENCES = []


# ═══════════════════════════════════════════════════════════════════════════
#  5. LE CHIFFRAGE
# ═══════════════════════════════════════════════════════════════════════════

SEUIL_NON_CHIFFRE = 0.25   # part au-delà de laquelle le total cesse d'être une estimation


def _f(x, n=2):
    return round(float(x), n)


def operations():
    """Le référentiel des natures d'opération, prêt pour une page."""
    out = []
    for cle in ORDRE_OPERATIONS:
        o = OPERATIONS[cle]
        out.append({
            "cle": cle, "nom": o["nom"], "objet": o["objet"], "dit": o["dit"],
            "annuel": bool(o.get("annuel")),
            "rang_alea": o["rang_alea"],
            "postes": [dict(POSTES[p], cle=p) for p in o["postes"]],
            "sans_objet": [{"poste": p, "nom": POSTES[p]["nom"], "pourquoi": r}
                           for p, r in sorted(o["sans_objet"].items())],
            "quantites_utiles": sorted({POSTES[p]["assiette"] for p in o["postes"]}),
        })
    return out


def chiffrer(operation, quantites=None, prix_unitaires=None, provision_pct=None):
    """Le chiffrage d'une opération : quantité × prix unitaire, poste par poste.

    AUCUN PRIX N'EST EMBARQUÉ. Un poste sans prix unitaire ressort
    `non_chiffree` avec sa raison, et la part non chiffrée est publiée : c'est
    elle qui dit si le total est une estimation ou une addition partielle.
    """
    o = OPERATIONS.get(operation)
    if not o:
        return {"ok": False, "erreur": "operation_inconnue",
                "message": "Nature d'opération inconnue : %r. Attendu : %s."
                           % (operation, ", ".join(ORDRE_OPERATIONS))}
    q = dict(quantites or {})
    pu = dict(prix_unitaires or {})

    inconnues = sorted(set(q) - set(QUANTITES))
    if inconnues:
        return {"ok": False, "erreur": "quantite_inconnue",
                "message": "Quantité inconnue : %s. Une quantité non déclarée "
                           "ne porte aucune unité, donc aucun contrôle."
                           % ", ".join(inconnues)}
    postes_inconnus = sorted(set(pu) - set(POSTES))
    if postes_inconnus:
        return {"ok": False, "erreur": "poste_inconnu",
                "message": "Poste inconnu : %s." % ", ".join(postes_inconnus)}

    lignes, total, manque = [], 0.0, 0
    for cle in o["postes"]:
        P = POSTES[cle]
        a = P["assiette"]
        val_q = q.get(a)
        prix = pu.get(cle)
        ligne = {"poste": cle, "nom": P["nom"], "famille": P["famille"],
                 "famille_nom": FAMILLES[P["famille"]],
                 "quoi": P["quoi"], "assiette": a,
                 "assiette_nom": QUANTITES[a]["nom"],
                 "unite": QUANTITES[a]["unite"],
                 "quantite": val_q, "prix_unitaire": prix}
        if val_q is None and prix is None:
            ligne.update(etat="non_chiffree", montant=None,
                         dit="Ni quantité ni prix unitaire : ce poste n'est pas "
                             "chiffré, et il n'est pas nul pour autant.")
            manque += 1
        elif val_q is None:
            ligne.update(etat="non_chiffree", montant=None,
                         dit="Prix unitaire fourni mais quantité manquante (%s). "
                             "Le poste reste ouvert." % QUANTITES[a]["ou"])
            manque += 1
        elif prix is None:
            ligne.update(etat="non_chiffree", montant=None,
                         dit="Quantité connue, prix unitaire manquant. Aucun "
                             "prix n'est embarqué dans ce module : il vient de "
                             "votre bordereau ou d'une opération livrée.")
            manque += 1
        else:
            m = _f(float(val_q) * float(prix))
            ligne.update(etat="chiffree", montant=m,
                         dit="%s %s × %s € = %s € HT"
                             % (_f(val_q, 3), QUANTITES[a]["unite"], _f(prix),
                                _f(m)))
            total += m
        lignes.append(ligne)

    n = len(o["postes"])
    part_non_chiffree = _f(manque / n, 4) if n else 0.0

    # LA PROVISION. Le module ne fixe PAS sa valeur — il tient une relation
    # d'ordre entre natures, ce qui se défend, et refuse le coefficient, qui
    # ne se défend pas.
    prov = None
    if provision_pct is not None:
        taux = max(0.0, float(provision_pct)) / 100.0
        prov = {"taux_pct": _f(provision_pct, 2), "montant": _f(total * taux),
                "saisi": True}

    return {
        "ok": True, "version": VERSION,
        "operation": operation, "operation_nom": o["nom"],
        "annuel": bool(o.get("annuel")),
        "lignes": lignes,
        "par_famille": _par_famille(lignes),
        "total_chiffre": _f(total),
        "provision": prov,
        "total_avec_provision": _f(total + (prov["montant"] if prov else 0.0)),
        "postes_non_chiffres": manque, "postes_total": n,
        "part_non_chiffree": part_non_chiffree,
        "lecture": _lecture(o, manque, n, part_non_chiffree, total),
        "sans_objet": [{"poste": p, "nom": POSTES[p]["nom"], "pourquoi": r}
                       for p, r in sorted(o["sans_objet"].items())],
        "avertissement": AVERTISSEMENT,
    }


def _par_famille(lignes):
    out = {}
    for L in lignes:
        f = out.setdefault(L["famille"], {"famille": L["famille"],
                                          "nom": FAMILLES[L["famille"]],
                                          "montant": 0.0, "non_chiffres": 0})
        if L["etat"] == "chiffree":
            f["montant"] = _f(f["montant"] + L["montant"])
        else:
            f["non_chiffres"] += 1
    return [out[k] for k in sorted(out)]


def _lecture(o, manque, n, part, total):
    if manque == n:
        return ("Aucun poste n'est chiffré : ce tableau est une structure, pas "
                "une estimation. Il dit ce qu'il y a à chiffrer, et c'est déjà "
                "ce qui manque le plus tôt dans une opération.")
    if part > SEUIL_NON_CHIFFRE:
        return ("%d postes sur %d ne sont pas chiffrés, soit %.0f %% de la "
                "structure. Au-delà d'un quart, le total n'est plus une "
                "estimation : c'est l'addition de ce qu'on sait déjà, "
                "présentée comme un montant."
                % (manque, n, part * 100))
    if manque:
        return ("%d poste(s) sur %d restent ouverts. Le total porte donc sur "
                "le reste, et il faut le lire ainsi." % (manque, n))
    return ("Tous les postes de cette nature sont chiffrés. Le total vaut ce "
            "que valent les quantités et les prix fournis — ce module n'en "
            "vérifie aucun.")


def ordre_des_aleas():
    """LA RELATION D'ORDRE, à la place du coefficient qu'on attendrait.

    Le module ne dit pas de combien la provision d'une réhabilitation dépasse
    celle d'un neuf : personne ne peut le dire sans une base d'opérations
    livrées, et ce dépôt n'en a pas. Il dit qu'elle ne peut pas être
    inférieure, et pourquoi — ce qui suffit à empêcher la faute la plus
    courante : reprendre la provision d'un neuf sur une opération d'existant.
    """
    return {
        "regle": "La provision pour aléas croît avec la part d'existant et "
                 "avec ce qu'on ignore de lui. Elle ne se déduit pas d'un "
                 "coefficient : elle se décide, et elle se justifie.",
        "ordre": [{"operation": c, "nom": OPERATIONS[c]["nom"],
                   "rang": OPERATIONS[c]["rang_alea"],
                   "dit": OPERATIONS[c]["dit"]}
                  for c in sorted(ORDRE_OPERATIONS,
                                  key=lambda c: OPERATIONS[c]["rang_alea"])],
        "refus": "Aucune valeur de provision n'est proposée. Une valeur sans "
                 "relevé serait crédible et fausse, ce qui est la pire des "
                 "combinaisons.",
    }


AVERTISSEMENT = (
    "Ce tableau met en ordre et compte ; il ne dimensionne rien et ne vérifie "
    "aucune quantité. Les prix unitaires viennent de vous : aucun ratio de "
    "coût n'est embarqué, faute d'une base d'opérations livrées dans ce "
    "référentiel — 249 centres recensés, aucun ne publiant à la fois sa "
    "capacité et son investissement. Il ne remplace ni un métré, ni une "
    "consultation d'entreprises, ni l'avis d'un économiste."
)


def referentiel():
    return {"version": VERSION, "operations": operations(),
            "quantites": QUANTITES, "postes": POSTES, "familles": FAMILLES,
            "ordre_operations": ORDRE_OPERATIONS,
            "seuil_non_chiffre": SEUIL_NON_CHIFFRE,
            "aleas": ordre_des_aleas(),
            "forme_reference": FORME_REFERENCE,
            "references": REFERENCES,
            "avertissement": AVERTISSEMENT}


def sante():
    return {
        "module": "econome_dc", "version": VERSION,
        "operations": len(OPERATIONS), "postes": len(POSTES),
        "quantites": len(QUANTITES),
        "references_livrees": len(REFERENCES),
        "ratios_embarques": 0,
        "portee": "Chiffre des quantités par des prix fournis. Aucun ratio de "
                  "coût n'est embarqué : le référentiel du cabinet ne porte "
                  "aucune opération livrée avec capacité ET investissement.",
    }


# ═══════════════════════════════════════════════════════════════════════════
#  6. CONTRÔLE AU CHARGEMENT
#
#     Mieux vaut un service qui ne démarre pas qu'un chiffrage dont un poste
#     pointe vers une quantité qui n'existe pas : il ressortirait « non
#     chiffré » pour toujours, sans que rien ne dise pourquoi.
# ═══════════════════════════════════════════════════════════════════════════

def _verifier():
    for cle, P in POSTES.items():
        if P["assiette"] not in QUANTITES:
            raise RuntimeError(
                "econome_dc : le poste %s s'appuie sur la quantité inconnue %s"
                % (cle, P["assiette"]))
        if P["famille"] not in FAMILLES:
            raise RuntimeError("econome_dc : famille inconnue sur %s" % cle)
        for champ in ("nom", "quoi"):
            if not str(P.get(champ, "")).strip():
                raise RuntimeError("econome_dc : %s sans %s" % (cle, champ))

    if set(ORDRE_OPERATIONS) != set(OPERATIONS):
        raise RuntimeError("econome_dc : l'ordre d'affichage ne couvre pas les "
                           "natures d'opération")

    for cle, o in OPERATIONS.items():
        if not o["postes"]:
            raise RuntimeError("econome_dc : %s sans aucun poste" % cle)
        for p in o["postes"]:
            if p not in POSTES:
                raise RuntimeError("econome_dc : poste inconnu %s dans %s"
                                   % (p, cle))
        # CHAQUE POSTE EST SOIT RETENU, SOIT ÉCARTÉ AVEC SA RAISON. Un poste
        # simplement absent des deux listes disparaîtrait en silence — c'est
        # exactement la faute que ce module reproche aux ratios.
        couverts = set(o["postes"]) | set(o["sans_objet"])
        oublies = sorted(set(POSTES) - couverts)
        if oublies:
            raise RuntimeError(
                "econome_dc : %s ne dit rien des postes %s — un poste ni "
                "retenu ni écarté disparaît sans laisser de trace"
                % (cle, ", ".join(oublies)))
        double = sorted(set(o["postes"]) & set(o["sans_objet"]))
        if double:
            raise RuntimeError("econome_dc : %s retient ET écarte %s"
                               % (cle, ", ".join(double)))
        for p, raison in o["sans_objet"].items():
            if len(str(raison).strip()) < 15:
                raise RuntimeError(
                    "econome_dc : la raison d'écarter %s de %s est trop courte "
                    "pour être une raison" % (p, cle))
        if len(o["dit"]) < 80:
            raise RuntimeError(
                "econome_dc : %s ne dit pas ce qui la distingue — sans cela "
                "le lecteur croira qu'un coefficient suffisait" % cle)

    rangs = {c: OPERATIONS[c]["rang_alea"] for c in OPERATIONS}
    if not (rangs["neuf"] < rangs["extension"]
            < rangs["rehabilitation_technique"] < rangs["reprise_travaux"]):
        raise RuntimeError(
            "econome_dc : l'ordre des aléas ne croît plus avec la part "
            "d'existant — c'est la seule chose que ce module affirme sur les "
            "provisions, et elle doit tenir")

    if REFERENCES:
        for r in REFERENCES:
            if set(FORME_REFERENCE) - set(r):
                raise RuntimeError(
                    "econome_dc : une opération de référence sans %s"
                    % ", ".join(sorted(set(FORME_REFERENCE) - set(r))))


_verifier()
