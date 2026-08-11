# -*- coding: utf-8 -*-
"""Le bordereau de transmission — ce qui doit voyager AVEC le document.

CE QUE CE MODULE RÉSOUT, ET CE N'EST PAS LE TÉLÉCHARGEMENT

Un document produit ici se lit correctement ici : la page dit à quelle phase on
est, quelle tolérance porte le chiffre, ce qui reste à produire, et pourquoi
telle valeur est provisoire. Le fichier, lui, part seul. Six semaines plus tard,
aux achats, une enveloppe d'avant-projet à ±30 % devient un budget ; à
l'exploitation, une valeur de conception devient une consigne ; en comité, un
ordre de grandeur devient un engagement. Personne n'a menti : le contexte est
simplement resté sur le site.

CE QUE LE BORDEREAU PORTE, DONC, EN PREMIÈRE PAGE

  · ce que le document EST — sa nature, sa phase, son indice, sa date ;
  · ce qu'il N'EST PAS — la phrase que le lecteur pressé doit croiser avant le
    premier chiffre, et la seule qui empêche l'erreur ci-dessus ;
  · ce que CETTE fonction-là doit savoir — les achats et l'exploitation ne se
    trompent pas de la même façon sur le même document ;
  · ce qui reste à produire — sans quoi un dossier incomplet se lit comme un
    dossier fini ;
  · à qui revenir — parce qu'un lecteur qui doute et n'a personne à appeler
    interprète.

RIEN DE NOMINATIF NE CIRCULE. Le destinataire est une FONCTION, jamais une
personne : « Achats / approvisionnement », pas un nom. Un document nominatif
entrerait au registre des traitements et sa conservation devrait être bornée —
pour un gain nul, la fonction disant déjà tout ce que le bordereau doit adapter.

CE MODULE NE TRANSMET RIEN. Il écrit le bordereau ; c'est le client qui remet le
fichier. Aucun envoi, aucun lien public, aucune copie conservée : ce qui ne
quitte pas la plateforme ne peut pas partir à la mauvaise adresse.
"""
import re
import time

VERSION = "2026-08-a"

