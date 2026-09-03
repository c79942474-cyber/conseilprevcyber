# -*- coding: utf-8 -*-
"""Client Impact — deux centres de données, le même service, deux empreintes.

CE QUE CETTE ÉTUDE DE CAS ÉTABLIT, ET COMMENT.

Deux centres de données qui rendent EXACTEMENT le même service peuvent afficher
des empreintes très différentes. La phrase est facile à écrire et elle ne vaut
rien tant qu'un chiffre ne la porte pas : ce module produit ce chiffre, et il ne
l'écrit nulle part.

IL NE PORTE AUCUNE VALEUR D'EMPREINTE. Le PUE, le carbone, l'eau et l'incorporé
sont calculés par le moteur de `datacenter.py`, celui-là même que sert la page
/datacenter, avec sa formule, sa source normative et son incertitude. Recopier
ici un résultat le figerait : le jour où l'intensité d'un réseau est mise à
jour, la démonstration continuerait d'afficher l'ancien écart, et personne ne le
verrait — c'est exactement le défaut que ce dépôt traque partout ailleurs.

« LE MÊME SERVICE » EST UNE CONTRAINTE, PAS UNE FORMULE DE STYLE. Si les deux
configurations ne rendaient pas le même service, l'écart d'empreinte ne
prouverait rien : un site deux fois plus petit émet deux fois moins, et ce n'est
pas une performance. Les grandeurs qui DÉFINISSENT le service sont donc listées
en `INVARIANTS`, et une configuration qui en modifierait une seule fait tomber le
module au chargement. C'est la seule façon d'être sûr que ce qui est comparé est
comparable.

CE QUE LA DÉMONSTRATION N'EST PAS. Ce n'est pas une mission conduite : aucun
client, aucune mesure de terrain. Ce sont trois configurations types passées
dans un moteur public. Le dire est une condition pour que le reste soit cru.
"""
import datacenter

VERSION = "2026-09-a"

NOM = "Client Impact"
SOUS_TITRE = ("Deux centres de données, le même service rendu, "
              "deux empreintes qui n'ont rien à voir")


# ═══════════════════════════════════════════════════════════════════════════
#  1. LE SERVICE — ce qui doit rester identique pour que l'écart veuille dire
#     quelque chose
# ═══════════════════════════════════════════════════════════════════════════
# CHAQUE INVARIANT DIT POURQUOI IL EN EST UN. Un invariant sans justification
# est une constante qu'on déplacera le jour où elle gêne.

INVARIANTS = [
    {"cle": "puissance_it_kw", "valeur": 1200,
     "nom": "Puissance informatique installée", "unite": "kW",
     "pourquoi": "C'est la définition physique du service rendu : la capacité "
                 "de calcul mise à disposition. Comparer deux sites de "
                 "puissances différentes reviendrait à féliciter le plus petit."},
    {"cle": "taux_charge", "valeur": 0.65,
     "nom": "Taux de charge moyen", "unite": "part",
     "pourquoi": "Un site rempli à 30 % consomme moins en absolu et davantage "
                 "par unité de service. Le figer interdit de gagner l'écart "
                 "sur un remplissage différent."},
    {"cle": "heures_an", "valeur": 8760,
     "nom": "Heures de fonctionnement", "unite": "h/an",
     "pourquoi": "Les deux sites tournent en continu. Un service disponible "
                 "moins longtemps n'est pas le même service."},
    {"cle": "nb_serveurs", "valeur": 3000,
     "nom": "Parc de serveurs", "unite": "serveurs",
     "pourquoi": "Il commande le carbone INCORPORÉ, qui ne dépend ni du pays "
                 "ni du refroidissement. Le figer est ce qui rend visible le "
                 "fait qu'une partie de l'empreinte ne se déplace pas."},
]

SERVICE = {i["cle"]: i["valeur"] for i in INVARIANTS}


# ═══════════════════════════════════════════════════════════════════════════
#  2. LES TROIS CONFIGURATIONS — elles ne diffèrent QUE par leurs leviers
# ═══════════════════════════════════════════════════════════════════════════
# POURQUOI TROIS ET PAS DEUX. Les deux premières opposent deux réalités
# physiques. La troisième est la même que la première, à un contrat près : elle
# achète des garanties d'origine. Elle existe parce que l'écart le plus
# spectaculaire de ce dossier n'est PAS physique — c'est un écart de périmètre
# comptable, entre deux chiffres également exacts.

