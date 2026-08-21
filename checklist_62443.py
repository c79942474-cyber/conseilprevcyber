"""CHECKLIST DE CONFORMITÉ IEC 62443 — vingt-sept points, et ce qu’ils prouvent.

CE QUE CE MODULE FAIT, ET CE QU’IL REFUSE DE FAIRE

Il porte une liste de vérification en six sections, chacune rattachée à la
partie de la série qui la fonde. Il compte ce qui est coché. Il s’arrête là.

IL NE REND PAS UN NIVEAU DE MATURITÉ, et c’est un refus délibéré. « Maturité »
n’est pas un mot vague dans cette série : la CEI 62443-2-4 définit des NIVEAUX
DE MATURITÉ (ML 1 à 4) et la 62443-3-3 des NIVEAUX DE SÉCURITÉ (SL 1 à 4). Les
deux se constatent sur preuves, par exigence, pour un périmètre donné — jamais
par un compte de cases. Afficher « 68 % de maturité » emprunterait le
vocabulaire de la norme pour désigner autre chose, et ce chiffre-là serait cité
en réunion, puis en offre, puis devant un auditeur qui demanderait sur quelle
évaluation il repose. La page de ce site consacrée à la maturité OT le dit déjà
dans ses propres termes : un assessment va « au-delà de la case à cocher ».

CE QUE LA LISTE VAUT DONC. Une liste de vérification sert à ne rien oublier
avant un audit, pas à s’auto-évaluer. C’est utile, et c’est autre chose.

CHAQUE POINT PORTE SA PREUVE. Une case cochée sans document derrière ne vaut
rien : c’est la première chose qu’un auditeur demande, et c’est ce qui distingue
une liste utile d’une liste décorative. Le champ `preuve` dit ce qu’il faudra
montrer.

CHAQUE POINT CITE UNE PARTIE DE LA SÉRIE, et cette partie est DÉCLARÉE dans ce
module avec ce qu’elle porte — un contrôle au chargement le vérifie. On cite la
partie, jamais le numéro de clause : une clause se cite sur le texte sous les
yeux, et ce module ne l’a pas. Là où le point relève de l’organisation sans
exigence technique précise, la partie citée est celle du programme de sécurité
(62443-2-1), qui est bien son fondement.
"""

VERSION = "2026-08-a"

# Les parties de la série effectivement citées ici, et ce qu’elles portent.
PARTIES = {
    "62443-2-1": {
        "titre": "Programme de sécurité pour les systèmes d’automatisation "
                 "et de contrôle industriels (CSMS)",
        "porte": "Ce que l’organisation doit mettre en place et tenir : "
                 "politique, rôles, gestion du risque, incidents, correctifs.",
    },
    "62443-2-4": {
        "titre": "Exigences de programme de sécurité pour les prestataires "
                 "de services IACS",
        "porte": "Ce qu’on exige d’un fournisseur ou d’un intégrateur, et les "
                 "NIVEAUX DE MATURITÉ (ML 1 à 4) auxquels il répond.",
    },
    "62443-2-3": {
        "titre": "Gestion des correctifs dans l’environnement IACS "
                 "(rapport technique)",
        "porte": "Comment un correctif se qualifie, se planifie et "
                 "s’applique quand l’arrêt du procédé n’est pas une option — "
                 "et ce qu’on fait de ce qui ne peut PAS être corrigé.",
    },
    "62443-3-2": {
        "titre": "Évaluation du risque de sécurité pour la conception du "
                 "système",
        "porte": "Le découpage en ZONES et CONDUITS, l’analyse de risque qui "
                 "le justifie, et le niveau de sécurité cible par zone.",
    },
    "62443-3-3": {
        "titre": "Exigences de sécurité système et niveaux de sécurité",
        "porte": "Les exigences système par fondement (FR 1 à FR 7) et les "
                 "NIVEAUX DE SÉCURITÉ (SL 1 à 4).",
    },
    "62443-4-2": {
        "titre": "Exigences de sécurité technique pour les composants IACS",
        "porte": "Ce qu’un composant — automate, station, équipement réseau — "
                 "doit savoir faire pour un niveau donné.",
    },
}

