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
    "surface_batiment_m2": {
        "nom": "Surface totale du bâtiment", "unite": "m²",
        "ou": "Surface de plancher du permis, ou surface hors œuvre du DOE "
              "pour un bâtiment existant.",
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
#  2 bis. D'OÙ VIENT LE PRIX — la colonne qui manquait
#
#     UN PRIX SANS PROVENANCE NE SE DÉFEND PAS SIX MOIS PLUS TARD. C'est la
#     question que pose le maître d'ouvrage devant l'écart, et celle qu'on ne
#     sait plus trancher si on ne l'a pas notée en saisissant. Le module ne
#     propose donc AUCUN montant — il n'en a pas —, mais il propose la seule
#     chose qu'il puisse fournir de fiable : la nature de la source, et ce
#     qu'elle vaut.
#
#     LES PROVENANCES SONT ORDONNÉES, du plus opposable au moins engageant. Cet
#     ordre est le seul jugement que le module porte sur un prix.
# ═══════════════════════════════════════════════════════════════════════════

PROVENANCES = {
    "marche_notifie": {
        "nom": "Marché notifié", "rang": 1,
        "vaut": "Un prix signé sur une opération réelle. C'est le seul qui "
                "engage quelqu'un.",
        "reserve": "Daté : un prix de marché vieillit, et la révision se "
                   "calcule, elle ne s'estime pas.",
    },
    "dgd": {
        "nom": "Décompte général définitif", "rang": 2,
        "vaut": "Le prix RÉELLEMENT payé, travaux modificatifs compris — le "
                "plus instructif des cinq, et le plus rare à obtenir.",
        "reserve": "Il porte les aléas de CETTE opération, qui ne sont pas "
                   "ceux de la prochaine.",
    },
    "devis": {
        "nom": "Devis d'entreprise", "rang": 3,
        "vaut": "Un prix proposé sur un besoin décrit. Il engage l'entreprise "
                "tant qu'il est valable.",
        "reserve": "Un devis d'étude n'est pas un devis de marché : la "
                   "consultation fait bouger les prix dans les deux sens.",
    },
    "bordereau": {
        "nom": "Bordereau de prix unitaires", "rang": 4,
        "vaut": "Votre base de prix, tenue et révisée. Elle vaut ce que vaut "
                "sa mise à jour.",
        "reserve": "Un bordereau non daté n'est plus un bordereau, c'est un "
                   "souvenir.",
    },
    "estimation": {
        "nom": "Estimation interne", "rang": 5,
        "vaut": "Le jugement de l'économiste, faute de mieux. Légitime en "
                "phase amont, à condition d'être annoncé comme tel.",
        "reserve": "C'est la provenance qu'on oublie de remplacer. Elle doit "
                   "se voir dans le tableau jusqu'à ce qu'elle disparaisse.",
    },
}

ORDRE_PROVENANCES = ["marche_notifie", "dgd", "devis", "bordereau", "estimation"]


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


def _nb(x, n=2):
    """UN NOMBRE ÉCRIT COMME ON L'ÉCRIT EN FRANÇAIS, et seulement dans les
    phrases. Les montants sortaient en clair du gabarit Python — « 612000.0 € »
    au milieu d'une page où tout le reste affiche « 612 000 € ». Le lecteur ne
    doute pas du chiffre, il doute de la page.

    Les valeurs BRUTES restent publiées dans leurs propres champs : cette
    fonction n'entre dans aucun calcul, elle habille du texte.
    """
    v = round(float(x), n)
    ent = int(abs(v))
    # ESPACE FINE INSÉCABLE (U+202F), écrite en échappement pour qu'on ne
    # la prenne pas pour une espace ordinaire en relisant : celle-ci
    # laisserait « 612 » finir une ligne et « 000 » commencer la suivante.
    s = "{:,}".format(ent).replace(",", "\u202f")
    reste = round(abs(v) - ent, n)
    if n > 0 and reste > 0:
        s += "," + ("%.*f" % (n, reste))[2:].rstrip("0")
    return ("−" if v < 0 else "") + s


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


def chiffrer(operation, quantites=None, prix_unitaires=None, provision_pct=None,
             provenances=None):
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
    pv = dict(provenances or {})
    prov_inconnues = sorted(set(pv.values()) - set(PROVENANCES))
    if prov_inconnues:
        return {"ok": False, "erreur": "provenance_inconnue",
                "message": "Provenance inconnue : %s. Attendu : %s."
                           % (", ".join(prov_inconnues),
                              ", ".join(ORDRE_PROVENANCES))}

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

    lignes, total, manque, sans_source = [], 0.0, 0, 0
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
                             % (_nb(val_q, 3), QUANTITES[a]["unite"], _nb(prix),
                                _nb(m)))
            total += m
        # LA PROVENANCE ACCOMPAGNE LE PRIX, ou son absence est dite. Un prix
        # sans source ne se défend pas six mois plus tard, et c'est exactement
        # le moment où la question se pose.
        src = pv.get(cle)
        if prix is None:
            ligne.update(provenance=None, provenance_nom=None, provenance_rang=None)
        elif src:
            V = PROVENANCES[src]
            ligne.update(provenance=src, provenance_nom=V["nom"],
                         provenance_rang=V["rang"],
                         provenance_reserve=V["reserve"])
        else:
            ligne.update(provenance=None, provenance_nom=None,
                         provenance_rang=None,
                         provenance_manquante="Prix saisi sans provenance : il "
                         "sera indéfendable devant un écart. Nommez la source.")
            sans_source += 1
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
        "prix_sans_provenance": sans_source,
        "provenances_employees": sorted(
            {L["provenance"] for L in lignes if L.get("provenance")},
            key=lambda c: PROVENANCES[c]["rang"]),
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


