# -*- coding: utf-8 -*-
"""Ce que le profil décide AVANT que l'étude soit lancée.

L'étape 1 de la page /datacenter affirme deux choses : qu'une seule entrée est
indispensable, et que « renseigner davantage resserre les incertitudes ». La
seconde affirmation était jusqu'ici invérifiable — le lecteur devait la croire
sur parole. Ce module la CHIFFRE.

Le principe : pour chaque champ laissé vide, on rejoue l'étude complète en
balayant le domaine de ce champ, et on mesure l'écart obtenu sur les grandeurs
de tête. Cet écart n'est pas une incertitude statistique — c'est l'étendue des
résultats encore compatibles avec ce que l'utilisateur a dit. Renseigner le
champ la fait disparaître ; c'est exactement ce que la page promet.

Trois règles tenues ici :

  · AUCUNE formule n'est réécrite. Chaque point de chaque courbe vient d'un
    appel à datacenter.etude(). Un module d'analyse qui recopie le modèle qu'il
    analyse finit par en diverger, et c'est l'analyse qu'on croit.

  · AUCUN domaine n'est inventé. On ne balaie que ce que le référentiel énumère
    (les familles, les pays, les classes) ou ce que la définition borne (une
    part vaut entre 0 et 1). Les deux seuls balayages qui reposent sur un choix
    — le taux de charge et les cycles de concentration — portent la nature
    « hypothese » et affichent leurs bornes.

  · Les champs sans domaine borné ne sont pas balayés du tout. La puissance
    informatique, le nombre de serveurs et le prix de l'électricité n'ont pas
    de plage défendable : leur inventer une reviendrait à fabriquer une
    sensibilité. Ils sont déclarés exclus, avec le motif.
"""

import datacenter as D

VERSION = "2026-08-a"

# ── Balayages déclarés ─────────────────────────────────────────────────────
# Ces deux bornes-là sont un CHOIX, pas une donnée du référentiel. Elles sont
# donc nommées, exportées et affichées : un balayage dont on ne voit pas les
# bornes ne se relit pas.
BALAYAGE_TAUX = (0.20, 1.00)
PAS_TAUX = 0.05
BALAYAGE_COC = (2.0, 8.0)

BALAYAGE_NOTE = (
    "Les bornes du taux de charge et des cycles de concentration sont un "
    "balayage déclaré, pas une plage mesurée : elles cadrent l'exploration, "
    "elles ne prétendent pas décrire votre installation."
)


def _suite(a, b, pas):
    """Grille en centièmes, pour que 0,60 tombe sur un point et pas à côté.

    Additionner 0,05 en flottant donne 0,6000000000000001 au huitième pas :
    le coude du modèle se retrouve alors entre deux points, et la détection le
    manque. On compte en entiers, on divise à la fin.
    """
    ia, ib, ip = int(round(a * 100)), int(round(b * 100)), int(round(pas * 100))
    return [i / 100.0 for i in range(ia, ib + 1, ip)]


# ── Les grandeurs qu'on suit ───────────────────────────────────────────────
# Quatre, et ce sont celles que la page met en avant. En suivre quinze donnerait
# un tableau que personne ne lit ; en suivre trois faisait afficher « 0 % » en
# face de la part de chaleur réutilisée, qui ne touche aucune des trois
# premières mais commande l'ERF — l'une des huit déclarations exigées par la
# directive efficacité énergétique. Un zéro sans cette quatrième colonne se lit
# « ce champ ne sert à rien », et c'est faux.
INDICATEURS = [
    {"cle": "pue", "section": "energie", "champ": "pue",
     "nom": "PUE", "unite": "", "dec": 3},
    {"cle": "wue_source", "section": "eau", "champ": "wue_source",
     "nom": "Eau de la source (WUE)", "unite": "L/kWh IT", "dec": 2},
    {"cle": "co2", "section": "carbone", "champ": "empreinte_totale_t",
     "nom": "Empreinte carbone totale", "unite": "tCO2e/an", "dec": 0},
    {"cle": "erf", "section": "chaleur", "champ": "erf",
     "nom": "Chaleur fatale réutilisée (ERF)", "unite": "%", "dec": 1},
]