SECTIONS = [
    {
        "cle": "gouvernance",
        "nom": "Gouvernance & Management",
        "partie": "62443-2-1",
        "dit": "Ce qui n’a pas de propriétaire ne se maintient pas. Cette "
               "section est la première parce que les cinq autres s’écroulent "
               "sans elle : une architecture segmentée sans responsable "
               "redevient plate au premier projet pressé.",
        "points": [
            {
                "cle": "politique",
                "libelle": "Politique de sécurité OT définie et approuvée par "
                           "la direction",
                "rattachement": "62443-2-1",
                "preuve": "La politique elle-même, datée, et la trace de son "
                          "approbation par la direction — pas un projet de "
                          "document, pas une note de service.",
            },
            {
                "cle": "responsable",
                "libelle": "Responsable sécurité OT (CISO / OT Security "
                           "Manager) désigné",
                "rattachement": "62443-2-1",
                "preuve": "La lettre de mission ou la fiche de poste, avec le "
                          "périmètre et le temps alloué. Un nom sans temps "
                          "dédié n’est pas une désignation.",
            },
            {
                "cle": "analyse_risque",
                "libelle": "Analyse de risque OT réalisée (conforme 62443-3-2)",
                "rattachement": "62443-3-2",
                "preuve": "Le rapport d’analyse : périmètre, scénarios, "
                          "cotation, et le niveau de sécurité cible retenu "
                          "par zone. C’est lui qui justifie le découpage.",
            },
            {
                "cle": "traitement_risque",
                "libelle": "Plan de traitement des risques (Risk Treatment "
                           "Plan) établi",
                "rattachement": "62443-3-2",
                "preuve": "Le plan, avec pour chaque risque la décision "
                          "prise — réduire, transférer, accepter — son "
                          "porteur et son échéance. Un risque accepté SANS "
                          "signature n’est pas accepté.",
            },
            {
                "cle": "incidents",
                "libelle": "Procédures de gestion des incidents OT documentées",
                "rattachement": "62443-2-1",
                "preuve": "La procédure, et la trace du dernier exercice ou "
                          "du dernier incident traité. Une procédure jamais "
                          "jouée se découvre pendant la crise.",
            },
        ],
    },
    {
        "cle": "architecture",
        "nom": "Architecture & Segmentation",
        "partie": "62443-3-2",
        "dit": "C’est ici que la série est la plus prescriptive, et c’est ici "
               "que le coût se décide. Un découpage en zones et conduits n’est "
               "pas un schéma réseau : c’est le résultat d’une analyse de "
               "risque, et il se défend exigence par exigence.",
        "points": [
            {
                "cle": "inventaire",
                "libelle": "Inventaire complet des actifs OT (automates, RTU, "
                           "IHM, réseaux)",
                "rattachement": "62443-2-1",
                "preuve": "L’inventaire, avec sa date de dernière mise à jour "
                          "et son mode d’obtention. CE POINT COMMANDE TOUS "
                          "LES AUTRES : on ne protège, ne segmente ni ne "
                          "corrige que ce qu’on a recensé.",
            },
            {
                "cle": "zones_conduits",
                "libelle": "Modèle Zones & Conduits défini et documenté",
                "rattachement": "62443-3-2",
                "preuve": "Le document de zonage : chaque zone, son niveau "
                          "cible, chaque conduit et ce qu’il transporte — "
                          "rattaché à l’analyse de risque qui le fonde.",
            },
            {
                "cle": "pare_feu",
                "libelle": "Pare-feu industriels déployés entre zones IT et OT",
                "rattachement": "62443-3-3",
                "preuve": "La configuration en vigueur et la date de la "
                          "dernière revue de règles. Un pare-feu dont "
                          "personne ne revoit les règles finit ouvert.",
            },
            {
                "cle": "dmz",
                "libelle": "DMZ industrielle configurée (si applicable)",
                "rattachement": "62443-3-3",
                "preuve": "Le schéma et les flux autorisés. « Si applicable » "
                          "veut dire que son absence se justifie aussi : "
                          "écrivez pourquoi il n’y en a pas.",
            },
            {
                "cle": "conduits",
                "libelle": "Conduits sécurisés avec chiffrement ou diodes de "
                           "données",
                "rattachement": "62443-3-3",
                "preuve": "Pour chaque conduit, le moyen retenu et sa raison. "
                          "Une diode et un tunnel chiffré ne répondent pas à "
                          "la même menace : l’une interdit le retour, l’autre "
                          "protège le transit.",
            },
        ],
    },
    {
        "cle": "acces",
        "nom": "Contrôles d’accès & Authentification",
        "partie": "62443-3-3",
        "dit": "Les deux premiers fondements de la 62443-3-3 — identification "
               "et contrôle d’usage. C’est la section où l’écart entre la "
               "politique écrite et le terrain est le plus fréquent : le "
               "compte partagé de l’astreinte survit à toutes les politiques.",
        "points": [
            {
                "cle": "mfa",
                "libelle": "Authentification forte sur les systèmes critiques "
                           "(MFA)",
                "rattachement": "62443-3-3",
                "preuve": "La liste des systèmes concernés et le moyen "
                          "employé. Le facteur doit tenir SANS lien avec "
                          "l’extérieur : un code par SMS ne s’atteint pas "
                          "dans une salle blindée.",
            },
            {
                "cle": "privileges",
                "libelle": "Gestion des comptes et privilèges (moindre "
                           "privilège)",
                "rattachement": "62443-3-3",
                "preuve": "La matrice des rôles et la dernière revue de "
                          "droits, avec ce qu’elle a retiré. Une revue qui ne "
                          "retire jamais rien n’a pas eu lieu.",
            },
            {
                "cle": "mots_de_passe",
                "libelle": "Mots de passe complexes et rotation régulière",
                "rattachement": "62443-3-3",
                "preuve": "La règle appliquée, et le moyen de la vérifier. "
                          "RÉSERVE : imposer une rotation courte pousse aux "
                          "mots de passe écrits près de l’écran — la "
                          "rotation se justifie sur compromission, pas par "
                          "principe.",
            },
            {
                "cle": "comptes_defaut",
                "libelle": "Désactivation des comptes par défaut (admin, "
                           "guest)",
                "rattachement": "62443-4-2",
                "preuve": "Le relevé par équipement. C’est une exigence de "
                          "COMPOSANT : elle se vérifie automate par automate, "
                          "pas au niveau du système.",
            },
            {
                "cle": "journalisation",
                "libelle": "Journalisation des accès et des modifications",
                "rattachement": "62443-3-3",
                "preuve": "Ce qui est journalisé, où, et combien de temps "
                          "c’est conservé. Un journal conservé sept jours ne "
                          "sert à rien : une intrusion se découvre en "
                          "moyenne bien plus tard.",
            },
        ],
    },
    {
        "cle": "protection",
        "nom": "Protection technique",
        "partie": "62443-3-3",
        "dit": "La section où les réflexes venus de l’informatique de gestion "
               "font le plus de dégâts. Un correctif s’applique quand le "
               "procédé le permet, un antivirus ne s’installe pas sur un "
               "automate, et une sauvegarde jamais restaurée n’est pas une "
               "sauvegarde.",
        "points": [
            {
                "cle": "antivirus",
                "libelle": "Antivirus / EDR sur les stations de travail OT",
                "rattachement": "62443-3-3",
                "preuve": "Le parc couvert ET la liste des exclusions "
                          "validées par l’éditeur du système de conduite. "
                          "Un agent non validé arrête la production plus "
                          "sûrement qu’une attaque.",
            },
            {
                "cle": "sauvegardes",
                "libelle": "Sauvegardes régulières et testées des "
                           "configurations",
                "rattachement": "62443-2-1",
                "preuve": "La date de la dernière RESTAURATION réussie, pas "
                          "celle de la dernière sauvegarde. C’est le seul "
                          "des deux qui prouve quelque chose.",
            },
            {
                "cle": "correctifs",
                "libelle": "Patch management : plan de mise à jour des "
                           "systèmes OT",
                "rattachement": "62443-2-3",
                "preuve": "Le plan, les fenêtres d’application, et les "
                          "mesures compensatoires pour ce qui NE PEUT PAS "
                          "être corrigé. Cette dernière colonne est la plus "
                          "importante en OT, et c’est celle qu’on omet.",
            },
            {
                "cle": "durcissement",
                "libelle": "Désactivation des ports et services non "
                           "nécessaires",
                "rattachement": "62443-4-2",
                "preuve": "Le relevé de configuration par type d’équipement, "
                          "et sa date. Exigence de composant, à vérifier sur "
                          "le matériel réel.",
            },
            {
                "cle": "chiffrement",
                "libelle": "Chiffrement des communications sensibles",
                "rattachement": "62443-3-3",
                "preuve": "Les flux concernés et le moyen. RÉSERVE : beaucoup "
                          "de protocoles industriels ne le supportent pas — "
                          "la réponse est alors le conduit, pas le protocole.",
            },
        ],
    },
    {
        "cle": "detection",
        "nom": "Monitoring & Détection",
        "partie": "62443-3-3",
        "dit": "Détecter suppose de savoir à quoi ressemble le normal. En OT "
               "c’est un avantage — le trafic y est répétitif — à condition "
               "d’avoir capturé cette normale avant l’incident, pas pendant.",
        "points": [
            {
                "cle": "ids",
                "libelle": "IDS / IPS déployé sur le réseau OT",
                "rattachement": "62443-3-3",
                "preuve": "Les points de capture et le mode. RÉSERVE : en "
                          "OT, la détection PASSIVE est la règle — un "
                          "équipement qui coupe un flux de conduite crée le "
                          "défaut qu’il devait prévenir.",
            },
            {
                "cle": "siem",
                "libelle": "SIEM ou plateforme de corrélation des journaux OT",
                "rattachement": "62443-2-1",
                "preuve": "Les sources réellement raccordées, et qui regarde. "
                          "Une plateforme sans destinataire nommé produit des "
                          "alertes que personne ne lit.",
            },
            {
                "cle": "anomalies",
                "libelle": "Détection d’anomalies de trafic industriel",
                "rattachement": "62443-3-3",
                "preuve": "La référence de trafic normal, sa date, et ce qui "
                          "déclenche son renouvellement. Une référence prise "
                          "après une modification de procédé ne vaut plus.",
            },
            {
                "cle": "veille",
                "libelle": "Veille cyber et renseignement sur les menaces ICS",
                "rattachement": "62443-2-1",
                "preuve": "Les sources suivies et la trace d’une décision "
                          "prise à partir d’elles. Une veille qui n’a jamais "
                          "rien déclenché est un abonnement, pas une veille.",
            },
        ],
    },
    {
        "cle": "fournisseurs",
        "nom": "Fournisseurs & chaîne d’approvisionnement",
        "partie": "62443-2-4",
        "dit": "La partie de la série qu’on découvre le plus tard, et celle "
               "qui se traite le plus tôt : une exigence absente du marché ne "
               "se rattrape pas après notification. C’est aussi la seule "
               "section où la série parle de NIVEAUX DE MATURITÉ — ceux du "
               "prestataire, ML 1 à 4, constatés sur son propre programme.",
        "points": [
            {
                "cle": "eval_fournisseurs",
                "libelle": "Évaluation de la sécurité des fournisseurs "
                           "(conforme 62443-2-4)",
                "rattachement": "62443-2-4",
                "preuve": "La grille d’évaluation employée et son résultat "
                          "par fournisseur. C’est ici, et seulement ici, "
                          "qu’un niveau de maturité se constate.",
            },
            {
                "cle": "clauses",
                "libelle": "Exigences de sécurité dans les contrats d’achat OT",
                "rattachement": "62443-2-4",
                "preuve": "Les clauses telles qu’elles figurent au marché — "
                          "accès distant, remise des preuves, réversibilité, "
                          "notification d’incident. Un cahier des charges "
                          "n’est pas un contrat.",
            },
            {
                "cle": "certification",
                "libelle": "Certification des composants (62443-4-2) si "
                           "disponible",
                "rattachement": "62443-4-2",
                "preuve": "Les attestations, avec leur PÉRIMÈTRE et leur "
                          "version : une certification porte sur une "
                          "référence et un millésime précis, pas sur une "
                          "gamme ni sur un fabricant.",
            },
        ],
    },
]