CONFIGURATIONS = [
    {
        "cle": "a",
        "nom": "Site A — implantation historique",
        "resume": "Salle en région à réseau électrique carboné, groupe froid à "
                  "eau glacée, tours évaporatives, chaleur rejetée.",
        "leviers": {
            "pays": "PL",
            "refroidissement": "eau_glacee",
            "part_evaporative": 0.7,
            "cycles_concentration": 3,
            "part_chaleur_reutilisee": 0.0,
        },
        "pourquoi": "Le cas courant d'un site choisi pour sa proximité, son "
                    "foncier ou son histoire — jamais pour son réseau.",
    },
    {
        "cle": "b",
        "nom": "Site B — implantation arbitrée",
        "resume": "Réseau électrique peu carboné, free cooling direct sur air "
                  "extérieur, aucune évaporation, chaleur cédée à un réseau "
                  "urbain.",
        "leviers": {
            "pays": "SE",
            "refroidissement": "free_cooling_air",
            "part_evaporative": 0.0,
            "cycles_concentration": 6,
            "part_chaleur_reutilisee": 0.6,
            "temperature_rejet_c": 45,
        },
        "pourquoi": "Le même service, avec trois décisions prises au moment où "
                    "elles coûtent le moins cher : le lieu, la famille de "
                    "refroidissement, le débouché de la chaleur.",
    },
    {
        "cle": "a_certificats",
        "nom": "Site A — avec garanties d'origine",
        "resume": "Le site A, inchangé, qui achète des garanties d'origine "
                  "couvrant la totalité de sa consommation.",
        "leviers": {
            "pays": "PL",
            "refroidissement": "eau_glacee",
            "part_evaporative": 0.7,
            "cycles_concentration": 3,
            "part_chaleur_reutilisee": 0.0,
            "part_renouvelable": 1.0,
        },
        "pourquoi": "Rigoureusement le même site que A : mêmes machines, même "
                    "réseau, mêmes électrons. Seul le contrat change — et le "
                    "chiffre publiable avec.",
        "physiquement_identique_a": "a",
    },
]


# ═══════════════════════════════════════════════════════════════════════════
#  3. CE QU'ON RETIENT DE CHAQUE ÉTUDE, ET OÙ LE MOTEUR LE RANGE
# ═══════════════════════════════════════════════════════════════════════════
# LE CHEMIN EST DONNÉ, PAS LE NOMBRE. Chaque indicateur dit dans quel bloc du
# résultat il se trouve ; sa valeur, son unité, sa formule, sa source et son
# incertitude sont celles que le moteur rend. Aucune n'est réécrite ici.

INDICATEURS = [
    {"cle": "pue", "chemin": ("energie", "pue"),
     "lecture": "Ce que le site consomme pour un kilowattheure informatique."},
    {"cle": "energie_totale_MWh", "chemin": ("energie", "energie_totale_MWh"),
     "lecture": "L'énergie appelée sur le réseau, service rendu identique."},
    {"cle": "co2_exploitation_localise_t",
     "chemin": ("carbone", "co2_exploitation_localise_t"),
     "lecture": "Les émissions réelles du réseau qui alimente le site."},
    {"cle": "co2_exploitation_marche_t",
     "chemin": ("carbone", "co2_exploitation_marche_t"),
     "lecture": "Le chiffre que les contrats d'électricité autorisent à "
                "publier."},
    {"cle": "empreinte_totale_t", "chemin": ("carbone", "empreinte_totale_t"),
     "lecture": "Exploitation ET matériel : la seule somme qui se compare."},
    {"cle": "part_incorpore_pct", "chemin": ("carbone", "part_incorpore_pct"),
     "lecture": "La part de l'empreinte qui ne dépend ni du réseau ni du "
                "refroidissement."},
    {"cle": "appoint_m3", "chemin": ("eau", "appoint_m3"),
     "lecture": "L'eau consommée SUR le site."},
    {"cle": "eau_amont_m3", "chemin": ("eau", "eau_amont_m3"),
     "lecture": "L'eau consommée pour produire l'électricité du site."},
    {"cle": "erf", "chemin": ("chaleur", "erf"),
     "lecture": "La part de l'énergie rendue à un usage extérieur."},
]


