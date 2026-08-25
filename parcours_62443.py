"""LE PARCOURS 62443 — dans quel ordre, et pourquoi celui-là.

CE QUE CE MODULE AJOUTE À LA LISTE DE VÉRIFICATION

`checklist_62443` compte ce qui est coché, et s'arrête là — c'est sa règle,
écrite dans son en-tête. Ce module-ci fait le pas suivant, qui est d'un autre
ordre : il dit DANS QUEL ORDRE prendre ce qui reste, et pourquoi.

Il est séparé pour cette raison exactement. Le compte est un fait ; l'ordre est
un JUGEMENT DE CE CABINET. Les mêlant dans un seul fichier, on aurait fini par
lire l'ordre avec l'autorité du compte.

════════════════════════════════════════════════════════════════════════════
CE QUE CE MODULE NE REND PAS, ET IL FAUT LE LIRE AVANT LE RESTE
════════════════════════════════════════════════════════════════════════════
IL NE REND AUCUN NIVEAU DE MATURITÉ. C'était la demande — « une évaluation de
la maturité en fonction des réponses » — et c'est la seule partie de la
demande qui n'est pas tenue telle quelle. Le motif n'est pas une pudeur :

  · La CEI 62443-2-4 définit des NIVEAUX DE MATURITÉ (ML 1 à 4) pour le
    programme d'un PRESTATAIRE. La 62443-3-3 définit des NIVEAUX DE SÉCURITÉ
    (SL 1 à 4) par exigence et par zone. Les deux se constatent sur PREUVES,
    pour un périmètre donné, par une évaluation conduite.
  · Un compte de cases n'est ni l'un ni l'autre. « ML 2 » affiché au bas d'un
    formulaire serait cité en réunion, puis en offre, puis devant un auditeur
    qui demanderait sur quelle évaluation il repose — et il n'y en aurait pas.
  · La liste elle-même le dit, à son point `eval_fournisseurs` : « C'est ici,
    et SEULEMENT ici, qu'un niveau de maturité se constate. »

CE QUI EST RENDU À LA PLACE, et qui décide davantage : OÙ ÇA COINCE. Un
pourcentage dit à quelle distance on est de la fin ; il ne dit pas par quoi
commencer. Un verrou nommé — « l'inventaire bloque neuf points » — se traduit
en décision le jour même.

════════════════════════════════════════════════════════════════════════════
L'ORDRE VIENT D'UNE TABLE DE PRÉALABLES, ÉCRITE ET MOTIVÉE
════════════════════════════════════════════════════════════════════════════
Un préalable n'est pas une préférence de méthode : c'est un point sans lequel
un autre NE PEUT PAS ÊTRE PROUVÉ. On ne segmente pas un parc qu'on n'a pas
recensé ; un corrélateur n'a rien à lire sans journalisation ; un pare-feu se
place ENTRE deux zones, donc après le zonage.

Chaque arête porte sa raison, et le module refuse de se charger si l'une
manque. C'est le même traitement que `EDITEURS_INDUSTRIELS` chez le voisin :
une table tenue à la main, relisible ligne à ligne, qui s'assume comme
jugement plutôt que de se déguiser en dérivation.

CE QUI N'EST PAS DÉCLARÉ EST LIBRE. Les arêtes transitives ne sont pas
écrites — `pare_feu` dépend de `zones_conduits`, qui dépend de
`analyse_risque` : l'écrire trois fois ferait trois lignes à maintenir pour
une seule idée, et la troisième finirait par contredire les deux autres.
"""

import checklist_62443 as CK

VERSION = "2026-08-a"