ORDRE_SECTIONS = [s["cle"] for s in SECTIONS]

# ── CE QUE LE COMPTE N’EST PAS ─────────────────────────────────────────────
# Écrit ici plutôt qu’en note de bas de page : c’est la phrase qui empêche le
# chiffre d’être cité pour autre chose que ce qu’il est.
REFUS_MATURITE = (
    "Ce compte n’est PAS un niveau de maturité ni un niveau de sécurité. "
    "La CEI 62443-2-4 définit des niveaux de maturité (ML 1 à 4) pour le "
    "programme d’un prestataire, et la 62443-3-3 des niveaux de sécurité "
    "(SL 1 à 4) par exigence et par zone. Les deux se constatent sur preuves, "
    "pour un périmètre donné, par une évaluation — jamais par un compte de "
    "cases. Cette liste sert à ne rien oublier avant un audit ; c’est utile, "
    "et c’est autre chose."
)

LECTURE_PREUVE = (
    "Une case cochée sans document derrière ne vaut rien : c’est la première "
    "chose qu’un auditeur demande. Chaque point dit donc ce qu’il faudra "
    "montrer."
)


def _points():
    for s in SECTIONS:
        for p in s["points"]:
            yield s, p


def referentiel():
    """La liste, prête pour une page."""
    return {
        "version": VERSION,
        "sections": SECTIONS,
        "ordre_sections": ORDRE_SECTIONS,
        "parties": PARTIES,
        "total": sum(len(s["points"]) for s in SECTIONS),
        "refus_maturite": REFUS_MATURITE,
        "lecture_preuve": LECTURE_PREUVE,
    }