# Définition de la portée, écrite ici pour être affichée telle quelle : elle
# rapporte l'étendue au PLUS GRAND des résultats possibles, et non à la valeur
# courante. Rapportée à la valeur courante, une grandeur nulle par défaut —
# l'ERF quand rien n'est réutilisé — donnait une division par zéro traitée en
# « 0 % », c'est-à-dire l'inverse de la vérité : tout y est encore ouvert.
PORTEE_DEFINITION = (
    "Part du résultat encore indéterminée : (plus haut − plus bas) rapporté au "
    "plus haut des résultats possibles. 100 % signifie que la grandeur n'est "
    "pas du tout fixée tant que ce champ reste vide.")


def _mesures(res):
    """Extrait les trois grandeurs de tête d'une étude complète."""
    out = {}
    for ind in INDICATEURS:
        bloc = res.get(ind["section"]) or {}
        val = (bloc.get(ind["champ"]) or {}).get("valeur")
        out[ind["cle"]] = float(val) if val is not None else None
    return out


def _signature_leviers(res):
    """Quels leviers le moteur propose. Certains champs ne changent aucune
    grandeur mais changent la liste des leviers — la classe ASHRAE est le cas
    d'école. Une barre à zéro sans cette précision se lit « ce champ ne sert à
    rien », ce qui est faux."""
    return tuple(sorted((l.get("titre") or l.get("nom") or "")
                        for l in (res.get("leviers") or [])))