#: CE QUE CE MODULE REFUSE DE RENDRE, dans les mots où il le rendra à l'écran
#: et dans le document emporté. La phrase voyage avec le résultat : servie à
#: part, elle resterait sur la page pendant que le chiffre, lui, partirait.
REFUS_NIVEAU = (
    "Ce parcours ne rend AUCUN niveau de maturité ni de sécurité. La CEI "
    "62443-2-4 définit des niveaux de maturité (ML 1 à 4) pour le programme "
    "d'un prestataire, la 62443-3-3 des niveaux de sécurité (SL 1 à 4) par "
    "exigence et par zone ; les deux se constatent sur preuves, pour un "
    "périmètre donné, par une évaluation conduite. Ce que vous lisez ici est "
    "un ÉTAT DE PRÉPARATION : ce qui est coché, ce qui reste, et dans quel "
    "ordre le prendre."
)

#: LE SEUL POINT DE LA LISTE OÙ UN NIVEAU DE MATURITÉ SE CONSTATE VRAIMENT.
#: Il est nommé parce qu'un lecteur qui cherche « la maturité » doit être
#: envoyé quelque part, et non simplement éconduit.
OU_LA_MATURITE_SE_CONSTATE = "eval_fournisseurs"

#: LA TABLE DES PRÉALABLES — jugement de ce cabinet, motivé arête par arête.
#: Lire : « pour prouver CLÉ, il faut d'abord PRÉALABLE, parce que RAISON. »
PREALABLES = {
    "analyse_risque": [
        ("inventaire",
         "On analyse le risque de ce qu'on a recensé. Une analyse conduite "
         "sur un parc supposé porte sur un parc qui n'existe pas — et c'est "
         "elle qui fixera les niveaux cibles par zone."),
    ],
    "traitement_risque": [
        ("analyse_risque",
         "Un plan de traitement traite les risques D'UNE ANALYSE : sans "
         "elle, il traite une intuition, et la colonne « risque accepté » "
         "n'a rien à quoi se rattacher."),
    ],
    "zones_conduits": [
        ("analyse_risque",
         "Le zonage se rattache à l'analyse de risque qui le fonde — c'est "
         "ce que dit la preuve exigée au point lui-même. Un découpage sans "
         "elle est un schéma réseau, pas un modèle de zones."),
    ],
    "pare_feu": [
        ("zones_conduits",
         "Un pare-feu se place ENTRE deux zones. Sans zonage, on pose un "
         "équipement au hasard d'une topologie et on appelle cela une "
         "frontière."),
    ],
    "dmz": [
        ("zones_conduits",
         "Une DMZ industrielle est une zone du modèle. Sa présence comme "
         "son absence se justifient par rapport à lui."),
    ],
    "conduits": [
        ("zones_conduits",
         "Un conduit est un objet du zonage : il n'existe pas avant lui. "
         "Sécuriser des conduits non définis revient à chiffrer des liens "
         "choisis au jugé."),
    ],
    "mfa": [
        ("analyse_risque",
         "La preuve exigée est « la liste des systèmes concernés » : c'est "
         "l'analyse de risque qui dit lesquels sont critiques. Sans elle, on "
         "équipe ce qui était commode à équiper."),
    ],
    "privileges": [
        ("inventaire",
         "Le moindre privilège se règle système par système, et la liste des "
         "systèmes est l'inventaire. Une matrice de rôles sur un parc "
         "incomplet laisse des droits hors matrice."),
    ],
    "comptes_defaut": [
        ("inventaire",
         "On désactive les comptes par défaut DES ÉQUIPEMENTS RECENSÉS. "
         "Ceux qu'on ignore gardent les leurs, et c'est une exigence de "
         "composant : elle se vérifie automate par automate."),
    ],
    "mots_de_passe": [
        ("politique",
         "Une règle de mot de passe est un objet de politique : écrite "
         "ailleurs, elle n'oblige personne et se négocie projet par projet."),
    ],
    "journalisation": [
        ("inventaire",
         "Journaliser suppose de savoir QUOI journaliser. Un périmètre de "
         "journalisation qui ne couvre pas tout le parc laisse ses angles "
         "morts là où ils étaient déjà."),
    ],
    "antivirus": [
        ("inventaire",
         "La preuve exigée est « le parc couvert » : sans inventaire, la "
         "couverture se mesure sur un dénominateur inconnu."),
    ],
    "sauvegardes": [
        ("inventaire",
         "On sauvegarde les configurations d'équipements identifiés. Ce qui "
         "n'est pas au parc n'est pas sauvegardé, et cela ne se découvre "
         "qu'à la restauration."),
    ],
    "correctifs": [
        ("inventaire",
         "« On ne protège, ne segmente ni ne corrige que ce qu'on a "
         "recensé » — la preuve de l'inventaire le dit dans ces termes. Le "
         "plan de correctifs a besoin des versions en service."),
    ],
    "durcissement": [
        ("inventaire",
         "Un relevé de configuration par type d'équipement suppose de "
         "connaître les types en service. Exigence de composant, vérifiée "
         "sur le matériel réel."),
    ],
    "chiffrement": [
        ("analyse_risque",
         "« Les flux concernés » : ce qui est sensible se décide dans "
         "l'analyse, pas au moment de choisir un algorithme."),
    ],
    "ids": [
        ("zones_conduits",
         "Une sonde se place sur un conduit ou en bordure de zone. Les "
         "points de capture exigés en preuve n'existent pas avant le "
         "modèle."),
    ],
    "anomalies": [
        ("ids",
         "Une référence de trafic normal se construit sur ce qu'une sonde "
         "capte. Sans capture, la référence est une hypothèse."),
    ],
    "siem": [
        ("journalisation",
         "Un corrélateur corrèle des journaux. Sans journalisation, il n'a "
         "rien à lire — et une plateforme sans source raccordée produit un "
         "coût, pas une détection."),
    ],
    "incidents": [
        ("responsable",
         "Une procédure d'incident nomme qui décide et qui déclare. Sans "
         "responsable désigné, elle nomme un poste vacant, et c'est pendant "
         "la crise qu'on s'en aperçoit."),
    ],
    "clauses": [
        ("politique",
         "Les exigences portées au marché déclinent la politique. Écrites "
         "sans elle, elles varient d'un contrat à l'autre et rien ne dit "
         "laquelle fait foi."),
    ],
}