def compter(coches=None):
    """Ce qui est coché, section par section. UN COMPTE, ET RIEN D’AUTRE.

    `coches` est la liste des clés de points cochés. Une clé inconnue est
    REFUSÉE plutôt qu’ignorée : une liste qui compte des points qui n’existent
    pas rendrait un total impossible à recouper.
    """
    # DÉFAUT CORRIGÉ : coches pouvait contenir autre chose que des chaînes
    # (un client de l'API poste ce qu'il veut). sorted() sur un ensemble
    # mêlant str et int lève déjà en Python 3 ; ", ".join() sur des int
    # lève aussi. Le refus motivé — celui-là même que cette fonction existe
    # pour rendre — se faisait donc court-circuiter par sa propre mise en
    # forme, remplacé par une erreur serveur générique. Normaliser à
    # l'entrée rend le refus capable de nommer n'importe quoi.
    vues = {str(x) for x in (coches or [])}
    connues = {p["cle"] for _, p in _points()}
    inconnues = sorted(vues - connues)
    if inconnues:
        return {"ok": False, "erreur": "points_inconnus",
                "message": "Point(s) inconnu(s) : %s." % ", ".join(inconnues),
                "connus": sorted(connues)}
    par_section = []
    for s in SECTIONS:
        faits = [p["cle"] for p in s["points"] if p["cle"] in vues]
        restants = [{"cle": p["cle"], "libelle": p["libelle"],
                     "preuve": p["preuve"], "rattachement": p["rattachement"]}
                    for p in s["points"] if p["cle"] not in vues]
        par_section.append({
            "cle": s["cle"], "nom": s["nom"], "partie": s["partie"],
            "faits": len(faits), "sur": len(s["points"]),
            "restants": restants,
        })
    total = sum(len(s["points"]) for s in SECTIONS)
    faits = len(vues)
    return {
        "ok": True, "version": VERSION,
        "faits": faits, "sur": total,
        "par_section": par_section,
        # LE POURCENTAGE EST PUBLIÉ, ET DÉSAMORCÉ DANS LA MÊME RÉPONSE. Le
        # taire ne l’empêcherait pas d’être recalculé de tête ; le nommer
        # « part des points cochés » et non « maturité » lui donne son sens.
        "part_cochee_pct": round(faits / total * 100.0, 1) if total else 0.0,
        "ce_que_ce_n_est_pas": REFUS_MATURITE,
        "lecture": _lecture(faits, total, par_section),
    }