# ── CE QUE CHAQUE DOCUMENT EST, ET N'EST PAS ───────────────────────────────
# `n_est_pas` porte les confusions RÉELLES, celles qui coûtent quelque chose —
# pas des précautions de style. Une réserve qui ne nomme pas l'erreur qu'elle
# prévient ne prévient rien : on la lit comme une formule et on passe.
NATURES = {
    "note_calcul": {
        "nom": "Note de calcul énergie, eau et carbone",
        "est": "un calcul déterministe conduit sur un profil DÉCLARÉ — puissance "
               "informatique, mode de refroidissement, pays — à la précision "
               "d'une étude, non d'une mesure.",
        "n_est_pas": [
            "un engagement de performance : le PUE, la consommation d'eau et "
            "l'intensité carbone dépendent de l'exploitation réelle, pas de la "
            "conception seule ;",
            "une mesure sur site : aucune valeur ici ne provient d'un relevé ;",
            "un devis : il ne porte ni prix ferme ni quantitatif de marché.",
        ],
        "reste": [
            "les relevés du site retenu, qui remplacent les hypothèses "
            "climatiques et de réseau ;",
            "les données constructeur des matériels effectivement retenus ;",
            "le contrat de fourniture d'électricité, qui fixe l'intensité "
            "carbone réellement imputable.",
        ],
    },
    "trajectoire": {
        "nom": "Trajectoire de décarbonation",
        "est": "un ordonnancement de leviers selon la hiérarchie éviter, "
               "réduire, substituer, puis compenser le résiduel — l'ordre des "
               "actions, avec ce que chacune suppose acquis.",
        "n_est_pas": [
            "un plan d'action budgété : aucun levier n'y porte de coût ni de "
            "délai d'exécution ;",
            "un engagement de neutralité : la compensation n'y clôt rien, elle "
            "ne traite que ce que les trois premiers rangs n'ont pas pu éviter ;",
            "un inventaire vérifié : les quantités viennent du calcul, pas d'une "
            "vérification par tierce partie.",
        ],
        "reste": [
            "l'inventaire du périmètre, avec son année de référence ;",
            "les facteurs d'émission propres au site et à ses contrats ;",
            "le chiffrage de chaque levier retenu, et son porteur.",
        ],
    },
    "etude_phase": {
        "nom": "Étude de phase — contenu attendu du dossier",
        "est": "la LISTE de ce que le dossier de cette phase doit contenir, "
               "avec les grandeurs que le moteur peut déjà verser et celles "
               "qu'il signale comme restant à produire.",
        "n_est_pas": [
            "le dossier lui-même : c'est ce qu'il faut écrire, pas ce qui est "
            "écrit ;",
            "un état d'avancement : rien ici ne dit ce qui est fait, seulement "
            "ce qui est dû ;",
            "une pièce opposable : aucune ligne de ce document n'engage tant "
            "qu'elle n'est pas reprise dans une pièce visée.",
        ],
        "reste": [
            "les pièces elles-mêmes, une par une, à leur indice ;",
            "le visa de la maîtrise d'œuvre sur celles qui viennent de "
            "l'entreprise.",
        ],
    },
    "piece": {
        "nom": "Pièce de dossier — brouillon",
        "est": "un BROUILLON de pièce, rédigé avec l'aide d'un modèle de "
               "langage sur des grandeurs issues d'un calcul déterministe.",
        "n_est_pas": [
            "une pièce visée : tant qu'un ingénieur ne l'a pas relue et "
            "validée, elle n'a que la valeur d'un projet de rédaction ;",
            "une pièce contractuelle : elle ne devient opposable qu'une fois "
            "citée dans un marché signé ;",
            "un document dont chaque phrase est vérifiée : les mentions "
            "« [à compléter] » marquent ce qui manque, et il faut les traiter "
            "avant toute diffusion large.",
        ],
        "reste": [
            "la relecture par un ingénieur, et le visa qui s'ensuit ;",
            "le remplacement de chaque « [à compléter] » ;",
            "l'attribution d'un indice de version.",
        ],
    },
    "strategie_dd": {
        "nom": "Stratégie de développement durable — livrable d'ouverture",
        "est": "le cadrage d'ouverture de l'étude, établi à partir des réponses "
               "au questionnaire client et de la méthode des quatre "
               "perspectives.",
        "n_est_pas": [
            "un audit : rien n'y est vérifié, ni sur pièces ni sur site — les "
            "constats reprennent ce que le client a déclaré au questionnaire ;",
            "une déclaration de performance extra-financière : elle n'a ni le "
            "périmètre ni la vérification qu'exige un rapport réglementaire ;",
            "un arbitrage : il éclaire la décision de la direction, il ne la "
            "prend pas.",
        ],
        "reste": [
            "les données réelles du site et de l'exploitation ;",
            "l'arbitrage de la direction sur les enjeux mis sous surveillance ;",
            "la révision annuelle, sans laquelle le cadrage se périme.",
        ],
    },
}