#: Les points sans aucun préalable — ce par quoi on peut commencer un lundi.
#: Calculé, jamais recopié : une liste tenue à part se serait décrochée de la
#: table au premier ajout.


def _tous():
    return {p["cle"]: (s, p) for s, p in CK._points()}


def _verifier():
    """LA TABLE DOIT RESTER RELISIBLE, ET ACYCLIQUE.

    Une arête vers un point inexistant bloquerait à jamais son dépendant ; un
    cycle rendrait un parcours dans lequel rien n'est jamais atteignable, et
    la page afficherait « rien à faire » à qui n'a rien fait.
    """
    connus = set(_tous())
    for cle, aretes in PREALABLES.items():
        if cle not in connus:
            raise ValueError("préalable posé sur un point inconnu : %s" % cle)
        vus = set()
        for prealable, pourquoi in aretes:
            if prealable not in connus:
                raise ValueError("préalable inconnu : %s → %s" % (cle, prealable))
            if prealable == cle:
                raise ValueError("point préalable de lui-même : %s" % cle)
            if prealable in vus:
                raise ValueError("préalable en double : %s → %s" % (cle, prealable))
            vus.add(prealable)
            # UNE ARÊTE SANS RAISON EST UNE PRÉFÉRENCE DÉGUISÉE EN CONTRAINTE.
            # C'est tout ce qui sépare cette table d'un ordre arbitraire.
            if len(str(pourquoi).strip()) < 60:
                raise ValueError("préalable %s → %s sans raison écrite"
                                 % (cle, prealable))

    # PAS DE CYCLE — vérifié par parcours en profondeur, pas supposé.
    etat = {}

    def descendre(n):
        if etat.get(n) == "fini":
            return
        if etat.get(n) == "en cours":
            raise ValueError("cycle de préalables sur : %s" % n)
        etat[n] = "en cours"
        for prealable, _ in PREALABLES.get(n, []):
            descendre(prealable)
        etat[n] = "fini"

    for cle in connus:
        descendre(cle)


