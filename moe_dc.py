"""HONORAIRES DE MAÎTRISE D'ŒUVRE — par mission et par phase.

CE QUE CE MODULE AJOUTE. Le module d'enveloppe chiffre les travaux et porte une
ligne « Études, maîtrise d'œuvre et autorisation » en pourcentage global. C'est
assez pour un ordre de grandeur, et beaucoup trop peu pour décider : un maître
d'ouvrage n'achète pas « de la maîtrise d'œuvre », il achète TREIZE missions
distinctes sur CINQ phases, et il choisit lesquelles il confie.

D'OÙ VIENNENT CES TAUX. D'un barème relevé sur un projet réel de centre de
données en Île-de-France (bilan de 2018), reconstitué mission par mission et
phase par phase. Ce n'est PAS une statistique de marché : c'est UN projet, et il
est cité comme tel. Chaque taux est modifiable — vos propres offres priment sur
un relevé, comme vos devis priment sur l'hypothèse de coût au mégawatt.

TROIS PARTIS PRIS QUI CHANGENT LE RÉSULTAT, ET QU'IL FAUT LIRE AVANT LES CHIFFRES

  1. L'ASSIETTE N'EST PAS L'ENVELOPPE. Les honoraires se calculent sur les
     TRAVAUX. En sont exclus la ligne de maîtrise d'œuvre elle-même — on ne
     paie pas d'honoraires sur des honoraires — et la provision pour aléas, qui
     n'est pas un ouvrage. Prendre l'enveloppe entière pour assiette gonfle la
     note d'environ un huitième, sans que rien ne le signale.

  2. DEUX ASSIETTES, DEUX BARÈMES, ET L'ÉCART EST ÉNORME. Sur le clos-couvert,
     l'architecte pèse 4 % et les fluides 0,5 %. Sur le lot technique — la
     partie qui fait un centre de données —, c'est l'inverse : l'architecte
     tombe à 0,5 % et les fluides montent à 2 %. Appliquer un taux unique à
     l'ensemble se trompe dans les deux sens à la fois, et d'autant plus que la
     part technique est grande — sur le projet relevé, elle faisait 70 % des
     travaux.

  3. RETIRER UNE PHASE NE FAIT PAS QU'ÉCONOMISER. Elle produit un livrable et
     couvre un risque ; sans elle, le livrable n'existe pas et le risque
     revient au maître d'ouvrage. Chaque phase porte donc ce qu'elle produit ET
     ce que son absence coûte. Un calculateur qui afficherait seulement la
     baisse du montant conseillerait de tout retirer.

DEUX MISSIONS NE SE CHOISISSENT PAS. Le coordonnateur SPS et le contrôle
technique relèvent d'obligations légales dès que leurs conditions sont réunies.
Les présenter comme des options d'économie serait un mauvais conseil, et le
module refuse de le faire : il les marque, et les compte même si on les
décoche.
"""

VERSION = "2026-08-a"

SOURCE = {
    "origine": "Barème d'honoraires relevé sur un projet de centre de données "
               "en Île-de-France — bilan promoteur de 2018, décomposé par "
               "mission et par phase.",
    "nature": "relevé de projet",
    "reserve": "UN projet n'est pas un marché. Ces taux donnent une structure "
               "et un ordre de grandeur ; ils ne remplacent pas les offres que "
               "vous recevrez. Chacun est modifiable.",
    "anonymisation": "Ni le maître d'ouvrage, ni le montant du projet, ni "
                     "aucune donnée commerciale (chiffre d'affaires, marge, "
                     "valeur du foncier) ne sont repris ici : seuls la "
                     "structure des missions et les taux d'honoraires le sont.",
}

AVERTISSEMENT = (
    "Les honoraires se calculent sur le montant des TRAVAUX, pas sur "
    "l'enveloppe : la ligne de maîtrise d'œuvre et la provision pour aléas en "
    "sont retirées. Le barème distingue le clos-couvert du lot technique, dont "
    "les taux diffèrent d'un facteur huit sur certaines missions.")