def suggestions(operation=None):
    """CE QUE LE MODULE PEUT PROPOSER, ET IL FAUT LE LIRE AVANT DE L'ATTENDRE.

    Aucune valeur n'est inventée. Les propositions viennent EXCLUSIVEMENT des
    opérations que vous avez livrées et enregistrées dans REFERENCES. Tant que
    cette liste est vide — c'est le cas aujourd'hui — le module rend une liste
    vide et le dit, plutôt qu'un ordre de grandeur trouvé ailleurs.

    POURQUOI PAS D'ORDRES DE GRANDEUR DE FILIÈRE. Il en existe de publiés, au
    mégawatt et pour l'opération ENTIÈRE. En tirer un prix par lot demanderait
    de les répartir par une clé qu'aucune source ne donne : deux hypothèses
    enchaînées, un nombre crédible, et personne pour dire d'où il sort. C'est
    exactement le genre de chiffre qui se retourne contre celui qui le publie.
    """
    par_poste = {}
    for r in REFERENCES:
        if operation and r.get("operation") != operation:
            continue
        for poste, prix in (r.get("prix_unitaires") or {}).items():
            if poste not in POSTES:
                continue
            par_poste.setdefault(poste, []).append(
                {"valeur": _f(prix), "reference": r.get("reference"),
                 "annee": r.get("annee_reception"), "source": r.get("source")})
    out = {}
    for poste, vals in par_poste.items():
        v = sorted(x["valeur"] for x in vals)
        out[poste] = {
            "observations": vals, "n": len(vals),
            "min": v[0], "max": v[-1],
            # LA MÉDIANE, PAS LA MOYENNE : sur deux ou trois relevés, une
            # moyenne se laisse emporter par l'exception, qui est justement ce
            # qu'on veut voir.
            "mediane": v[len(v) // 2] if len(v) % 2 else _f((v[len(v) // 2 - 1]
                                                             + v[len(v) // 2]) / 2),
        }
    return {
        "operation": operation, "postes": out,
        "references_disponibles": len(REFERENCES),
        "dit": ("Aucune opération livrée n'est enregistrée : le module ne "
                "propose donc aucun prix. Il en proposera dès la première "
                "versée dans REFERENCES — et ce seront les vôtres, pas des "
                "ordres de grandeur de filière."
                if not REFERENCES else
                "Propositions tirées de %d opération(s) que vous avez livrée(s). "
                "Ce sont des OBSERVATIONS, pas un barème : elles portent le "
                "contexte de leur opération." % len(REFERENCES)),
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
            "provenances": PROVENANCES, "ordre_provenances": ORDRE_PROVENANCES,
            "suggestions": suggestions(),
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
        "provenances": len(PROVENANCES),
        "quantites_orphelines": sorted(
            set(QUANTITES) - {P["assiette"] for P in POSTES.values()}),
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

    # UNE QUANTITÉ QUE NUL POSTE NE CONSOMME NE SERAIT JAMAIS DEMANDÉE par le
    # formulaire — elle occuperait le référentiel sans que rien ne la lise.
    # Trois y dormaient : surface des locaux techniques, nombre de baies, durée
    # de contrat. Elles reviendront le jour où un poste s'y appuiera.
    orphelines = sorted(set(QUANTITES) - {P["assiette"] for P in POSTES.values()})
    if orphelines:
        raise RuntimeError(
            "econome_dc : quantité déclarée que nul poste ne consomme : %s"
            % ", ".join(orphelines))

    if set(ORDRE_PROVENANCES) != set(PROVENANCES):
        raise RuntimeError("econome_dc : l'ordre des provenances ne les couvre pas")
    rangs = sorted(PROVENANCES[c]["rang"] for c in PROVENANCES)
    if rangs != list(range(1, len(PROVENANCES) + 1)):
        raise RuntimeError(
            "econome_dc : les rangs de provenance ne forment pas une suite — "
            "c'est le seul jugement que ce module porte sur un prix")

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


# ═══════════════════════════════════════════════════════════════════════════
#  7. LE PONT VERS LA MAÎTRISE D'ŒUVRE
#
#     CE QU'IL APPORTE, ET CE N'EST PAS QUE DU TRANSPORT. Le barème de
#     maîtrise d'œuvre a besoin de DEUX choses : le montant des travaux, et la
#     part du lot technique dans ce montant. Sans la seconde, il retombe sur
#     une hypothèse à 70 % dont son propre texte dit qu'elle « pèse plus lourd
#     que n'importe quel taux du barème » — parce que les taux y sont inversés
#     entre clos-couvert et technique.
#
#     ICI, CETTE PART SE CALCULE. Les postes de ce module portent leur famille :
#     ce qui relève du bâtiment, ce qui relève des lots techniques. Le rapport
#     n'est donc plus une hypothèse, c'est une conséquence du chiffrage.
#
#     DEUX INCOMPLÉTUDES, JAMAIS MÉLANGÉES. Les travaux ont leurs postes non
#     chiffrés ; la maîtrise d'œuvre a ses missions sans taux relevé. Les
#     additionner en un seul « taux de complétude » produirait un indicateur
#     que ni l'un ni l'autre ne défend. Ils sont publiés côte à côte.
# ═══════════════════════════════════════════════════════════════════════════

# ───────────────────────────────────────────────────────────────────────────
#  7 bis. LES MISSIONS SELON LA NATURE DE L'OPÉRATION
#
#  « Selon les projets choisis » : une réhabilitation de lots techniques
#  n'appelle pas les mêmes intervenants qu'une construction neuve, et une
#  maintenance n'en appelle aucun au pourcentage. Le module PROPOSE une
#  sélection par nature ; il ne l'impose pas — les cases restent décochables,
#  sauf les deux missions que la loi rend obligatoires, que moe_dc recompte
#  même décochées.
#
#  TROIS ÉTATS, ET LE TROISIÈME EST LE PLUS UTILE :
#    · retenues     — proposée cochée, avec ce qu'elle vient faire ici ;
#    · sans_objet   — écartée, avec la raison, tirée de la définition même de
#                     la nature d'opération (pas d'une doctrine) ;
#    · a_qualifier  — RETENUE MAIS INCERTAINE : le module dit ce qui décide, et
#                     refuse de décider à la place. C'est l'état qu'un tableau
#                     ordinaire supprime, et c'est celui qui évite de facturer
#                     une mission inutile ou d'en oublier une obligatoire.
# ───────────────────────────────────────────────────────────────────────────

_TOUTES_MISSIONS = [
    "architecte", "moex", "opc", "coord_etudes", "bet_structure",
    "bet_fluides", "bet_environnement", "bet_acoustique", "bet_divers",
    "commissioning", "bet_vrd", "controle_technique", "sps",
    "bet_economiste", "bet_incendie", "coord_ssi",
]

# Ce qui reste vrai quelle que soit la nature : le module ne qualifie ni le
# classement ICPE, ni la catégorie du SSI, ni la catégorie d'ouvrage qui rend
# le contrôle technique obligatoire. Il le redit à chaque opération plutôt que
# de le dire une fois en préambule, où personne ne le lit.
_A_QUALIFIER_TOUJOURS = {
    "bet_environnement": "Le classement ICPE dépend des puissances installées "
                         "et des fluides frigorigènes retenus. Ce module ne "
                         "les qualifie pas : c'est l'arrêté de classement qui "
                         "décide, pas un chiffrage.",
    "coord_ssi": "L'obligation de coordination SSI dépend de la CATÉGORIE du "
                 "système (NF S 61-931), que ce module ne qualifie pas. "
                 "Retenue par prudence : l'oublier en catégorie A coûte plus "
                 "cher que de la porter à tort.",
    "controle_technique": "Obligatoire par catégorie d'ouvrage. L'hypothèse "
                          "retenue est qu'un centre de données y entre ; à "
                          "vérifier sur votre projet, jamais à supposer.",
}


def _missions(retenues, sans_objet, a_qualifier, dit):
    q = dict(_A_QUALIFIER_TOUJOURS)
    q.update(a_qualifier or {})
    # Une mission écartée n'a pas à être « à qualifier » : elle n'est pas là.
    q = {c: v for c, v in q.items() if c not in sans_objet}
    return {"retenues": retenues, "sans_objet": sans_objet,
            "a_qualifier": q, "dit": dit}


MISSIONS_PAR_OPERATION = {
    "neuf": _missions(
        retenues=list(_TOUTES_MISSIONS),
        sans_objet={},
        a_qualifier={},
        dit="Aucune mission n'est sans objet sur une construction neuve : le "
            "bâtiment, les lots techniques, les VRD et les autorisations "
            "existent tous. C'est la seule nature où la liste se prend "
            "entière — et donc la seule où l'économie se fait sur les PHASES, "
            "pas sur les missions."),

    "extension": _missions(
        retenues=list(_TOUTES_MISSIONS),
        sans_objet={},
        a_qualifier={
            "opc": "L'OPC pèse ici plus qu'en neuf : les coupures se "
                   "négocient avec l'exploitant, et le planning n'est plus "
                   "commandé par le chantier seul. Le taux relevé vient d'une "
                   "opération neuve — vérifiez-le avant de le garder.",
            "sps": "Chantier et exploitation coexistent : la coordination "
                   "porte aussi sur l'interférence avec le personnel du site, "
                   "ce que le taux relevé en neuf ne couvre pas.",
        },
        dit="L'extension appelle les mêmes missions que le neuf, mais deux "
            "d'entre elles n'y font pas le même travail : le pilotage et la "
            "coordination de sécurité doivent tenir un site qui continue de "
            "fonctionner. Le barème, lui, vient d'une opération neuve."),

    "rehabilitation_technique": _missions(
        retenues=["architecte", "moex", "opc", "coord_etudes", "bet_structure",
                  "bet_fluides", "bet_environnement", "bet_acoustique",
                  "bet_divers", "commissioning", "controle_technique", "sps",
                  "bet_economiste", "bet_incendie", "coord_ssi"],
        sans_objet={
            "bet_vrd": "Le bâtiment est conservé et l'opération ne crée ni "
                       "voirie ni réseau extérieur. À REQUALIFIER si un "
                       "aéroréfrigérant, une cuve ou une arrivée haute "
                       "tension sortent du bâtiment : ce sont des VRD.",
        },
        a_qualifier={
            "architecte": "SON MONTANT VA RESSORTIR TRÈS BAS, et ce n'est pas "
                          "une erreur de calcul : son taux principal porte sur "
                          "le clos-couvert, nul ici puisque le bâtiment est "
                          "conservé. Son intervention réelle — désenfumage, "
                          "percements, autorisations — ne disparaît pas pour "
                          "autant. Si elle existe, elle se rémunère au temps "
                          "passé, pas à ce pourcentage.",
            "bet_structure": "Retenue, et ce n'est pas une formalité : "
                             "reprendre des charges de groupes froids en "
                             "toiture ou des socles d'onduleurs sur un "
                             "plancher existant est la découverte la plus "
                             "chère de cette nature d'opération.",
        },
        dit="Le bâtiment est conservé : ce qui portait sur le clos-couvert "
            "s'effondre mécaniquement dans le barème, parce que son assiette "
            "est nulle. Le module l'affiche au lieu de le corriger en douce — "
            "un montant bas qui s'explique vaut mieux qu'un montant redressé "
            "par une clé inventée."),

    "reprise_travaux": _missions(
        retenues=list(_TOUTES_MISSIONS),
        sans_objet={},
        a_qualifier={
            "opc": "LA MISSION CENTRALE DE CETTE NATURE. Reprendre un chantier "
                   "interrompu, c'est d'abord réordonnancer ce qui reste et "
                   "réarticuler des marchés qui ne se suivent plus. Le taux "
                   "relevé sur une opération neuve la sous-estime "
                   "probablement ; ce module ne sait pas de combien.",
            "bet_economiste": "Elle commence par un CONSTAT CONTRADICTOIRE de "
                              "ce qui est exécuté, pas par un métré de ce qui "
                              "reste. Tant que ce constat n'est pas dressé, "
                              "aucun total de travaux n'a de valeur — et donc "
                              "aucun pourcentage assis dessus.",
            "controle_technique": "L'ouvrage a été commencé par un tiers : le "
                                  "contrôleur technique qui reprend n'a pas "
                                  "visé ce qui est déjà couvert. Sa mission "
                                  "n'est pas celle d'un ouvrage neuf.",
        },
        dit="Toutes les missions restent appelées, mais aucune ne fait le "
            "travail qu'elle ferait en neuf : on intervient sur un existant "
            "qu'on n'a pas construit, sans les garanties de celui qui l'a "
            "fait. C'est la nature où le pourcentage est le plus fragile."),

    "maintenance": _missions(
        retenues=[],
        sans_objet={c: "Une maintenance est un coût ANNUEL d'exploitation : "
                       "aucun honoraire ne s'y calcule en pourcentage de "
                       "travaux, faute de travaux."
                    for c in _TOUTES_MISSIONS},
        a_qualifier={},
        dit="Aucune mission n'est chiffrée ici, et l'obligation, elle, ne "
            "disparaît pas pour autant : une intervention de maintenance qui "
            "fait coexister plusieurs entreprises appelle un coordonnateur "
            "SPS comme un chantier. Ce que ce module refuse, c'est de le "
            "facturer au pourcentage d'un montant annuel — pas d'en rappeler "
            "l'existence."),
}


def missions_pour(operation):
    """Les missions proposées pour une nature d'opération, et pourquoi.

    Rend toujours les trois états, y compris pour la maintenance : « aucune »
    est une réponse, et elle se motive comme les autres.
    """
    o = MISSIONS_PAR_OPERATION.get(operation)
    if not o:
        return {"ok": False, "erreur": "operation_inconnue",
                "message": "Nature d'opération inconnue : %s" % operation,
                "connues": ORDRE_OPERATIONS}
    try:
        import moe_dc
        par = {m["cle"]: m for m in moe_dc.MISSIONS}
        obligatoires = list(moe_dc.OBLIGATOIRES)
    except Exception:
        par, obligatoires = {}, []

    def _m(c):
        m = par.get(c) or {}
        # UNE MISSION SANS TAUX RELEVÉ SE SIGNALE ICI, pas seulement au total :
        # le lecteur qui coche la ligne doit savoir qu'il devra saisir un taux,
        # sinon il croira l'avoir chiffrée en la cochant.
        sans_taux = bool(m) and (m.get("taux_sc") is None
                                 or m.get("taux_mep") is None)
        return {"cle": c, "nom": m.get("nom", c),
                "role": m.get("role"),
                "obligatoire": c in obligatoires,
                "a_qualifier": o["a_qualifier"].get(c),
                "sans_taux": sans_taux,
                "hors_releve": m.get("hors_releve")}

    return {
        "ok": True, "operation": operation,
        "operation_nom": OPERATIONS[operation]["nom"],
        "retenues": [_m(c) for c in o["retenues"]],
        "sans_objet": [{"cle": c, "nom": (par.get(c) or {}).get("nom", c),
                        "raison": r}
                       for c, r in sorted(o["sans_objet"].items())],
        "dit": o["dit"],
        "reserve": "Cette sélection est une PROPOSITION tirée de la nature de "
                   "l'opération, pas de votre projet. Les missions "
                   "obligatoires restent comptées même décochées : les "
                   "retirer afficherait une économie qui n'aura pas lieu.",
    }


def _verifier_missions():
    """LA MÊME DISCIPLINE QUE POUR LES POSTES, appliquée aux missions.

    Une mission ni retenue ni écartée disparaîtrait en silence d'une nature
    d'opération — et personne ne saurait qu'elle a existé. Et si moe_dc gagne
    une mission demain sans qu'on décide de sa place ici, le service ne doit
    pas démarrer en la faisant disparaître partout.
    """
    if set(MISSIONS_PAR_OPERATION) != set(OPERATIONS):
        raise RuntimeError(
            "econome_dc : les missions ne sont pas décidées pour toutes les "
            "natures d'opération — %s"
            % sorted(set(OPERATIONS) ^ set(MISSIONS_PAR_OPERATION)))

    for cle, o in MISSIONS_PAR_OPERATION.items():
        couvertes = set(o["retenues"]) | set(o["sans_objet"])
        oubliees = sorted(set(_TOUTES_MISSIONS) - couvertes)
        if oubliees:
            raise RuntimeError(
                "econome_dc : %s ne dit rien des missions %s — ni retenues ni "
                "écartées, elles disparaîtraient sans laisser de trace"
                % (cle, ", ".join(oubliees)))
        double = sorted(set(o["retenues"]) & set(o["sans_objet"]))
        if double:
            raise RuntimeError("econome_dc : %s retient ET écarte %s"
                               % (cle, ", ".join(double)))
        inconnues = sorted(couvertes - set(_TOUTES_MISSIONS))
        if inconnues:
            raise RuntimeError("econome_dc : mission inconnue dans %s : %s"
                               % (cle, ", ".join(inconnues)))
        for m, raison in o["sans_objet"].items():
            if len(str(raison).strip()) < 30:
                raise RuntimeError(
                    "econome_dc : écarter %s de %s sans raison lisible — "
                    "c'est la faute que ce module reproche aux ratios"
                    % (m, cle))
        # Une mission « à qualifier » qui ne serait pas retenue n'aurait aucun
        # effet : l'incertitude s'afficherait sur une ligne absente.
        hors = sorted(set(o["a_qualifier"]) - set(o["retenues"]))
        if hors:
            raise RuntimeError(
                "econome_dc : %s qualifie %s sans la retenir — l'avertissement "
                "porterait sur une ligne qui ne s'affiche pas"
                % (cle, ", ".join(hors)))
        if len(o["dit"]) < 80:
            raise RuntimeError(
                "econome_dc : %s ne dit pas ce qui distingue sa sélection de "
                "missions" % cle)

    # LES OBLIGATOIRES NE S'ÉCARTENT PAS D'UNE OPÉRATION DE TRAVAUX. La seule
    # nature qui les écarte est la maintenance, et elle ne le fait pas parce
    # que l'obligation tomberait — son texte le dit — mais parce qu'aucun
    # pourcentage de travaux ne s'y calcule.
    try:
        import moe_dc
    except Exception:
        # Le pont dira lui-même « module_absent » ; faire échouer le chiffrage
        # des travaux parce que le barème d'honoraires manque serait pire.
        return
    connues = {m["cle"] for m in moe_dc.MISSIONS}
    if connues != set(_TOUTES_MISSIONS):
        raise RuntimeError(
            "econome_dc : le barème porte des missions dont la place par "
            "nature d'opération n'est pas décidée : %s"
            % ", ".join(sorted(connues ^ set(_TOUTES_MISSIONS))))
    for cle, o in MISSIONS_PAR_OPERATION.items():
        if OPERATIONS[cle].get("annuel"):
            continue
        manquantes = [c for c in moe_dc.OBLIGATOIRES if c not in o["retenues"]]
        if manquantes:
            raise RuntimeError(
                "econome_dc : %s écarte une mission obligatoire (%s) — ce "
                "serait afficher une économie qui n'aura pas lieu"
                % (cle, ", ".join(manquantes)))


_verifier_missions()


FAMILLE_VERS_ASSIETTE = {
    "batiment": "clos_couvert",
    "technique": "technique",
    # L'EXISTANT NE TRANCHE PAS. Dépose, curage, mise en sécurité et site
    # occupé servent les deux assiettes à des parts que rien ne permet de
    # partager. Ils entrent dans le MONTANT des travaux — ce sont des travaux —
    # mais pas dans le calcul du RAPPORT, qu'ils fausseraient d'un côté ou de
    # l'autre selon une clé inventée.
    "existant": None,
    # L'EXPLOITATION N'EST PAS UN INVESTISSEMENT : elle est annuelle et sort
    # de l'assiette d'honoraires.
    "exploitation": "hors",
}


def avec_maitrise_oeuvre(chiffrage, phases=None, missions=None, taux_perso=None):
    """Le chiffrage des travaux, prolongé par celui de la maîtrise d'œuvre.

    Rend les deux, leur liaison, et les DEUX mesures d'incomplétude — celle des
    travaux et celle des honoraires — sans jamais les fondre en une.
    """
    if not chiffrage or not chiffrage.get("ok"):
        return {"ok": False, "erreur": "chiffrage_absent",
                "message": "Aucun chiffrage de travaux : la maîtrise d'œuvre "
                           "se calcule SUR les travaux, elle ne les remplace "
                           "pas."}
    if chiffrage.get("annuel"):
        return {"ok": False, "erreur": "operation_annuelle",
                "message": "Une maintenance est un coût annuel d'exploitation, "
                           "pas une opération de travaux : aucun honoraire de "
                           "maîtrise d'œuvre ne s'y calcule au pourcentage."}
    try:
        import moe_dc
    except Exception:
        return {"ok": False, "erreur": "module_absent",
                "message": "Le barème de maîtrise d'œuvre n'est pas disponible."}

    # « SELON LES PROJETS CHOISIS » : à défaut de sélection explicite, on prend
    # celle que la nature d'opération propose — et non les seize missions, qui
    # feraient payer des VRD sur un bâtiment conservé. Une sélection reçue de
    # l'appelant prime : la proposition n'est pas une contrainte.
    propose = missions_pour(chiffrage["operation"])
    if missions is None and propose.get("ok"):
        missions = [m["cle"] for m in propose["retenues"]]

    par_famille = {f["famille"]: f["montant"] for f in chiffrage["par_famille"]}
    bat = float(par_famille.get("batiment") or 0.0)
    tech = float(par_famille.get("technique") or 0.0)
    exi = float(par_famille.get("existant") or 0.0)
    assiette_eur = bat + tech + exi
    if assiette_eur <= 0:
        return {"ok": False, "erreur": "assiette_vide",
                "message": "Aucun poste de travaux n'est chiffré : il n'y a "
                           "pas d'assiette sur laquelle asseoir des honoraires."}

    socle = bat + tech
    part_tech = (tech / socle) if socle > 0 else None
    res = moe_dc.honoraires_directs(
        [assiette_eur / 1e6, assiette_eur / 1e6],
        part_technique=part_tech, phases=phases, missions=missions,
        taux_perso=taux_perso)
    if not res.get("ok"):
        return {"ok": False, "erreur": "moe_refuse", "detail": res}

    moe_eur = float(res["total_meur"][1]) * 1e6
    return {
        "ok": True, "version": VERSION,
        "travaux": {
            "operation": chiffrage["operation"],
            "operation_nom": chiffrage["operation_nom"],
            "assiette_eur": _f(assiette_eur),
            "detail": {"batiment_eur": _f(bat), "technique_eur": _f(tech),
                       "existant_eur": _f(exi)},
            "postes_non_chiffres": chiffrage["postes_non_chiffres"],
            "postes_total": chiffrage["postes_total"],
            "part_non_chiffree": chiffrage["part_non_chiffree"],
        },
        "part_technique": {
            "valeur": _f(part_tech, 4) if part_tech is not None else None,
            "nature": "calculee" if part_tech is not None else "indisponible",
            "dit": ("Calculée sur le chiffrage : %s %% des travaux de bâtiment "
                    "et de technique relèvent des lots techniques. Le barème "
                    "n'a donc pas eu à retomber sur son hypothèse à 70 %%, dont "
                    "son propre texte dit qu'elle pèse plus lourd que n'importe "
                    "quel taux." % _nb((part_tech or 0) * 100, 1)
                   if part_tech is not None else
                   "Ni le bâtiment ni la technique ne sont chiffrés : le "
                   "rapport ne se calcule pas, et le barème retombe sur son "
                   "hypothèse."),
            "exclus": "Les sujétions d'existant (%s €) entrent dans l'assiette "
                      "mais pas dans le rapport : elles servent les deux côtés "
                      "à des parts que rien ne permet de partager." % _nb(exi),
        },
        "maitrise_oeuvre": {
            "total_eur": _f(moe_eur),
            "taux_effectif_pct": res["taux_effectif_pct"][1],
            "par_phase": res["par_phase"],
            "missions_ouvertes": res.get("missions_ouvertes") or [],
            "lecture": res.get("lecture_ouvertes"),
        },
        "missions_proposees": propose if propose.get("ok") else None,
        "missions_ecartees": (propose.get("sans_objet") or []
                              if propose.get("ok") else []),
        "kpi": _kpi(assiette_eur, moe_eur, chiffrage, res),
        "avertissement": AVERTISSEMENT,
    }


def _kpi(assiette_eur, moe_eur, chiffrage, res):
    """LES INDICATEURS, ET LE REFUS D'EN FABRIQUER UN TREIZIÈME.

    Deux incomplétudes cohabitent : des postes de travaux sans prix, des
    missions de maîtrise d'œuvre sans taux. Les fondre en un « taux de
    complétude » unique donnerait un nombre que ni l'un ni l'autre ne défend —
    et c'est celui-là qu'on citerait. Ils restent séparés.
    """
    ouvertes = len(res.get("missions_ouvertes") or [])
    total_missions = len([m for m in res.get("missions", [])])
    return {
        "part_moe_sur_travaux_pct": _f(moe_eur / assiette_eur * 100, 2)
        if assiette_eur else None,
        "part_moe_dans_operation_pct": _f(moe_eur / (assiette_eur + moe_eur) * 100, 2)
        if (assiette_eur + moe_eur) else None,
        "cout_operation_eur": _f(assiette_eur + moe_eur),
        "travaux_non_chiffres": {
            "postes": chiffrage["postes_non_chiffres"],
            "sur": chiffrage["postes_total"],
            "part_pct": _f(chiffrage["part_non_chiffree"] * 100, 1),
        },
        "moe_sans_taux": {
            "missions": ouvertes, "sur": total_missions,
            "part_pct": _f(ouvertes / total_missions * 100, 1) if total_missions else None,
        },
        "refus": "Aucun indicateur unique ne fond ces deux incomplétudes : "
                 "elles ne portent pas sur la même chose, et leur moyenne ne "
                 "voudrait rien dire. Le lecteur les lit toutes les deux.",
        "lecture": _lecture_kpi(assiette_eur, moe_eur, chiffrage, ouvertes),
    }


def _lecture_kpi(assiette_eur, moe_eur, chiffrage, ouvertes):
    bouts = []
    if assiette_eur:
        bouts.append("La maîtrise d'œuvre représente %s %% des travaux chiffrés."
                     % _nb(moe_eur / assiette_eur * 100, 2))
    if chiffrage["part_non_chiffree"] > SEUIL_NON_CHIFFRE:
        bouts.append("MAIS %d poste(s) de travaux sur %d ne sont pas chiffrés : "
                     "l'assiette est partielle, donc les honoraires aussi."
                     % (chiffrage["postes_non_chiffres"], chiffrage["postes_total"]))
    if ouvertes:
        bouts.append("Et %d mission(s) de maîtrise d'œuvre attendent leur taux : "
                     "elles ne sont pas dans ce montant." % ouvertes)
    if len(bouts) == 1:
        bouts.append("Les deux chiffrages sont complets.")
    return " ".join(bouts)