_verifier()


def _bloques_par(cle, memo=None):
    """Tous les points qui dépendent de `cle`, directement ou non.

    C'EST CE NOMBRE QUI CLASSE LE PARCOURS. « L'inventaire bloque neuf
    points » est une phrase qui décide ; « l'inventaire est important » n'en
    est pas une.
    """
    if memo is None:
        memo = {}
    if cle in memo:
        return memo[cle]
    memo[cle] = set()
    sortants = [c for c, ar in PREALABLES.items()
                if any(p == cle for p, _ in ar)]
    out = set(sortants)
    for s in sortants:
        out |= _bloques_par(s, memo)
    memo[cle] = out
    return out


def evaluer(coches=None):
    """OÙ VOUS EN ÊTES, ET CE QUI VOUS BLOQUE.

    Le compte vient de `checklist_62443.compter` — il n'est pas refait ici :
    deux comptes du même objet finissent par afficher deux nombres.
    """
    base = CK.compter(coches)
    if not base.get("ok"):
        return base

    vues = {str(x) for x in (coches or [])}
    tous = _tous()

    manquants = [c for c in tous if c not in vues]
    memo = {}

    def prets(cle):
        return all(p in vues for p, _ in PREALABLES.get(cle, []))

    atteignables = [c for c in manquants if prets(c)]
    en_attente = [c for c in manquants if not prets(c)]

    # LES VERROUS : ce qui n'est pas fait ET dont d'autres dépendent, classé
    # par le nombre de points qu'il libère. Un verrou qui ne bloque rien n'est
    # pas un verrou, c'est une tâche.
    verrous = []
    for c in manquants:
        aval = {x for x in _bloques_par(c, memo) if x in manquants}
        if aval:
            s, p = tous[c]
            verrous.append({
                "cle": c, "libelle": p["libelle"], "section": s["nom"],
                "rattachement": p["rattachement"], "preuve": p["preuve"],
                "bloque": len(aval),
                "bloque_lesquels": sorted(aval),
                "atteignable": prets(c),
            })
    verrous.sort(key=lambda v: (-v["bloque"], v["cle"]))

    return dict(
        base,
        version_parcours=VERSION,
        # LE MOT « MATURITÉ » N'APPARAÎT PAS DANS UNE CLÉ DE RÉSULTAT, et
        # c'est délibéré : un client d'API qui lirait `maturite` afficherait
        # « maturité » quoi qu'en dise la note d'à côté.
        etat_preparation={
            "coches": len(vues),
            "sur": len(tous),
            "atteignables": len(atteignables),
            "en_attente": len(en_attente),
        },
        verrous=verrous,
        ce_que_ce_n_est_pas=REFUS_NIVEAU,
        ou_la_maturite_se_constate={
            "cle": OU_LA_MATURITE_SE_CONSTATE,
            "libelle": tous[OU_LA_MATURITE_SE_CONSTATE][1]["libelle"],
            "fait": OU_LA_MATURITE_SE_CONSTATE in vues,
            "dit": "C'est le seul point de cette liste où un niveau de "
                   "maturité se constate vraiment — au sens de la 62443-2-4, "
                   "et sur le programme d'un prestataire, pas sur le vôtre.",
        },
        lecture_parcours=_lecture_parcours(manquants, verrous, atteignables),
    )