# ═══════════════════════════════════════════════════════════════════════════
# 1. LES PHASES — ce que chacune produit, et ce que son absence coûte
# ═══════════════════════════════════════════════════════════════════════════
# Le champ `sans` est la raison d'être de ce module. Un tableau qui montrerait
# seulement l'économie réalisée en décochant une phase conseillerait de les
# décocher toutes.
PHASES = [
    {"cle": "aps", "nom": "APS / PC",
     "titre": "Avant-projet sommaire et permis de construire",
     "produit": "Le parti architectural et technique, les surfaces, "
                "l'implantation, et le dossier de permis de construire — avec "
                "le volet ICPE pour un centre de données.",
     "sans": "Aucune autorisation d'urbanisme ne peut être déposée. C'est la "
             "phase qui commande le calendrier : un permis purgé de recours "
             "arrive rarement avant douze mois."},
    {"cle": "apd", "nom": "APD",
     "titre": "Avant-projet définitif",
     "produit": "Les choix techniques arrêtés, les puissances, les surfaces "
                "définitives et l'estimation détaillée par lot.",
     "sans": "Le chiffrage reste au stade de l'ordre de grandeur, et les "
             "options structurantes — redondance, mode de refroidissement — "
             "n'ont pas été tranchées par écrit."},
    {"cle": "pro", "nom": "PRO / DCE",
     "titre": "Projet et dossier de consultation des entreprises",
     "produit": "Les pièces sur lesquelles les entreprises remettent prix : "
                "descriptifs, plans d'exécution de principe, DPGF.",
     "sans": "Vous consultez sur des documents incomplets. Les entreprises "
             "chiffrent alors le risque à votre place, et les écarts entre "
             "offres cessent d'être comparables."},
    {"cle": "act", "nom": "ACT",
     "titre": "Assistance aux contrats de travaux",
     "produit": "L'analyse des offres, la mise au point des marchés et la "
                "vérification de ce que chaque entreprise a réellement inclus.",
     "sans": "Les offres se comparent sur le seul prix affiché, sans que "
             "personne vérifie ce qu'elles omettent — et l'omission se "
             "retrouve en travaux supplémentaires."},
    {"cle": "exe", "nom": "EXE / DET / AOR",
     "titre": "Exécution, direction des travaux et réception",
     "produit": "Le suivi du chantier, la validation des situations, les "
                "essais, la levée des réserves et le dossier des ouvrages "
                "exécutés.",
     "sans": "Personne ne représente le maître d'ouvrage sur le chantier. "
             "C'est la phase la plus lourde du barème, et celle dont "
             "l'absence se paie le plus longtemps : un dossier d'ouvrages "
             "exécutés incomplet gêne l'exploitation pendant toute la vie du "
             "bâtiment."},
]

ORDRE_PHASES = [p["cle"] for p in PHASES]