def _lire(etude, chemin):
    """Un indicateur du moteur, avec tout ce qui permet de le contester.

    ON NE GARDE PAS QUE LA VALEUR. Un nombre sans sa formule, sa source et son
    incertitude ne se discute pas : il se croit ou il se rejette, et les deux
    sont mauvais.
    """
    bloc = etude.get(chemin[0]) or {}
    t = bloc.get(chemin[1])
    if not isinstance(t, dict) or "valeur" not in t:
        return None
    return {"nom": t.get("nom"), "valeur": t.get("valeur"),
            "unite": t.get("unite"), "formule": t.get("formule"),
            "source": t.get("source"), "incertitude": t.get("incertitude"),
            "note": t.get("note")}


def _rapport(a, b):
    """a / b, ou None — un rapport à un dénominateur nul n'est pas « infini »,
    c'est une comparaison qui n'a pas de sens et qui doit se taire."""
    try:
        if b in (None, 0) or a is None:
            return None
        return float(a) / float(b)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def comparer():
    """Les trois configurations passées au moteur, et ce qui les sépare."""
    etudes = {}
    sorties = []
    for c in CONFIGURATIONS:
        profil = dict(SERVICE)
        profil.update(c["leviers"])
        e = datacenter.etude(profil)
        etudes[c["cle"]] = e
        sorties.append({
            "cle": c["cle"], "nom": c["nom"], "resume": c["resume"],
            "pourquoi": c["pourquoi"],
            "leviers": c["leviers"],
            "pays_nom": datacenter.nom_pays(c["leviers"].get("pays")),
            "refroidissement_nom": (
                datacenter.REFROIDISSEMENT.get(c["leviers"].get("refroidissement"))
                or {}).get("nom"),
            "indicateurs": {i["cle"]: _lire(e, i["chemin"])
                            for i in INDICATEURS},
        })

    a, b = etudes["a"], etudes["b"]
    return {
        "version": VERSION,
        "moteur": datacenter.VERSION,
        "nom": NOM,
        "sous_titre": SOUS_TITRE,
        "service": INVARIANTS,
        "configurations": sorties,
        "lectures": {i["cle"]: i["lecture"] for i in INDICATEURS},
        "ecarts": _ecarts(a, b, etudes["a_certificats"]),
        "decomposition": _decomposition(a, b),
        "enseignements": enseignements(a, b, etudes["a_certificats"]),
        "reserves": RESERVES,
        "nature": NATURE,
    }


def _v(etude, chemin):
    t = _lire(etude, chemin)
    return None if t is None else t["valeur"]


def _ecarts(a, b, a_cert):
    """Les rapports, indicateur par indicateur — A rapporté à B."""
    par_cle = {i["cle"]: i["chemin"] for i in INDICATEURS}
    out = {}
    for cle, chemin in par_cle.items():
        out[cle] = _rapport(_v(a, chemin), _v(b, chemin))
    # LE RAPPORT QUI COMPTE LE PLUS N'OPPOSE PAS DEUX SITES : il oppose deux
    # PÉRIMÈTRES sur le même site. C'est celui-là que les évaluateurs relèvent.
    out["meme_site_deux_chiffres"] = {
        "localise_t": _v(a_cert, ("carbone", "co2_exploitation_localise_t")),
        "marche_t": _v(a_cert, ("carbone", "co2_exploitation_marche_t")),
    }
    return out


def _intensite_employee(etude):
    """(g/kWh, vient_du_pays) — celle que le MOTEUR a employée, pas celle qu'on
    irait relire dans la table.

    LIRE LA TABLE À CÔTÉ EST UNE SECONDE SOURCE, et deux sources divergent. Le
    moteur accepte une intensité imposée en entrée (`intensite_reseau_g`) qui
    court-circuite le pays : la décomposition afficherait alors un facteur qui
    n'est pas celui qui a servi au calcul. On lit donc ce que le moteur déclare
    avoir employé, et on dit séparément si cela correspond bien au pays — parce
    que c'est le récit « c'est le choix du lieu » qui en dépend.
    """
    t = (etude.get("carbone") or {}).get("co2_exploitation_localise_t") or {}
    g = (t.get("entrees") or {}).get("intensité (g/kWh)")
    du_pays = datacenter.INTENSITE_RESEAU.get((etude.get("profil") or {}).get("pays"))
    if g is None:
        return du_pays, du_pays is not None
    return g, (du_pays is not None and abs(float(g) - float(du_pays)) < 1e-9)