def _lecture_parcours(manquants, verrous, atteignables):
    if not manquants:
        return ("Les vingt-sept points sont cochés. Le parcours s'arrête ici ; "
                "l'étape suivante n'est plus une liste mais une évaluation sur "
                "preuves, périmètre par périmètre.")
    if verrous and verrous[0]["bloque"] >= 3:
        v = verrous[0]
        return ("%d point(s) restent. Le premier verrou est « %s » : %d autres "
                "points en dépendent et ne pourront pas être prouvés avant "
                "lui. C'est là que se décide le calendrier, pas dans le total."
                % (len(manquants), v["libelle"], v["bloque"]))
    return ("%d point(s) restent, dont %d peuvent être engagés dès maintenant "
            "— aucun préalable ne leur manque."
            % (len(manquants), len(atteignables)))


def parcours(coches=None):
    """LE CHEMIN, EN VAGUES.

    UNE VAGUE N'EST PAS UN TRIMESTRE. C'est un ensemble de points dont tous
    les préalables sont satisfaits une fois la vague précédente faite —
    autrement dit : ce qu'on peut mener EN PARALLÈLE. Y coller des dates
    supposerait connaître les moyens de la maison, que ce site n'a pas.

    À L'INTÉRIEUR D'UNE VAGUE, l'ordre est celui du nombre de points libérés,
    puis celui de la liste. Faire remonter ce qui débloque le plus est la
    seule règle qui rende le classement utile plutôt que décoratif.
    """
    ev = evaluer(coches)
    if not ev.get("ok"):
        return ev

    vues = {str(x) for x in (coches or [])}
    tous = _tous()
    restants = [c for c in tous if c not in vues]
    memo = {}
    acquis = set(vues)
    vagues = []

    while restants:
        prete = [c for c in restants
                 if all(p in acquis for p, _ in PREALABLES.get(c, []))]
        if not prete:
            # INATTEIGNABLE : impossible tant que `_verifier` interdit les
            # cycles. Le cas est traité quand même — une boucle infinie dans
            # une page se lit comme une panne du serveur.
            break
        prete.sort(key=lambda c: (-len({x for x in _bloques_par(c, memo)
                                        if x in restants}), c))
        etapes = []
        for c in prete:
            s, p = tous[c]
            aval = sorted({x for x in _bloques_par(c, memo) if x in restants})
            etapes.append({
                "cle": c,
                "libelle": p["libelle"],
                "section": s["nom"],
                "section_cle": s["cle"],
                "rattachement": p["rattachement"],
                "partie_titre": CK.PARTIES[p["rattachement"]]["titre"],
                "preuve": p["preuve"],
                "libere": len(aval),
                "libere_lesquels": aval,
                "prealables": [
                    {"cle": pre, "libelle": tous[pre][1]["libelle"],
                     "pourquoi": pourquoi, "fait": pre in acquis}
                    for pre, pourquoi in PREALABLES.get(c, [])
                ],
            })
        vagues.append({"rang": len(vagues) + 1, "n": len(etapes),
                       "etapes": etapes})
        acquis |= set(prete)
        restants = [c for c in restants if c not in acquis]

    return dict(ev, vagues=vagues, n_vagues=len(vagues), bloques_hors_vague=restants)


# ══════════════════════════════════════════════════════════════════════════
#  LE DOCUMENT EMPORTÉ
# ══════════════════════════════════════════════════════════════════════════
# IL CIRCULE SANS SA PAGE — transféré, imprimé, joint à un comité de pilotage,
# relu six mois plus tard par quelqu'un qui n'a jamais vu ce site. Il porte
# donc TOUT ce qui permet d'en juger, y compris ce qui le relativise : la
# réserve sur les niveaux de maturité arrive AVANT les chiffres, pas en note
# de bas de page.