# ═══════════════════════════════════════════════════════════════════════════
# 2. LES MISSIONS — deux barèmes, parce que deux assiettes
# ═══════════════════════════════════════════════════════════════════════════
# `taux_sc`  : part du montant du CLOS-COUVERT (gros œuvre, VRD, bâtiment)
# `taux_mep` : part du montant du LOT TECHNIQUE (électricité, froid, salles)
# `repartition` : comment le montant se répartit sur les phases ; somme = 1.
MISSIONS = [
    {"cle": "architecte", "nom": "Architecte — mission de conception",
     "taux_sc": 0.040, "taux_mep": 0.005,
     "repartition": {"aps": 0.200, "apd": 0.150, "pro": 0.150,
                     "act": 0.125, "exe": 0.375},
     "role": "Le parti d'ensemble, l'insertion, les autorisations. Sur un "
             "centre de données, son poids est dans le clos-couvert : la salle "
             "informatique se conçoit par les fluides, pas par la façade."},
    {"cle": "moex", "nom": "MOEX — maîtrise d'œuvre d'exécution",
     "taux_sc": 0.020, "taux_mep": 0.005,
     "repartition": {"aps": 0, "apd": 0, "pro": 0, "act": 0, "exe": 1.0},
     "role": "La conduite du chantier au nom du maître d'ouvrage. Entièrement "
             "en phase travaux — la décocher revient à ne pas être représenté "
             "sur le chantier."},
    {"cle": "opc", "nom": "OPC — ordonnancement, pilotage, coordination",
     "taux_sc": 0.020, "taux_mep": 0.010,
     "repartition": {"aps": 0, "apd": 0, "pro": 0, "act": 0, "exe": 1.0},
     "role": "Le calendrier et l'articulation des entreprises. Son poids "
             "DOUBLE sur le lot technique, où se croisent le plus de corps "
             "d'état sur le même mètre carré."},
    {"cle": "coord_etudes", "nom": "Coordination des études",
     "taux_sc": 0.004, "taux_mep": 0.004,
     "repartition": {"aps": 0.30, "apd": 0.20, "pro": 0.30, "act": 0.20,
                     "exe": 0},
     "role": "La cohérence entre les bureaux d'études. Elle s'arrête à la "
             "signature des marchés : c'est une mission d'études, pas de "
             "chantier."},
    {"cle": "bet_structure", "nom": "BET Structure",
     "taux_sc": 0.010, "taux_mep": 0.001,
     "repartition": {"aps": 0.10, "apd": 0.15, "pro": 0.20, "act": 0.10,
                     "exe": 0.45},
     "role": "Descentes de charges, planchers techniques, reprises. Le poids "
             "des groupes froid et des onduleurs se traite ici."},
    {"cle": "bet_fluides", "nom": "BET Fluides",
     "taux_sc": 0.005, "taux_mep": 0.020,
     "repartition": {"aps": 0.10, "apd": 0.15, "pro": 0.20, "act": 0.10,
                     "exe": 0.45},
     "role": "LE bureau d'études d'un centre de données. Son taux est "
             "QUADRUPLE sur le lot technique : c'est là que se décident le "
             "PUE, le mode de refroidissement et la consommation d'eau."},
    {"cle": "bet_environnement", "nom": "BET Environnement — ICPE",
     "taux_sc": 0.002, "taux_mep": 0.0,
     "repartition": {"aps": 1.0, "apd": 0, "pro": 0, "act": 0, "exe": 0},
     "role": "Le dossier d'installation classée, entièrement en amont. Un "
             "centre de données relève de rubriques ICPE au titre de ses "
             "groupes électrogènes et de ses fluides frigorigènes — à vérifier "
             "au cas par cas.",
     "reserve": "Le classement dépend des puissances et des fluides retenus : "
                "ce module ne le qualifie pas."},
    {"cle": "bet_acoustique", "nom": "BET Acoustique",
     "taux_sc": 0.001, "taux_mep": 0.0005,
     "repartition": {"aps": 0.10, "apd": 0.15, "pro": 0.20, "act": 0.10,
                     "exe": 0.45},
     "role": "Groupes froid, groupes électrogènes et tours : le bruit est le "
             "premier motif de contentieux de voisinage d'un centre de "
             "données, et il se traite en conception."},
    {"cle": "bet_divers", "nom": "BET Divers",
     "taux_sc": 0.005, "taux_mep": 0.005,
     "repartition": {"aps": 0.10, "apd": 0.15, "pro": 0.20, "act": 0.10,
                     "exe": 0.45},
     "role": "Les études spécialisées qu'on ne sait pas nommer au début et "
             "qu'on finit toujours par commander."},
    {"cle": "commissioning", "nom": "Commissioning Manager",
     "taux_sc": 0.001, "taux_mep": 0.010,
     "repartition": {"aps": 0, "apd": 0.10, "pro": 0.10, "act": 0, "exe": 0.80},
     "role": "La preuve que l'installation fait ce qu'elle promet — essais "
             "intégrés, montée en charge, bascules. Son taux est DIX FOIS plus "
             "élevé sur le lot technique, et c'est la mission qui distingue un "
             "centre de données d'un entrepôt : sans elle, la disponibilité "
             "annoncée n'est jamais démontrée."},
    {"cle": "bet_vrd", "nom": "BET VRD",
     "taux_sc": 0.050, "taux_mep": 0.0,
     "repartition": {"aps": 0.10, "apd": 0.15, "pro": 0.20, "act": 0.10,
                     "exe": 0.45},
     "role": "Voiries et réseaux. Le taux paraît élevé parce que son assiette "
             "est étroite : il ne porte que sur les VRD, pas sur le bâtiment.",
     "assiette_etroite": True},
    {"cle": "controle_technique", "nom": "Contrôle technique",
     "taux_sc": 0.004, "taux_mep": 0.004,
     "repartition": {"aps": 0.10, "apd": 0.15, "pro": 0.20, "act": 0.10,
                     "exe": 0.45},
     "role": "Avis sur la solidité et la sécurité des personnes.",
     "obligation": {
         "texte": "Obligatoire pour certaines catégories d'ouvrages — dont les "
                  "bâtiments à risque particulier. À vérifier sur votre projet, "
                  "mais l'hypothèse par défaut est qu'il s'applique.",
         "reference": "Code de la construction et de l'habitation, art. L125-1 "
                      "et suivants"}},
    {"cle": "sps", "nom": "Coordonnateur SPS",
     "taux_sc": 0.003, "taux_mep": 0.003,
     "repartition": {"aps": 0, "apd": 0.05, "pro": 0.05, "act": 0.05,
                     "exe": 0.85},
     "role": "Sécurité et protection de la santé des travailleurs sur le "
             "chantier.",
     "obligation": {
         "texte": "Obligatoire dès que plusieurs entreprises interviennent sur "
                  "le même chantier — ce qui est le cas de tout centre de "
                  "données. Ce n'est pas une option d'économie.",
         "reference": "Code du travail, art. L4532-2"}},
]