# ── Les domaines balayables ────────────────────────────────────────────────
# `valeurs` est une fonction pour que les listes soient lues au référentiel au
# moment de l'appel, et non figées à l'import : une famille ajoutée à
# datacenter.py entre d'elle-même dans le balayage.
DOMAINES = {
    "refroidissement": {
        "valeurs": lambda: list(D.REFROIDISSEMENT.keys()),
        "nature": "referentiel",
        "origine": "les familles énumérées au référentiel",
    },
    "pays": {
        "valeurs": lambda: [c for c in sorted(D.EWIF_PAYS) if c != "UE"],
        "nature": "referentiel",
        "origine": "les pays documentés au référentiel (hors moyenne UE)",
    },
    "classe_ashrae": {
        "valeurs": lambda: list(D.CLASSES_ASHRAE.keys()),
        "nature": "referentiel",
        "origine": "les classes ASHRAE du référentiel",
    },
    "intensite_reseau_g": {
        "valeurs": lambda: sorted(set(D.INTENSITE_RESEAU.values())),
        "nature": "referentiel",
        "origine": "les intensités carbone des mix européens du référentiel",
    },
    "part_evaporative": {
        "valeurs": lambda: [i / 10.0 for i in range(11)],
        "nature": "definition",
        "origine": "une part vaut entre 0 et 1, par définition",
    },
    "part_renouvelable": {
        "valeurs": lambda: [i / 10.0 for i in range(11)],
        "nature": "definition",
        "origine": "une part vaut entre 0 et 1, par définition",
    },
    "part_chaleur_reutilisee": {
        "valeurs": lambda: [i / 10.0 for i in range(11)],
        "nature": "definition",
        "origine": "une part vaut entre 0 et 1, par définition",
    },
    "taux_charge": {
        "valeurs": lambda: _suite(BALAYAGE_TAUX[0], BALAYAGE_TAUX[1], PAS_TAUX),
        "nature": "hypothese",
        "origine": "balayage déclaré de %s à %s"
                   % (D.fr(BALAYAGE_TAUX[0]), D.fr(BALAYAGE_TAUX[1])),
    },
    "cycles_concentration": {
        "valeurs": lambda: [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
        "nature": "hypothese",
        "origine": "balayage déclaré de %s à %s cycles"
                   % (D.fr(BALAYAGE_COC[0]), D.fr(BALAYAGE_COC[1])),
    },
}

# Ce qu'on refuse de balayer, et pourquoi. Le dire vaut mieux que de laisser
# croire que la liste des facteurs est exhaustive.
EXCLUS = {
    "puissance_it_kw":
        "C'est la seule entrée indispensable : sans elle il n'y a pas d'étude, "
        "et elle n'a pas de plage par défaut à explorer.",
    "nb_serveurs":
        "Aucune plage défendable sans connaître la densité visée. Ce champ "
        "n'agit que sur la part serveurs du carbone incorporé.",
    "prix_electricite_eur_mwh":
        "Le prix dépend d'un contrat, pas d'un référentiel technique. Lui "
        "inventer une plage fabriquerait une sensibilité qui n'existe pas.",
    "pue_cible":
        "Un PUE imposé ne se balaie pas : il REMPLACE la plage de conception "
        "par un engagement contractuel. La bande d'incertitude du PUE tombe "
        "alors à zéro — non parce que le réel est mieux connu, mais parce "
        "qu'un engagement a été pris à sa place.",
}


def _libelles():
    return {c["id"]: c for c in D.CHAMPS}


# ── Saisi, ou seulement par défaut ? ───────────────────────────────────────
# Le formulaire PRÉ-REMPLIT les valeurs par défaut dans les champs. Elles
# reviennent donc au serveur comme si elles avaient été tapées, et la première
# version de ce module les comptait pour des saisies : la page annonçait sept
# champs renseignés là où l'utilisateur n'en avait rempli qu'un, et retirait de
# l'analyse des incertitudes qui n'avaient pas été levées. Un champ n'est
# considéré comme renseigné que s'il S'ÉCARTE de sa valeur par défaut.
#
# La limite de ce test est réelle et vaut d'être dite : qui saisit exactement
# la valeur par défaut est indiscernable de qui l'a laissée. Le doute est
# tranché du côté prudent — l'incertitude reste affichée.
SAISI, DEFAUT, ABSENT = "saisi", "defaut", "absent"

NOTE_DEFAUT_EGAL = (
    "Un champ laissé sur sa valeur par défaut compte comme non renseigné : le "
    "formulaire la pré-remplit, et rien ne distingue une valeur acceptée d'une "
    "valeur choisie. Modifiez-la — même pour y revenir — et l'incertitude "
    "correspondante disparaît de cette analyse.")


def _etat(profil, champ):
    cid = champ["id"]
    if cid not in profil or profil[cid] in ("", None):
        return ABSENT
    if "defaut" not in champ:
        return SAISI
    d, v = champ["defaut"], profil[cid]
    if isinstance(d, (int, float)) and not isinstance(d, bool):
        try:
            return DEFAUT if abs(float(v) - float(d)) < 1e-9 else SAISI
        except (TypeError, ValueError):
            return SAISI
    return DEFAUT if str(v).strip() == str(d).strip() else SAISI


# ═══════════════════════════════════════════════════════════════════════════
#  1. Ce qui est renseigné, ce qui reste par défaut
# ═══════════════════════════════════════════════════════════════════════════

def defauts(profil):
    """Le relevé champ par champ. La page annonce que tout sauf la puissance a
    une valeur par défaut ; voici lesquelles tiennent encore."""
    profil = profil or {}
    lignes = []
    for c in D.CHAMPS:
        cid = c["id"]
        e = _etat(profil, c)
        lignes.append({
            "id": cid,
            "label": c["label"],
            "unite": c.get("unite", ""),
            "requis": bool(c.get("requis")),
            "etat": e,
            "renseigne": e == SAISI,
            "valeur": profil.get(cid) if e != ABSENT else None,
            "defaut": c.get("defaut"),
            "balayable": cid in DOMAINES,
            "motif_exclusion": EXCLUS.get(cid, ""),
        })
    n_rens = sum(1 for l in lignes if l["etat"] == SAISI)
    n_def = sum(1 for l in lignes if l["etat"] == DEFAUT)
    return {
        "champs": lignes,
        "n_total": len(lignes),
        "n_renseignes": n_rens,
        "n_defaut": len(lignes) - n_rens,
        "n_valeur_defaut": n_def,
        "n_absents": len(lignes) - n_rens - n_def,
        "note": NOTE_DEFAUT_EGAL,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  2. La courbe de charge partielle
# ═══════════════════════════════════════════════════════════════════════════

def courbe_charge(profil):
    """PUE et énergie en fonction du taux de charge, moteur à l'appui.

    C'est la courbe que l'aide du champ décrit en une phrase (« sous 0,55, la
    pénalité de charge partielle devient le premier poste de perte ») sans
    jamais la montrer. Le coude n'est pas dessiné depuis une constante recopiée
    ici : il est DÉTECTÉ sur les points calculés. Si le seuil du moteur bouge,
    la courbe et le repère bougent avec lui.
    """
    profil = dict(profil or {})
    if not profil.get("puissance_it_kw"):
        return {"disponible": False,
                "motif": "La puissance informatique est nécessaire pour tracer la courbe."}

    pts = []
    for t in _suite(BALAYAGE_TAUX[0], BALAYAGE_TAUX[1], PAS_TAUX):
        p = dict(profil)
        p["taux_charge"] = t
        e = D.etude(p)["energie"]
        pue = e["pue"]
        # La bande de conception est portée par l'incertitude du PUE ; on la
        # relit plutôt que de la recomposer depuis la famille.
        bande = _bande_pue(pue)
        pts.append({
            "taux": round(t, 4),
            "pue": round(float(pue["valeur"]), 4),
            "pue_min": bande[0],
            "pue_max": bande[1],
            "energie_totale_MWh": round(float(e["energie_totale_MWh"]["valeur"]), 1),
            "energie_it_MWh": round(float(e["energie_it_MWh"]["valeur"]), 1),
        })

    impose = bool(profil.get("pue_cible"))
    taux_courant = float(profil.get("taux_charge") or 0.65)
    return {
        "disponible": True,
        "points": pts,
        "coude": None if impose else _coude(pts),
        "courant": _au_taux(pts, taux_courant),
        "taux_courant": taux_courant,
        "taux_renseigne": "taux_charge" in (profil or {}),
        "pue_impose": impose,
        "balayage": [BALAYAGE_TAUX[0], BALAYAGE_TAUX[1]],
        "famille": (D.REFROIDISSEMENT.get(profil.get("refroidissement"))
                    or D.REFROIDISSEMENT["eau_glacee"])["nom"],
        "note": ("Un PUE imposé au cahier des charges remplace le modèle : la "
                 "courbe est plate et la bande de conception disparaît, parce "
                 "qu'un engagement a été pris à la place du calcul."
                 if impose else
                 "La bande est la plage de conception de la famille retenue. "
                 "La pénalité de charge partielle la décale vers le haut sans "
                 "la resserrer : mal charger une salle ne rend pas son PUE "
                 "plus prévisible, seulement plus mauvais."),
    }


def _bande_pue(pue_trace):
    """Prend la bande que le moteur expose en donnée.

    Elle a d'abord été relue dans la phrase d'incertitude (« plage de
    conception 1,25 – 1,45 ») par un analyseur maison. C'était une erreur : la
    phrase est rédigée pour être lue, pas analysée, et la reformuler aurait
    cassé le tracé sans que rien ne le signale. datacenter.py porte désormais
    `bande` à côté d'elle.
    """
    b = pue_trace.get("bande")
    if isinstance(b, dict) and "min" in b and "max" in b:
        return [round(float(b["min"]), 4), round(float(b["max"]), 4)]
    # PUE imposé au cahier des charges : le moteur n'expose aucune bande, il
    # n'y en a plus. La valeur tient lieu des deux bornes.
    v = round(float(pue_trace["valeur"]), 4)
    return [v, v]


def _coude(pts):
    """Le taux au-dessous duquel le PUE commence à se dégrader.

    Détecté sur les pentes successives : le dernier point où la pente cesse
    d'être nulle. Aucune valeur de seuil n'est écrite ici."""
    if len(pts) < 3:
        return None
    seuil = 1e-6
    dernier = None
    for i in range(len(pts) - 1):
        d = pts[i + 1]["pue"] - pts[i]["pue"]
        if abs(d) > seuil:
            dernier = pts[i + 1]["taux"]
    if dernier is None:
        return None
    pente = 0.0
    for i in range(len(pts) - 1):
        if pts[i + 1]["taux"] <= dernier + 1e-9:
            d = pts[i + 1]["pue"] - pts[i]["pue"]
            dt = pts[i + 1]["taux"] - pts[i]["taux"]
            if abs(d) > seuil and dt:
                pente = d / dt
    return {"taux": dernier, "pente_par_point_de_charge": round(pente / 100.0, 6),
            "note": "Au-dessus, le PUE de conception ne dépend plus du taux de "
                    "charge dans ce modèle. Au-dessous, chaque point de charge "
                    "perdu dégrade le PUE."}


def _au_taux(pts, t):
    if not pts:
        return None
    return min(pts, key=lambda p: abs(p["taux"] - t))


# ═══════════════════════════════════════════════════════════════════════════
#  3. La sensibilité : ce que chaque champ vide laisse encore ouvert
# ═══════════════════════════════════════════════════════════════════════════

def sensibilite(profil):
    """Pour chaque champ non renseigné, l'étendue des résultats encore possibles.

    Lecture — et elle est essentielle : ces étendues NE S'ADDITIONNENT PAS.
    Chaque barre répond à « si ce champ seul reste inconnu, tout le reste étant
    ce que vous avez dit ». Le pays fixe à la fois le facteur eau et l'intensité
    carbone : sa barre et celle de l'intensité du contrat décrivent en partie le
    même écart.
    """
    profil = dict(profil or {})
    if not profil.get("puissance_it_kw"):
        return {"disponible": False,
                "motif": "La puissance informatique est nécessaire pour mesurer les écarts."}

    base = D.etude(profil)
    ref = _mesures(base)
    lev_base = _signature_leviers(base)
    lib = _libelles()
    facteurs = []
    for cid, dom in DOMAINES.items():
        # Renseigné signifie « écarté de la valeur par défaut ». Un champ resté
        # sur son pré-remplissage laisse son incertitude entière : le retirer
        # ici ferait disparaître de l'écran une inconnue que personne n'a levée.
        if _etat(profil, lib.get(cid) or {"id": cid}) == SAISI:
            continue
        vals = dom["valeurs"]()
        if not vals:
            continue
        # L'état courant fait partie de la comparaison : un champ dont toutes
        # les valeurs donnent les mêmes leviers, mais d'autres que ceux affichés
        # aujourd'hui, change bel et bien quelque chose.
        mesures, leviers_vus = [], {lev_base}
        for v in vals:
            p = dict(profil)
            p[cid] = v
            r = D.etude(p)
            mesures.append((v, _mesures(r)))
            leviers_vus.add(_signature_leviers(r))

        etendues, pire = {}, None
        for ind in INDICATEURS:
            k = ind["cle"]
            suite = [(v, m[k]) for v, m in mesures if m.get(k) is not None]
            if not suite:
                continue
            bas = min(suite, key=lambda x: x[1])
            haut = max(suite, key=lambda x: x[1])
            socle = ref.get(k) or 0.0
            # Dénominateur : le plus grand résultat possible, jamais la valeur
            # courante. Voir PORTEE_DEFINITION — une référence nulle rendait la
            # mesure indéfinie et la faisait passer pour un zéro.
            echelle = max(abs(bas[1]), abs(haut[1]))
            rel = ((haut[1] - bas[1]) / echelle * 100.0) if echelle else 0.0
            etendues[k] = {
                "min": round(bas[1], 4), "max": round(haut[1], 4),
                "min_pour": _lisible(cid, bas[0]), "max_pour": _lisible(cid, haut[0]),
                "actuel": round(socle, 4),
                "etendue_relative_pct": round(rel, 1),
            }
            if pire is None or rel > pire:
                pire = rel

        facteurs.append({
            "id": cid,
            "label": (lib.get(cid) or {}).get("label", cid),
            "nature": dom["nature"],
            "origine": dom["origine"],
            "n_valeurs": len(vals),
            "etendues": etendues,
            "portee_max_pct": round(pire or 0.0, 1),
            # Un champ peut ne changer aucune grandeur et changer pourtant les
            # leviers proposés : le dire évite de lire « inutile » là où il faut
            # lire « agit ailleurs ».
            "change_les_leviers": len(leviers_vus) > 1,
        })

    facteurs.sort(key=lambda f: -f["portee_max_pct"])
    return {
        "disponible": True,
        "indicateurs": INDICATEURS,
        "portee_definition": PORTEE_DEFINITION,
        "reference": {k: round(v, 4) for k, v in ref.items() if v is not None},
        "facteurs": facteurs,
        "n_ouverts": len(facteurs),
        "exclus": [{"id": k, "label": (lib.get(k) or {}).get("label", k), "motif": m}
                   for k, m in EXCLUS.items()],
        "balayage_note": BALAYAGE_NOTE,
        "note_addition": (
            "Ces étendues ne s'additionnent pas : chacune suppose que les "
            "autres champs valent ce qui est affiché. Le pays commande à la "
            "fois le facteur eau et l'intensité carbone — sa barre recouvre "
            "en partie celle de l'intensité du contrat."),
        "leviers_seuls": [f["label"] for f in facteurs
                          if f["portee_max_pct"] < 0.05 and f["change_les_leviers"]],
    }


def _lisible(cid, v):
    """Le nom de la valeur, pas sa clé. « tour_evaporative » dans une infobulle
    oblige le lecteur à traduire ce que le référentiel sait déjà dire."""
    if cid == "refroidissement":
        return (D.REFROIDISSEMENT.get(v) or {}).get("nom", v)
    if cid == "pays":
        mix = (D.EWIF_PAYS.get(v) or {}).get("mix", "")
        return "%s — %s" % (v, mix) if mix else str(v)
    if cid == "intensite_reseau_g":
        return "%s gCO2e/kWh" % D.fr(v)
    if isinstance(v, float):
        return D.fr(v)
    return str(v)


# ═══════════════════════════════════════════════════════════════════════════
#  4. L'assemblage
# ═══════════════════════════════════════════════════════════════════════════

def apercu(profil):
    profil = dict(profil or {})
    d = defauts(profil)
    s = sensibilite(profil)
    c = courbe_charge(profil)

    tete = ""
    if s.get("disponible") and s.get("facteurs"):
        f = s["facteurs"][0]
        tete = ("Le champ qui laisse le plus d'indétermination est « %s » : "
                "sans lui, jusqu'à %s %% d'une grandeur de tête reste ouvert."
                % (f["label"], D.fr(f["portee_max_pct"], 0)))
    elif s.get("disponible"):
        tete = ("Tous les champs à domaine borné sont renseignés : il ne reste "
                "que les incertitudes du référentiel lui-même.")

    return {
        "version": VERSION,
        "defauts": d,
        "courbe_charge": c,
        "sensibilite": s,
        "entete": tete,
    }


def sante():
    """Auto-contrôle. Vérifie que le coude est bien DÉTECTÉ et non supposé, et
    que le balayage porte sur des domaines non vides."""
    p = {"puissance_it_kw": 2000}
    c = courbe_charge(p)
    s = sensibilite(p)
    return {
        "version": VERSION,
        "points_courbe": len(c.get("points") or []),
        "coude_detecte": (c.get("coude") or {}).get("taux"),
        "facteurs_balayes": len(s.get("facteurs") or []),
        "facteur_dominant": (s.get("facteurs") or [{}])[0].get("label"),
        "domaines_vides": [k for k, d in DOMAINES.items() if not d["valeurs"]()],
        "exclus": len(EXCLUS),
        "moteur": D.VERSION,
    }