# ── À QUI, ET CE QUE CETTE FONCTION-LÀ DOIT SAVOIR ─────────────────────────
# LES MÊMES CHIFFRES NE TROMPENT PAS TOUT LE MONDE DE LA MÊME FAÇON. Un ordre
# de grandeur d'étude devient un budget aux achats, une consigne à
# l'exploitation, un engagement en comité. Chaque fonction porte donc SA mise en
# garde, et l'usage qu'elle ne doit pas faire du document.
#
# DES FONCTIONS, PAS DES PERSONNES : rien de nominatif ne circule, et il n'y a
# donc rien à borner en conservation ni à inscrire au registre des traitements.
DESTINATAIRES = {
    "direction": {
        "nom": "Direction ou comité d'investissement",
        "avant": "Les montants et les grandeurs de ce document sont des ordres "
                 "de grandeur d'étude, assortis d'une tolérance qui figure au "
                 "cartouche. Demandez cette tolérance AVANT d'arbitrer : un "
                 "chiffre d'avant-projet présenté sans elle engage l'entreprise "
                 "sur une précision qu'il n'a pas.",
        "pas": "Ne le citez pas comme une enveloppe budgétaire arrêtée.",
    },
    "achats": {
        "nom": "Achats et approvisionnement",
        "avant": "Les valeurs chiffrées sont des ordres de grandeur d'ÉTUDE, "
                 "établis sans consultation du marché. Elles servent à "
                 "dimensionner et à comparer, pas à négocier.",
        "pas": "Ne consultez pas de fournisseur sur ces valeurs : un objectif "
               "de prix bâti dessus est indéfendable en négociation et "
               "décrédibilise la consultation entière.",
    },
    "exploitation": {
        "nom": "Exploitation et maintenance",
        "avant": "Les valeurs sont des valeurs de CONCEPTION — ce que "
                 "l'installation doit pouvoir tenir —, pas des consignes de "
                 "conduite. Les consignes se règlent sur l'installation "
                 "réelle, après essais.",
        "pas": "Ne les reportez pas telles quelles dans une gamme de conduite "
               "ni dans un automate.",
    },
    "hse": {
        "nom": "HSE, environnement et développement durable",
        "avant": "Les grandeurs environnementales sont calculées à partir de "
                 "facteurs d'émission moyens et d'un profil déclaré. Un "
                 "reporting réglementaire exige des données mesurées, un "
                 "périmètre arrêté et une vérification.",
        "pas": "Ne les versez pas telles quelles à une déclaration "
               "réglementaire ni à un rapport de durabilité.",
    },
    "si": {
        "nom": "Direction des systèmes d'information ou SI industriel",
        "avant": "La puissance informatique est une ENTRÉE de l'étude, "
                 "déclarée par le projet. Le document en tire des conséquences "
                 "d'infrastructure ; il ne valide pas la capacité informatique "
                 "elle-même.",
        "pas": "Ne le lisez pas comme un engagement de capacité "
               "d'hébergement.",
    },
    "juridique": {
        "nom": "Juridique et contrats",
        "avant": "Aucune ligne de ce document n'est contractuelle. Elle ne le "
                 "devient qu'une fois reprise, mot pour mot, dans une pièce "
                 "annexée à un marché signé.",
        "pas": "Ne l'annexez pas à un contrat en l'état.",
    },
    "moe": {
        "nom": "Maîtrise d'œuvre ou bureau d'études extérieur",
        "avant": "Les hypothèses sont DÉCLARÉES, pas relevées. Confrontez-les "
                 "aux vôtres avant de vous en servir : deux études qui "
                 "divergent sur une hypothèse d'entrée divergeront sur tout le "
                 "reste, et l'écart se découvre au montage.",
        "pas": "Ne reprenez aucune grandeur sans avoir vérifié l'hypothèse "
               "qui la porte.",
    },
    "entreprise": {
        "nom": "Entreprise de travaux ou fournisseur",
        "avant": "Ce document n'est pas une pièce de consultation. Il n'a ni "
                 "le niveau de définition ni le caractère opposable d'un "
                 "dossier de consultation des entreprises.",
        "pas": "N'établissez aucun prix sur cette base : une offre bâtie "
               "dessus sera écartée, et le temps passé perdu.",
    },
    "interne": {
        "nom": "Équipe projet interne",
        "avant": "Le document circule dans son contexte d'origine. Vérifiez "
                 "surtout l'INDICE : une version antérieure qui continue de "
                 "circuler en parallèle est la cause la plus fréquente de "
                 "décisions prises sur des chiffres périmés.",
        "pas": "Ne le diffusez pas hors de l'équipe sans le bordereau qui "
               "l'accompagne.",
    },
}