ORDRE_MISSIONS = [m["cle"] for m in MISSIONS]
OBLIGATOIRES = [m["cle"] for m in MISSIONS if m.get("obligation")]


# ═══════════════════════════════════════════════════════════════════════════
# 3. DE L'ENVELOPPE À L'ASSIETTE
# ═══════════════════════════════════════════════════════════════════════════
# Rattachement des lots de la DPGF aux deux assiettes du barème. Les lots
# exclus le sont pour une raison écrite : c'est ce qui empêche d'en ajouter un
# par distraction.
LOTS_CLOS_COUVERT = ["01", "02"]
LOTS_TECHNIQUE = ["03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
LOTS_EXCLUS = {
    "00": "c'est la maîtrise d'œuvre elle-même — on ne calcule pas des "
          "honoraires sur des honoraires",
    "13": "provision pour aléas : ce n'est pas un ouvrage, et l'inclure "
          "ferait payer des honoraires sur un risque qui ne se réalisera "
          "peut-être pas",
}
# Part des VRD DANS le clos-couvert, pour l'assiette étroite du BET VRD.
# Relevée sur le projet de référence : 2,09 M€ de VRD pour 50,4 M€ de travaux
# de clos-couvert et de bureaux.
PART_VRD_DANS_CLOS = 0.041


def _f(x, n=3):
    return round(float(x), n)


def assiettes(parts_lots, enveloppe_meur):
    """Répartit l'enveloppe entre les deux assiettes du barème.

    `parts_lots` : {code de lot: part de l'enveloppe}, tel que le module
    d'enveloppe le produit. On rend des MONTANTS, pas des parts : c'est sur des
    montants que le barème s'applique, et convertir tôt évite de se tromper
    d'assiette plus loin.
    """
    bas, haut = float(min(enveloppe_meur)), float(max(enveloppe_meur))
    p_clos = sum(parts_lots.get(c, 0.0) for c in LOTS_CLOS_COUVERT)
    p_tech = sum(parts_lots.get(c, 0.0) for c in LOTS_TECHNIQUE)
    p_hors = sum(parts_lots.get(c, 0.0) for c in LOTS_EXCLUS)
    return {
        "clos_couvert_meur": [_f(bas * p_clos), _f(haut * p_clos)],
        "technique_meur": [_f(bas * p_tech), _f(haut * p_tech)],
        "vrd_meur": [_f(bas * p_clos * PART_VRD_DANS_CLOS),
                     _f(haut * p_clos * PART_VRD_DANS_CLOS)],
        "part_clos": _f(p_clos), "part_technique": _f(p_tech),
        # DEUX PARTS QUI NE SE VALENT PAS, ET LES CONFONDRE COÛTE CHER.
        # `part_technique` est rapportée à l'ENVELOPPE ; celle-ci est rapportée
        # aux TRAVAUX, c'est-à-dire à l'assiette réelle du barème. Sur une
        # enveloppe dont 13 % sortent de l'assiette, l'écart entre les deux
        # dépasse dix points — et comme les taux du clos-couvert et du lot
        # technique diffèrent d'un facteur huit sur certaines missions, prendre
        # l'une pour l'autre déplace les honoraires de plusieurs millions.
        # C'est la part À TRANSMETTRE à un module qui ne reçoit qu'un montant
        # de travaux, sans la décomposition par lot.
        "part_technique_travaux": (_f(p_tech / (p_tech + p_clos))
                                   if (p_tech + p_clos) > 0 else None),
        "part_hors_assiette": _f(p_hors),
        "hors_assiette": [{"lot": c, "pourquoi": r} for c, r in
                          sorted(LOTS_EXCLUS.items())],
        "note": ("L'assiette exclut %.1f %% de l'enveloppe : la maîtrise "
                 "d'œuvre elle-même et la provision pour aléas."
                 % (p_hors * 100)),
    }


def honoraires(parts_lots, enveloppe_meur, phases=None, missions=None,
               taux_perso=None):
    """Les honoraires, mission par mission et phase par phase.

    `phases`   : les phases confiées (défaut : toutes).
    `missions` : les missions confiées (défaut : toutes).
    `taux_perso` : {cle: {"sc": x, "mep": y}} — vos offres priment sur le
                   relevé, exactement comme vos devis priment sur l'hypothèse
                   de coût au mégawatt.
    """
    A = assiettes(parts_lots, enveloppe_meur)
    # VIDE N'EST PAS ABSENT, et la nuance décide du résultat. `phases=None`
    # veut dire « pas de filtre, donc tout » ; `phases=[]` veut dire « le
    # client n'a rien coché ». Ma première version testait `not phases`, qui
    # confond les deux : une liste vide étant fausse en Python, décocher TOUTES
    # les phases facturait la mission COMPLÈTE. Le contrôle a trouvé exactement
    # cela.
    ph = (list(ORDRE_PHASES) if phases is None
          else [p for p in ORDRE_PHASES if p in phases])
    if not ph:
        return {"ok": False, "error": "aucune_phase",
                "message": "Aucune phase retenue : il n'y a rien à chiffrer. "
                           "Une mission de maîtrise d'œuvre sans phase n'est "
                           "pas une économie, c'est une absence de mission."}

    # Même nuance sur les missions : ne rien cocher n'est pas tout prendre.
    demandees = set(ORDRE_MISSIONS) if missions is None else set(missions)
    # LES OBLIGATOIRES SONT COMPTÉES MÊME DÉCOCHÉES. Les retirer du chiffrage
    # ferait afficher une économie qui n'existe pas : la dépense sera engagée.
    imposees = [c for c in OBLIGATOIRES if c not in demandees]
    retenues = demandees | set(OBLIGATOIRES)

    lignes, tot_bas, tot_haut = [], 0.0, 0.0
    par_phase = {p: [0.0, 0.0] for p in ORDRE_PHASES}
    for m in MISSIONS:
        if m["cle"] not in retenues:
            continue
        perso = (taux_perso or {}).get(m["cle"]) or {}
        t_sc = float(perso.get("sc", m["taux_sc"]))
        t_mep = float(perso.get("mep", m["taux_mep"]))
        base_sc = A["vrd_meur"] if m.get("assiette_etroite") else A["clos_couvert_meur"]
        base_mep = [0.0, 0.0] if m.get("assiette_etroite") else A["technique_meur"]

        # Part de la mission effectivement due, au vu des phases retenues.
        part = sum(m["repartition"].get(p, 0.0) for p in ph)
        plein_bas = base_sc[0] * t_sc + base_mep[0] * t_mep
        plein_haut = base_sc[1] * t_sc + base_mep[1] * t_mep
        bas, haut = plein_bas * part, plein_haut * part

        detail = {}
        for p in ORDRE_PHASES:
            r = m["repartition"].get(p, 0.0)
            v = [_f(plein_bas * r), _f(plein_haut * r)]
            detail[p] = {"montant_meur": v, "part": _f(r),
                         "retenue": p in ph}
            if p in ph:
                par_phase[p][0] += plein_bas * r
                par_phase[p][1] += plein_haut * r

        lignes.append({
            "cle": m["cle"], "nom": m["nom"], "role": m["role"],
            "taux_sc": t_sc, "taux_mep": t_mep,
            "taux_saisi": bool(perso),
            "assiette": "VRD seuls" if m.get("assiette_etroite")
                        else "clos-couvert + technique",
            "part_retenue": _f(part),
            "montant_meur": [_f(bas), _f(haut)],
            "montant_toutes_phases_meur": [_f(plein_bas), _f(plein_haut)],
            "phases": detail,
            "obligation": m.get("obligation"),
            "impose": m["cle"] in imposees,
            "reserve": m.get("reserve"),
        })
        tot_bas += bas
        tot_haut += haut

    travaux_bas = A["clos_couvert_meur"][0] + A["technique_meur"][0]
    travaux_haut = A["clos_couvert_meur"][1] + A["technique_meur"][1]
    return {
        "ok": True,
        "assiettes": A,
        "phases_retenues": ph,
        "phases_ecartees": [p for p in ORDRE_PHASES if p not in ph],
        "missions": lignes,
        "imposees": [{"cle": c,
                      "nom": next(m["nom"] for m in MISSIONS if m["cle"] == c),
                      "obligation": next(m["obligation"] for m in MISSIONS
                                         if m["cle"] == c)}
                     for c in imposees],
        "par_phase": {p: [_f(par_phase[p][0]), _f(par_phase[p][1])]
                      for p in ORDRE_PHASES},
        "total_meur": [_f(tot_bas), _f(tot_haut)],
        "travaux_meur": [_f(travaux_bas), _f(travaux_haut)],
        "taux_effectif_pct": [
            _f(tot_bas / travaux_bas * 100, 2) if travaux_bas else None,
            _f(tot_haut / travaux_haut * 100, 2) if travaux_haut else None],
        "avertissement": AVERTISSEMENT,
        "source": SOURCE,
        "nature": "calcule",
    }


def consequences(phases):
    """Ce qu'on perd en écartant des phases — le pendant de l'économie.

    C'EST LA MOITIÉ QUI MANQUE À TOUT CALCULATEUR D'HONORAIRES. Afficher
    seulement la baisse du montant conseille de tout décocher. Une phase
    écartée produit un livrable qui n'existera pas et laisse un risque au
    maître d'ouvrage : les deux se lisent ensemble, ou ni l'un ni l'autre."""
    ph = set(phases or ORDRE_PHASES)
    return [{"cle": p["cle"], "nom": p["nom"], "titre": p["titre"],
             "produit": p["produit"], "sans": p["sans"]}
            for p in PHASES if p["cle"] not in ph]


# ═══════════════════════════════════════════════════════════════════════════
# 5. LE MÊME BARÈME, DANS LE VOCABULAIRE DE LA LOI MOP
# ═══════════════════════════════════════════════════════════════════════════
# La page d'ingénierie de conseilprevcyber ne parle pas des cinq groupes du
# barème : elle parle des NEUF éléments de mission de la loi MOP, qu'un maître
# d'ouvrage français reconnaît. Il faut donc traduire — et dire honnêtement ce
# que la traduction ne peut pas faire.
#
# LE BARÈME GROUPE CE QUE LA LOI SÉPARE, et je n'invente pas la sous-répartition.
# « APS-PC » couvre l'esquisse ET l'avant-projet sommaire ; « PRO-DCE » couvre le
# projet ET le dossier de consultation ; « EXE » couvre le visa, la direction de
# l'exécution ET la réception. Le relevé ne dit pas comment le montant se divise
# À L'INTÉRIEUR d'un groupe. Proposer de ne prendre que l'esquisse reviendrait
# donc à fabriquer un chiffre : le module refuse, et le dit.
PHASES_MOP = {
    "aps": {"mop": ["ESQ", "APS"],
            "note": "Le relevé groupe l'esquisse et l'avant-projet sommaire "
                    "avec le permis. Il ne dit pas comment le montant se "
                    "partage entre les deux : on ne peut pas n'en prendre "
                    "qu'une."},
    "apd": {"mop": ["APD"], "note": ""},
    "pro": {"mop": ["PRO", "DCE"],
            "note": "Projet et dossier de consultation sont groupés dans le "
                    "relevé — le DCE est la mise en forme du projet, et les "
                    "séparer demanderait une hypothèse que la source ne porte "
                    "pas."},
    "act": {"mop": ["ACT"], "note": ""},
    "exe": {"mop": ["EXE-VISA", "DET", "AOR"],
            "note": "Visa, direction de l'exécution et réception sont groupés. "
                    "C'est le poste le plus lourd du barème : le détacher "
                    "élément par élément demanderait un second relevé."},
}

# CE BARÈME NE CHIFFRE QUE DE LA MAÎTRISE D'ŒUVRE. L'appliquer à une assistance
# à maîtrise d'ouvrage, à un audit ou à l'ingénierie interne d'un contractant
# EPC donnerait un nombre parfaitement faux et parfaitement crédible — c'est la
# pire des deux combinaisons. Le module refuse plutôt que de rendre ce nombre.
PORTEE_MISSION = {
    "moe": {"phases": ORDRE_PHASES, "couvre": True,
            "dit": "Conception et suivi de réalisation : le barème couvre la "
                   "mission entière."},
    "moe_conception": {"phases": ["aps", "apd", "pro"], "couvre": True,
                       "dit": "La mission s'arrête à la consultation : "
                              "l'assistance aux contrats et le suivi de "
                              "chantier ne sont pas confiés, et le barème ne "
                              "les compte pas."},
    "amo": {"phases": [], "couvre": False,
            "dit": "L'assistance à maîtrise d'ouvrage ne conçoit pas : elle ne "
                   "se rémunère pas au pourcentage des travaux, mais au temps "
                   "passé ou au forfait. Ce barème ne s'y applique pas."},
    "bet": {"phases": [], "couvre": False,
            "dit": "Un bureau d'études dans la maîtrise d'œuvre d'un tiers est "
                   "rémunéré par ce tiers, sur SA discipline seule : le barème "
                   "d'une maîtrise d'œuvre complète ne le représente pas."},
    "epc": {"phases": [], "couvre": False,
            "dit": "Dans un contrat EPC, l'ingénierie est incluse dans le prix "
                   "du contractant : il n'y a pas d'honoraires séparés à "
                   "chiffrer, et en afficher créerait une ligne qui n'existe "
                   "pas au contrat."},
    "audit": {"phases": [], "couvre": False,
              "dit": "Un audit constate, il ne conçoit pas : sa rémunération "
                     "est un forfait sur un périmètre défini, sans rapport "
                     "avec le montant des travaux examinés."},
}

# Part du lot technique dans les travaux, à défaut de DPGF. Relevée sur le
# projet de référence : le lot technique y faisait 70 % des travaux. C'est une
# HYPOTHÈSE, affichée comme telle et modifiable — sur un centre de données, ce
# partage commande le résultat plus que n'importe quel taux.
PART_TECHNIQUE_DEFAUT = 0.70


def assiette_directe(travaux_meur, part_technique=None):
    """L'assiette quand il n'y a pas de DPGF, seulement un montant de travaux.

    POURQUOI CETTE PORTE D'ENTRÉE EXISTE. La page d'ingénierie de
    conseilprevcyber ne calcule PAS l'enveloppe d'investissement — elle le dit
    en toutes lettres et renvoie vers conseilprev pour cela. Elle dispose donc
    d'un montant de travaux, pas d'une décomposition par lot. Reconstituer une
    DPGF à partir d'un total serait inventer ; on demande le partage, et on
    affiche l'hypothèse retenue à défaut."""
    bas, haut = float(min(travaux_meur)), float(max(travaux_meur))
    pt = PART_TECHNIQUE_DEFAUT if part_technique is None else float(part_technique)
    pt = max(0.0, min(1.0, pt))
    pc = 1.0 - pt
    return {
        "clos_couvert_meur": [_f(bas * pc), _f(haut * pc)],
        "technique_meur": [_f(bas * pt), _f(haut * pt)],
        "vrd_meur": [_f(bas * pc * PART_VRD_DANS_CLOS),
                     _f(haut * pc * PART_VRD_DANS_CLOS)],
        "part_clos": _f(pc), "part_technique": _f(pt),
        "part_hors_assiette": 0.0, "hors_assiette": [],
        "part_saisie": part_technique is not None,
        "note": ("Partage clos-couvert / technique : %.0f %% de technique%s. "
                 "Sur un centre de données, ce partage pèse plus lourd que "
                 "n'importe quel taux du barème."
                 % (pt * 100,
                    "" if part_technique is not None
                    else " — hypothèse relevée sur le projet de référence, à "
                         "remplacer par votre décomposition")),
    }


def honoraires_directs(travaux_meur, part_technique=None, phases=None,
                       missions=None, taux_perso=None):
    """Comme `honoraires`, mais sur un montant de travaux au lieu d'une DPGF."""
    A = assiette_directe(travaux_meur, part_technique)
    # On rejoue le calcul principal en lui présentant l'assiette déjà faite :
    # une seconde implémentation du barème divergerait de la première.
    faux_lots = {}
    total = A["clos_couvert_meur"][1] + A["technique_meur"][1]
    if total > 0:
        for c in LOTS_CLOS_COUVERT[:1]:
            faux_lots[c] = A["clos_couvert_meur"][1] / total
        for c in LOTS_TECHNIQUE[:1]:
            faux_lots[c] = A["technique_meur"][1] / total
    r = honoraires(faux_lots, [A["clos_couvert_meur"][0] + A["technique_meur"][0],
                               total],
                   phases=phases, missions=missions, taux_perso=taux_perso)
    if r.get("ok"):
        r["assiettes"] = A          # l'assiette réelle, pas la reconstituée
    return r


def portee(mission):
    """Ce barème s'applique-t-il à cette mission — et sinon, pourquoi."""
    p = PORTEE_MISSION.get(mission or "moe")
    if not p:
        return {"couvre": False, "phases": [],
                "dit": "Mission inconnue de ce barème."}
    return dict(p, mission=mission or "moe")


def referentiel():
    return {"version": VERSION, "phases": PHASES, "ordre_phases": ORDRE_PHASES,
            "phases_mop": PHASES_MOP, "portee_mission": PORTEE_MISSION,
            "part_technique_defaut": PART_TECHNIQUE_DEFAUT,
            "missions": MISSIONS, "ordre_missions": ORDRE_MISSIONS,
            "obligatoires": OBLIGATOIRES, "source": SOURCE,
            "avertissement": AVERTISSEMENT,
            "lots_clos_couvert": LOTS_CLOS_COUVERT,
            "lots_technique": LOTS_TECHNIQUE,
            "lots_exclus": [{"lot": c, "pourquoi": r}
                            for c, r in sorted(LOTS_EXCLUS.items())]}


def sante():
    return {"module": "moe_dc", "version": VERSION,
            "missions": len(MISSIONS), "phases": len(PHASES),
            "obligatoires": len(OBLIGATOIRES),
            "portee": "Barème relevé sur UN projet, pas une statistique de "
                      "marché. Ne qualifie ni le classement ICPE ni "
                      "l'assujettissement au contrôle technique."}


def _verifier():
    """Refuse de charger si le barème ne se tient pas."""
    if len(MISSIONS) != 13:
        raise RuntimeError("moe_dc : le barème relevé porte treize missions")
    for m in MISSIONS:
        s = sum(m["repartition"].get(p, 0.0) for p in ORDRE_PHASES)
        if abs(s - 1.0) > 1e-6:
            raise RuntimeError(
                "moe_dc : la répartition de %s somme à %.4f et non à 1 — une "
                "mission dont les phases ne totalisent pas 100 %% se facture "
                "en partie nulle part" % (m["cle"], s))
        if set(m["repartition"]) - set(ORDRE_PHASES):
            raise RuntimeError("moe_dc : phase inconnue dans %s" % m["cle"])
        for champ in ("nom", "role"):
            if not str(m.get(champ, "")).strip():
                raise RuntimeError("moe_dc : %s sans %s" % (m["cle"], champ))
        if m["taux_sc"] < 0 or m["taux_mep"] < 0:
            raise RuntimeError("moe_dc : taux négatif sur %s" % m["cle"])
    for p in PHASES:
        for champ in ("nom", "titre", "produit", "sans"):
            if not str(p.get(champ, "")).strip():
                raise RuntimeError("moe_dc : phase %s sans %s"
                                   % (p["cle"], champ))
        if len(p["sans"]) < 60:
            raise RuntimeError(
                "moe_dc : la conséquence d'écarter %s est trop courte pour "
                "peser dans la décision — c'est elle qui empêche de tout "
                "décocher" % p["cle"])
    if not OBLIGATOIRES:
        raise RuntimeError(
            "moe_dc : aucune mission obligatoire — le module présenterait le "
            "coordonnateur SPS comme une option d'économie")
    for c in OBLIGATOIRES:
        m = next(x for x in MISSIONS if x["cle"] == c)
        if not m["obligation"].get("reference"):
            raise RuntimeError(
                "moe_dc : %s déclarée obligatoire sans référence de texte — "
                "une obligation sans source ne se vérifie pas" % c)
    if set(LOTS_CLOS_COUVERT) & set(LOTS_TECHNIQUE):
        raise RuntimeError("moe_dc : un lot dans les deux assiettes")
    if set(LOTS_EXCLUS) & (set(LOTS_CLOS_COUVERT) | set(LOTS_TECHNIQUE)):
        raise RuntimeError("moe_dc : un lot à la fois exclu et compté")


_verifier()