def _lecture(faits, total, par_section):
    if faits == 0:
        return ("Rien n’est coché. Cette liste se remplit avec les documents "
                "sous les yeux, pas de mémoire : c’est le seul usage qui en "
                "vaut la peine.")
    creuses = [s for s in par_section if s["faits"] == 0]
    if creuses:
        return ("%d point(s) sur %d. %d section(s) ne portent AUCUN point "
                "coché — %s : c’est là que se trouve l’écart, pas dans le "
                "total." % (faits, total, len(creuses),
                            ", ".join(s["nom"] for s in creuses)))
    if faits == total:
        return ("Les %d points sont cochés. Reste à réunir les preuves : "
                "c’est cette liste-là qu’un auditeur parcourt, pas celle des "
                "cases." % total)
    return ("%d point(s) sur %d. Chaque point restant dit ce qu’il faudrait "
            "montrer pour le cocher." % (faits, total))


def _verifier():
    """LA LISTE DOIT RESTER RECOUPABLE, et chaque point défendable.

    Un point sans rattachement citerait la série sans s’y rattacher ; un point
    sans preuve serait une case décorative ; une clé en double ferait compter
    deux fois le même point sans que le total ne bouge.
    """
    cles = [p["cle"] for _, p in _points()]
    if len(cles) != len(set(cles)):
        doubles = sorted({c for c in cles if cles.count(c) > 1})
        raise RuntimeError(
            "checklist_62443 : clé de point en double (%s) — le compte ne "
            "serait plus recoupable" % ", ".join(doubles))
    if set(ORDRE_SECTIONS) != {s["cle"] for s in SECTIONS}:
        raise RuntimeError("checklist_62443 : l’ordre ne couvre pas les sections")
    for s in SECTIONS:
        if not s["points"]:
            raise RuntimeError("checklist_62443 : section %s sans point" % s["cle"])
        if len(s["dit"]) < 80:
            raise RuntimeError(
                "checklist_62443 : la section %s ne dit pas ce qui la "
                "distingue — sans cela elle n’est qu’un intertitre" % s["cle"])
        if s["partie"] not in PARTIES:
            raise RuntimeError("checklist_62443 : partie inconnue sur %s" % s["cle"])
        for p in s["points"]:
            for champ in ("libelle", "preuve", "rattachement"):
                if not str(p.get(champ, "")).strip():
                    raise RuntimeError("checklist_62443 : %s sans %s"
                                       % (p["cle"], champ))
            if len(p["preuve"]) < 40:
                raise RuntimeError(
                    "checklist_62443 : la preuve attendue pour %s est trop "
                    "courte pour être une preuve" % p["cle"])
            # LA GARDE NE PORTAIT QUE SUR LES SECTIONS. Un point pouvait
            # donc citer une partie non déclarée — « 62443-2-3 » l’a fait —
            # et la page l’aurait affichée sans savoir de quoi elle parle.
            if p["rattachement"] not in PARTIES:
                raise RuntimeError(
                    "checklist_62443 : %s cite « %s », qui n’est pas une "
                    "partie déclarée de la série" % (p["cle"], p["rattachement"]))

    # LE REFUS DOIT NOMMER CE QU’IL REFUSE. Réduit à « ceci est indicatif », il
    # ne protégerait plus de rien : c’est la confusion avec ML et SL qu’il a
    # pour objet d’empêcher.
    for mot in ("ML 1 à 4", "SL 1 à 4", "62443-2-4", "62443-3-3"):
        if mot not in REFUS_MATURITE:
            raise RuntimeError(
                "checklist_62443 : le refus ne nomme plus « %s » — il cesse "
                "d’empêcher la confusion qu’il vise" % mot)


_verifier()