# Ce que le bordereau ne porte pas, dit noir sur blanc — même discipline que
# pour le lien inter-sites : ce qui est promis doit pouvoir se vérifier.
EXCLUS = [
    "Aucun nom de personne, ni pour l'émetteur ni pour le destinataire : la "
    "transmission désigne des FONCTIONS.",
    "Aucune coordonnée, aucune adresse électronique, aucun numéro.",
    "Aucune copie n'est conservée par la plateforme : le document est produit, "
    "remis, et rien n'en subsiste côté serveur.",
]

# Un nom propre glissé dans un champ de fonction ferait entrer le document au
# registre des traitements sans que personne l'ait décidé. On refuse donc ce
# qui ressemble à une identité : une civilité, ou une adresse électronique.
#
# COMPARAISON DE MOTS, PAS EXPRESSION RÉGULIÈRE. La première version cherchait
# « \b(m\.|mme|…)\b ». Elle ne trouvait JAMAIS « M. Dupont » : après un point
# littéral, « \b » exige une lettre, et un point suivi d'une espace n'offre
# aucune frontière de mot. Le filtre passait donc à côté du cas le plus
# évident — celui-là même qu'il existait pour attraper — et il fallait ouvrir
# un document pour s'en apercevoir. Découper puis comparer ne se trompe pas.
_CIVILITES = {"m", "m.", "mme", "mme.", "mlle", "mlle.", "monsieur", "madame",
              "mesdames", "messieurs", "dr", "dr.", "pr", "pr.", "me",
              "maitre", "maître"}


def _a_civilite(texte):
    return any(mot in _CIVILITES
               for mot in re.split(r"[\s,;:/]+", str(texte or "").lower()))


def _verifier():
    fautes = []
    for cle, n in NATURES.items():
        for champ in ("nom", "est"):
            if not (n.get(champ) or "").strip():
                fautes.append("nature %s : %s manquant" % (cle, champ))
        if len(n.get("n_est_pas") or []) < 2:
            fautes.append("nature %s : il faut au moins deux confusions nommées"
                          % cle)
        if not n.get("reste"):
            fautes.append("nature %s : rien de ce qui reste a produire" % cle)
        for x in (n.get("n_est_pas") or []):
            # Une reserve trop courte est un slogan : elle ne nomme pas l'erreur
            # qu'elle previent, et se lit comme une formule de style.
            if len(x) < 60:
                fautes.append("nature %s : reserve trop breve — %r" % (cle, x))
    for cle, d in DESTINATAIRES.items():
        for champ in ("nom", "avant", "pas"):
            if not (d.get(champ) or "").strip():
                fautes.append("destinataire %s : %s manquant" % (cle, champ))
        if len(d.get("avant") or "") < 100:
            fautes.append("destinataire %s : mise en garde trop breve" % cle)
        if _a_civilite(d.get("nom")):
            fautes.append("destinataire %s : le vocabulaire designe des "
                          "fonctions, pas des personnes" % cle)
    if not EXCLUS:
        fautes.append("la liste de ce que le bordereau ne porte pas est vide")
    return fautes


_FAUTES = _verifier()
if _FAUTES:
    raise RuntimeError("transmission — vocabulaire incoherent : "
                       + " ; ".join(_FAUTES))


def nominatif(valeur):
    """Ce qui ressemble à une identité de personne, et qu'on refuse.

    Le champ attend une CLÉ de fonction ; on ne devine pas, on refuse. Un nom
    accepté « pour être serviable » ferait entrer le document au registre des
    traitements, et personne ne l'aurait décidé.
    """
    v = str(valeur or "").strip()
    if not v:
        return False
    if "@" in v:
        return True
    return _a_civilite(v)


def destinataires():
    """Le vocabulaire, prêt pour la page."""
    return [{"cle": k, "nom": v["nom"], "avant": v["avant"], "pas": v["pas"]}
            for k, v in DESTINATAIRES.items()]


def natures():
    return [{"cle": k, "nom": v["nom"]} for k, v in NATURES.items()]