def _decomposition(a, b):
    """D'où vient l'écart d'exploitation, et la vérification que ça tombe juste.

    L'IDENTITÉ EST VÉRIFIÉE, PAS AFFIRMÉE. Le rapport des émissions
    d'exploitation DOIT être le produit du rapport des PUE par le rapport des
    intensités de réseau — c'est ce que dit la chaîne de calcul. Si le moteur
    change et que l'identité cesse de tomber juste, la page doit l'apprendre ici
    plutôt que d'afficher une décomposition qui ne décompose plus rien.
    """
    r_pue = _rapport(_v(a, ("energie", "pue")), _v(b, ("energie", "pue")))
    ia, ta = _intensite_employee(a)
    ib, tb = _intensite_employee(b)
    r_reseau = _rapport(ia, ib)
    r_co2 = _rapport(_v(a, ("carbone", "co2_exploitation_localise_t")),
                     _v(b, ("carbone", "co2_exploitation_localise_t")))
    produit = None if (r_pue is None or r_reseau is None) else r_pue * r_reseau
    exacte = (produit is not None and r_co2 is not None
              and abs(produit - r_co2) <= 1e-6 * max(1.0, abs(r_co2)))
    return {
        # ET LE FACTEUR RÉSEAU DIT S'IL VIENT BIEN DU PAYS. Le moteur accepte
        # une intensité imposée en entrée, qui court-circuite le pays : le
        # récit « c'est le choix du lieu » serait alors faux, avec un chiffre
        # juste. On le vérifie plutôt que de le supposer.
        "intensite_du_pays": bool(ta and tb),
        "facteurs": [
            {"cle": "pue", "libelle": "Rapport des PUE",
             "valeur": r_pue,
             "pourquoi": "À service identique, tout l'écart d'énergie appelée "
                         "vient du rendement de l'infrastructure.",
             "source": "ISO/IEC 30134-2 ; EN 50600-4-2"},
            {"cle": "reseau", "libelle": "Rapport des intensités de réseau",
             "valeur": r_reseau,
             "pourquoi": "Le même kilowattheure n'émet pas la même chose selon "
                         "le réseau qui le produit.",
             "source": "Intensité employée par le moteur pour ce calcul — "
                       "table du cabinet, confrontée à la Base Carbone ADEME "
                       "(voir /datacenter)"},
        ],
        "produit": produit,
        "rapport_constate": r_co2,
        "identite_verifiee": exacte,
        "lecture": ("L'écart d'exploitation est le PRODUIT de deux décisions, "
                    "pas leur somme : un bon PUE sur un réseau carboné ne "
                    "rattrape pas le réseau, il le divise par 1,1."),
        "reserve_si_fausse": ("L'identité ne tombe plus juste : la "
                              "décomposition ne décrit plus la chaîne de "
                              "calcul et ne doit pas être affichée comme si "
                              "elle le faisait."),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  4. LES ENSEIGNEMENTS — chacun tenu par une valeur, aucune écrite ici
# ═══════════════════════════════════════════════════════════════════════════

def enseignements(a, b, a_cert):
    """Cinq constats, chacun accompagné du chiffre qui l'établit."""
    e = []
    e.append({
        "cle": "produit",
        "titre": "L'écart se multiplie, il ne s'additionne pas",
        "texte": "Le lieu et le refroidissement ne s'ajoutent pas : ils se "
                 "multiplient. C'est pourquoi un excellent PUE sur un réseau "
                 "carboné déçoit toujours — il agit sur le petit facteur.",
        "appui": {"rapport_exploitation": _rapport(
            _v(a, ("carbone", "co2_exploitation_localise_t")),
            _v(b, ("carbone", "co2_exploitation_localise_t")))},
    })
    e.append({
        "cle": "incorpore",
        "titre": "Une partie de l'empreinte ne se déplace pas",
        "texte": "Les serveurs sont les mêmes des deux côtés : leur carbone "
                 "incorporé est identique. Il ne bouge pas d'un site à "
                 "l'autre, et il devient donc majoritaire dès que "
                 "l'exploitation baisse. Le PUE ne le voit pas ; aucun "
                 "indicateur d'exploitation ne le voit.",
        "appui": {"part_incorpore_a_pct": _v(a, ("carbone", "part_incorpore_pct")),
                  "part_incorpore_b_pct": _v(b, ("carbone", "part_incorpore_pct")),
                  "rapport_empreinte_totale": _rapport(
                      _v(a, ("carbone", "empreinte_totale_t")),
                      _v(b, ("carbone", "empreinte_totale_t")))},
    })
    e.append({
        "cle": "eau",
        "titre": "Zéro eau sur le site ne veut pas dire zéro eau",
        "texte": "Le site sans évaporation ne consomme rien au compteur — et "
                 "sa production d'électricité, elle, consomme de l'eau. Un "
                 "WUE de site à zéro publié seul est une demi-vérité ; c'est "
                 "l'eau AMONT qui dit ce que le service coûte réellement.",
        "appui": {"appoint_b_m3": _v(b, ("eau", "appoint_m3")),
                  "eau_amont_b_m3": _v(b, ("eau", "eau_amont_m3")),
                  "appoint_a_m3": _v(a, ("eau", "appoint_m3"))},
    })
    e.append({
        "cle": "perimetre",
        "titre": "Le même site peut publier deux chiffres, tous deux exacts",
        "texte": "Site A avec des garanties d'origine publie une exploitation "
                 "à zéro, quand le réseau qui l'alimente n'a pas changé d'un "
                 "gramme. Les deux chiffres sont réguliers ; ils ne répondent "
                 "pas à la même question. Présenter le seul chiffre marché "
                 "comme l'empreinte du site est l'omission que relèvent les "
                 "évaluateurs.",
        # LE TOTAL AUSSI CHANGE, et c'est le chiffre qui part en appel
        # d'offres : le moteur construit l'empreinte complète sur le chiffre
        # MARCHÉ. Le même site, la même année, les mêmes machines — deux
        # empreintes publiables.
        "appui": {"localise_t": _v(a_cert, ("carbone", "co2_exploitation_localise_t")),
                  "marche_t": _v(a_cert, ("carbone", "co2_exploitation_marche_t")),
                  "total_sans_certificats_t": _v(a, ("carbone", "empreinte_totale_t")),
                  "total_avec_certificats_t": _v(a_cert, ("carbone", "empreinte_totale_t"))},
    })
    e.append({
        "cle": "chaleur",
        "titre": "L'énergie sortante est un actif, pas un déchet",
        "texte": "La chaleur rejetée à 45 °C alimente un réseau urbain : elle "
                 "sort du bilan du site et entre dans celui d'un autre. Le "
                 "débouché se décide au moment du choix du terrain — après, "
                 "il n'existe plus.",
        "appui": {"erf_b_pct": _v(b, ("chaleur", "erf")),
                  "erf_a_pct": _v(a, ("chaleur", "erf"))},
    })
    return e


NATURE = (
    "CE N'EST PAS UNE MISSION CONDUITE. Aucun client, aucune mesure de "
    "terrain, aucun site réel : trois configurations types passées dans le "
    "moteur public de ce site (/datacenter), qui rend pour chaque valeur sa "
    "formule, sa source normative et son incertitude. Ce que la démonstration "
    "établit, c'est l'ORDRE DE GRANDEUR de l'écart et D'OÙ il vient — pas "
    "l'empreinte de votre installation, qui se mesure.")

RESERVES = [
    "Les intensités de réseau sont des MOYENNES ANNUELLES. Elles ne "
    "conviennent pas pour arbitrer un pilotage horaire : un site qui décale "
    "ses calculs vers les heures creuses obtient un résultat que cette "
    "moyenne ne sait pas décrire.",
    "Le carbone incorporé repose sur des facteurs par serveur qui varient "
    "d'un facteur deux selon les constructeurs et les études. C'est la "
    "grandeur la moins fermement établie de la comparaison, et c'est "
    "précisément celle qui devient majoritaire sur le site le plus propre.",
    "Le PUE est calculé à partir de la famille de refroidissement et du taux "
    "de charge, non mesuré. Un PUE contractuel imposé par un cahier des "
    "charges prime toujours sur ce calcul.",
    "L'eau amont porte la réserve du moteur sur les mix hydrauliques : "
    "l'évaporation des retenues n'y est pas comptée, son attribution à "
    "l'électricité étant contestée.",
    "Le choix du lieu n'est pas toujours libre : souveraineté, latence, "
    "contraintes contractuelles ou foncières peuvent l'interdire. La "
    "démonstration dit ce que ce choix COÛTE, elle ne dit pas qu'il est "
    "toujours ouvert.",
]


# ═══════════════════════════════════════════════════════════════════════════
#  LES CONTRÔLES DE COHÉRENCE — au chargement, pas en production
# ═══════════════════════════════════════════════════════════════════════════

def _verifier():
    """Les fautes de structure, ou une liste vide."""
    fautes = []
    cles = [c["cle"] for c in CONFIGURATIONS]
    if len(set(cles)) != len(cles):
        fautes.append("configurations en double : %s" % cles)
    if len(CONFIGURATIONS) < 2:
        fautes.append("il faut au moins deux configurations pour comparer")

    # LE CŒUR DE LA DÉMONSTRATION : une configuration qui toucherait à un
    # invariant ne rendrait plus le même service, et l'écart d'empreinte ne
    # prouverait plus rien. Le module refuse de se charger dans ce cas.
    invariants = {i["cle"] for i in INVARIANTS}
    for c in CONFIGURATIONS:
        touches = invariants & set(c["leviers"])
        if touches:
            fautes.append(
                "configuration %s : elle modifie %s, qui définit le SERVICE — "
                "l'écart d'empreinte ne comparerait plus deux façons de rendre "
                "le même service" % (c["cle"], ", ".join(sorted(touches))))
        for champ in ("nom", "resume", "pourquoi"):
            if not (c.get(champ) or "").strip():
                fautes.append("configuration %s : champ « %s » vide"
                              % (c["cle"], champ))

    for i in INVARIANTS:
        if not (i.get("pourquoi") or "").strip():
            fautes.append("invariant %s : aucune justification" % i["cle"])

    # Un indicateur qui désigne un bloc que le moteur ne rend pas est une case
    # définitivement vide sur la page.
    temoin = datacenter.etude(dict(SERVICE, pays="FR",
                                   refroidissement="eau_glacee"))
    for i in INDICATEURS:
        if _lire(temoin, i["chemin"]) is None:
            fautes.append("indicateur %s : le moteur ne rend rien en %s"
                          % (i["cle"], " / ".join(i["chemin"])))
        if not (i.get("lecture") or "").strip():
            fautes.append("indicateur %s : aucune lecture" % i["cle"])

    # La configuration « physiquement identique » doit l'être vraiment : sinon
    # l'enseignement sur les deux périmètres comparerait deux sites différents
    # et perdrait tout son sens.
    par_cle = {c["cle"]: c for c in CONFIGURATIONS}
    for c in CONFIGURATIONS:
        ref = c.get("physiquement_identique_a")
        if not ref:
            continue
        base = par_cle.get(ref)
        if not base:
            fautes.append("%s se dit identique à %s, qui n'existe pas"
                          % (c["cle"], ref))
            continue
        physiques = {k: v for k, v in c["leviers"].items()
                     if k != "part_renouvelable"}
        if physiques != base["leviers"]:
            fautes.append(
                "%s se dit physiquement identique à %s et ne l'est pas : "
                "l'enseignement sur les deux périmètres comparerait deux sites"
                % (c["cle"], ref))
    return fautes


_FAUTES = _verifier()
if _FAUTES:
    raise RuntimeError("impact_client — table incohérente : "
                       + " ; ".join(_FAUTES))


def sante():
    """Ce que le module peut dire de lui-même, sans rien calculer de lourd."""
    return {"version": VERSION, "moteur": datacenter.VERSION,
            "configurations": len(CONFIGURATIONS),
            "invariants": len(INVARIANTS),
            "indicateurs": len(INDICATEURS),
            "fautes": _FAUTES}