def markdown(coches=None, titre=None):
    """La liste, l'état et le parcours, en Markdown — prêt pour `build_docx`
    et `build_pdf`, qui portent déjà la charte de la maison."""
    d = parcours(coches)
    if not d.get("ok"):
        return None
    vues = {str(x) for x in (coches or [])}
    L = []
    A = L.append

    A("# %s" % (titre or "Checklist IEC 62443 — état et parcours"))
    A("")
    A("> **Ce que ce document n'est pas.** %s" % REFUS_NIVEAU)
    A("")

    A("## Où vous en êtes")
    A("")
    e = d["etat_preparation"]
    A("**%d point(s) cochés sur %d.** %d peuvent être engagés dès maintenant, "
      "%d attendent un préalable." % (e["coches"], e["sur"],
                                      e["atteignables"], e["en_attente"]))
    A("")
    A(d["lecture"])
    A("")
    A(d["lecture_parcours"])
    A("")

    A("| Section | Cochés | Partie de la série |")
    A("| --- | --- | --- |")
    for s in d["par_section"]:
        A("| %s | %d / %d | %s |" % (s["nom"], s["faits"], s["sur"], s["partie"]))
    A("")

    if d["verrous"]:
        A("## Ce qui bloque le reste")
        A("")
        A("Un verrou est un point non fait dont d'autres dépendent. Le nombre "
          "dit combien de points il libère — c'est lui qui décide du "
          "calendrier, pas le total.")
        A("")
        for v in d["verrous"][:6]:
            A("- **%s** — libère %d point(s). *%s*"
              % (v["libelle"], v["bloque"],
                 "engageable maintenant" if v["atteignable"]
                 else "attend lui-même un préalable"))
        A("")

    A("## Le parcours")
    A("")
    A("Une vague rassemble ce qui peut être mené EN PARALLÈLE : tous ses "
      "préalables sont satisfaits une fois la vague précédente faite. Ce ne "
      "sont pas des trimestres — y coller des dates supposerait connaître vos "
      "moyens.")
    A("")
    for v in d["vagues"]:
        A("### Vague %d — %d point(s)" % (v["rang"], v["n"]))
        A("")
        for e2 in v["etapes"]:
            A("**%s**  " % e2["libelle"])
            A("%s · %s  " % (e2["section"], e2["rattachement"]))
            A("*Preuve à produire :* %s  " % e2["preuve"])
            if e2["libere"]:
                A("*Libère %d point(s) en aval.*  " % e2["libere"])
            for pre in e2["prealables"]:
                A("*Préalable :* %s — %s  " % (pre["libelle"], pre["pourquoi"]))
            A("")

    A("## Ce qui est déjà coché")
    A("")
    if not vues:
        A("Rien pour l'instant.")
    else:
        tous = _tous()
        for s in CK.SECTIONS:
            faits = [p for p in s["points"] if p["cle"] in vues]
            if not faits:
                continue
            A("**%s**" % s["nom"])
            A("")
            for p in faits:
                A("- %s — *preuve :* %s" % (p["libelle"], p["preuve"]))
            A("")
        del tous

    A("## Où un niveau de maturité se constate")
    A("")
    m = d["ou_la_maturite_se_constate"]
    A("%s Le point concerné est « %s » — %s."
      % (m["dit"], m["libelle"], "coché" if m["fait"] else "non coché à ce jour"))
    A("")
    A("*Liste de vérification version %s · parcours version %s.*"
      % (d["version"], VERSION))
    return "\n".join(L)


def sante():
    """CE QUE CE MODULE COUVRE, MESURÉ — pas annoncé."""
    tous = _tous()
    memo = {}
    racines = [c for c in tous if not PREALABLES.get(c)]
    plus = max(tous, key=lambda c: len(_bloques_par(c, memo)))
    return {
        "module": "parcours_62443",
        "version": VERSION,
        "portee": "Ordonne les points restants de la liste 62443 selon une "
                  "table de préalables écrite à la main et motivée arête par "
                  "arête. NE REND AUCUN NIVEAU de maturité ni de sécurité.",
        "points": len(tous),
        "aretes": sum(len(a) for a in PREALABLES.values()),
        "racines": sorted(racines),
        "verrou_principal": {"cle": plus, "bloque": len(_bloques_par(plus, memo))},
        "vagues_a_vide": parcours([])["n_vagues"],
        "modeles_de_langage": 0,
    }