def bordereau(nature, destinataire, contexte=None):
    """Le bordereau, en Markdown, prêt à être posé en tête du document.

    Rend TOUJOURS un résultat lisible : une nature ou un destinataire inconnus
    ne font pas échouer l'export — ils sortent, et ils sont NOMMÉS. Un export
    qui échoue parce qu'une clé a changé prive le client de son document ; un
    bordereau qui tombe en silence le lui rend sans ses réserves, ce qui est
    pire.
    """
    contexte = dict(contexte or {})
    refuses = []

    n = NATURES.get(str(nature or "").strip())
    if n is None:
        refuses.append({"champ": "nature", "valeur": str(nature)[:40],
                        "motif": "nature de document inconnue — le bordereau "
                                 "ne peut pas dire ce que le document n'est pas"})
    d = DESTINATAIRES.get(str(destinataire or "").strip())
    if d is None and destinataire:
        refuses.append({"champ": "destinataire", "valeur": str(destinataire)[:40],
                        "motif": "fonction destinataire inconnue"})

    if n is None:
        return {"markdown": "", "refuses": refuses, "nature": None,
                "destinataire": (d or {}).get("nom"), "exclus": EXCLUS}

    L = []
    A = L.append
    A("## Bordereau de transmission")
    A("")
    A("| | |")
    A("|---|---|")
    if d:
        A("| Transmis à | **%s** |" % d["nom"])
    A("| Nature du document | %s |" % n["nom"])
    for cle, lib in (("phase", "Phase du projet"), ("indice", "Indice"),
                     ("client", "Client / organisation"),
                     ("perimetre", "Périmètre")):
        v = str(contexte.get(cle) or "").strip()
        if v:
            A("| %s | %s |" % (lib, v))
    A("| Date de transmission | %s |"
      % (contexte.get("date") or time.strftime("%d/%m/%Y")))
    A("")
    A("**Ce que ce document est.** Il porte %s" % n["est"])
    A("")
    A("**Ce qu'il n'est pas.** Lisez ces trois lignes avant le premier chiffre.")
    for x in n["n_est_pas"]:
        A("- %s" % x)
    A("")
    if d:
        A("**À savoir avant de le lire — %s.** %s" % (d["nom"], d["avant"]))
        A("")
        A("> %s" % d["pas"])
        A("")
    A("**Ce qui reste à produire.** Tant que ces points ne sont pas traités, le "
      "dossier n'est pas complet — et un dossier incomplet se lit comme un "
      "dossier fini.")
    for x in n["reste"]:
        A("- %s" % x)
    A("")
    A("**En cas de doute, revenez vers l'émetteur de l'étude** plutôt que "
      "d'interpréter. Une hypothèse mal reprise ne se voit qu'au résultat, et "
      "trop tard pour être corrigée sans coût.")
    A("")
    if refuses:
        A("**Réserve sur ce bordereau.** " + " ".join(
            "%s : %s." % (x["champ"], x["motif"]) for x in refuses))
        A("")
    A("---")
    A("")

    return {"markdown": "\n".join(L), "refuses": refuses,
            "nature": n["nom"], "destinataire": (d or {}).get("nom"),
            "exclus": EXCLUS, "version": VERSION}


def poser(md, nature, destinataire, contexte=None):
    """Le document, précédé de son bordereau — ou tel quel si rien n'est demandé.

    Le bordereau se pose EN TÊTE et non en annexe : une réserve qu'on ne
    rencontre qu'après avoir lu les chiffres arrive après la conclusion que le
    lecteur a déjà tirée.
    """
    if not destinataire:
        return md, None
    b = bordereau(nature, destinataire, contexte)
    if not b["markdown"]:
        return md, b
    return b["markdown"] + (md or ""), b


def sante():
    return {"module": "transmission", "version": VERSION,
            "natures": len(NATURES), "destinataires": len(DESTINATAIRES),
            "problemes": _verifier()}
