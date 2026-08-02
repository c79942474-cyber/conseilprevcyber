# -*- coding: utf-8 -*-
"""Playbook contractuel et détection d'écarts — relecture assistée des contrats.

CE QUE CE MODULE FAIT, ET SURTOUT CE QU'IL NE FAIT PAS
══════════════════════════════════════════════════════

Une équipe juridique qui relit la cinquième version d'un contrat a besoin d'une
réponse à une question simple : « qu'est-ce qui a bougé depuis la version
précédente, et est-ce que ça reste dans nos clous ? ». Cette réponse doit être
IDENTIQUE d'une relecture à l'autre pour le même texte — sinon elle n'est pas
opposable en interne, et le juriste la refait à la main.

C'est pourquoi le verdict est rendu ici, en Python, par des règles écrites et
lisibles : présence du sujet, marqueurs de rédaction défavorable, seuils
chiffrés comparés à la position interne. Le même contrat donne le même verdict,
aujourd'hui et dans six mois, avec ou sans réseau, avec ou sans clé d'API.

Le modèle de langage intervient APRÈS, et seulement pour ce qu'il fait bien :
expliquer un écart en français clair, rédiger une contre-proposition à partir de
la position de repli, répondre aux questions du relecteur. Il reçoit les verdicts
comme des faits et il lui est interdit de les contredire. Un modèle qui déciderait
seul qu'une clause est « conforme » produirait un texte parfaitement crédible et
parfaitement invérifiable : sur un contrat, c'est un risque, pas un service.

TROIS GARDE-FOUS
────────────────
1. Un thème sans règle de détection n'est jamais « conforme » : il ressort
   « non outillé — à relire à la main ». Le silence ne vaut pas approbation.
2. Le verdict cite toujours l'article du contrat sur lequel il se fonde, avec
   la phrase exacte qui a déclenché la règle. Un écart sans citation ne serait
   pas vérifiable.
3. Rien n'est conservé. Un contrat en cours de négociation est une pièce
   sensible ; l'analyse se fait en mémoire et le texte repart avec la réponse.
"""

import re
import unicodedata

import juridique

VERSION_PLAYBOOK = "2026.08"

# ═══════════════════════════════════════════════════════════════════════════
# 1. LES NIVEAUX — l'échelle de lecture, du meilleur au pire
# ═══════════════════════════════════════════════════════════════════════════
#
# Le rang sert à comparer deux versions : un thème qui passe du rang 1 au rang 3
# a reculé, et c'est cela qu'on veut voir sans relire les deux textes.

NIVEAUX = [
    {"id": "conforme", "rang": 0, "ton": "bon",
     "libelle": "Conforme au standard",
     "sens": "La rédaction correspond à la position interne. Rien à négocier."},
    {"id": "repli", "rang": 1, "ton": "bon",
     "libelle": "Repli accepté d'avance",
     "sens": "S'écarte du standard, mais dans une limite prévue par le playbook : "
             "le relecteur peut accepter sans remonter, en tracant la décision."},
    {"id": "ecart", "rang": 2, "ton": "moyen",
     "libelle": "Écart à faire valider",
     "sens": "Sort des limites prévues. La validation d'une instance nommée est "
             "requise avant d'accepter."},
    {"id": "absent", "rang": 3, "ton": "moyen",
     "libelle": "Sujet non traité",
     "sens": "Aucune clause du contrat ne traite ce sujet. Le silence joue "
             "rarement en faveur du client."},
    {"id": "non-outille", "rang": 4, "ton": "neutre",
     "libelle": "Non outillé — relecture humaine",
     "sens": "Ce thème n'a pas de règle de détection automatique. Il n'est ni "
             "validé ni invalidé : il doit être relu à la main."},
    {"id": "ligne-rouge", "rang": 5, "ton": "mauvais",
     "libelle": "Ligne rouge",
     "sens": "Rédaction que la politique interne exclut de signer. La remontée "
             "n'est pas une option, c'est une obligation."},
]

_RANG = {n["id"]: n["rang"] for n in NIVEAUX}
_NIVEAU = {n["id"]: n for n in NIVEAUX}


def niveaux():
    return [dict(n) for n in NIVEAUX]


# ═══════════════════════════════════════════════════════════════════════════
# 2. NORMALISATION ET DÉCOUPAGE
# ═══════════════════════════════════════════════════════════════════════════
#
# Tous les motifs sont écrits SANS accent et en minuscules, et le texte du
# contrat est ramené dans la même forme avant comparaison. Sans cela, chaque
# motif devrait porter ses variantes (« délai » / « delai » / « DÉLAI ») et
# finirait par en oublier une.

def _plat(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace(" ", " ").replace(" ", " ")
    s = s.replace("–", "-").replace("—", "-").replace("‑", "-")
    return re.sub(r"\s+", " ", s.lower()).strip()


# Un article de contrat commence presque toujours par « Article n », « n.n » ou
# une numérotation en tête de ligne. On découpe là-dessus, et à défaut sur les
# paragraphes : le but est de rattacher chaque verdict à un endroit précis du
# texte, pas de reconstituer une table des matières.
_RE_TITRE = re.compile(
    r"^\s*(?:(?:article|art\.?|clause|annexe)\s*)?"
    r"(\d{1,2}(?:\.\d{1,2}){0,3})\s*[\).:\-–—]?\s*(.{0,90})$",
    re.I)
_RE_ARTICLE_SEUL = re.compile(r"^\s*(?:article|clause|annexe)\s+([IVXLC\d]{1,6})\b(.{0,90})$", re.I)


def decouper(texte):
    """Découpe le contrat en articles. Renvoie [{ref, titre, texte, debut}]."""
    lignes = str(texte or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    segments, courant = [], None
    for i, ligne in enumerate(lignes):
        m = _RE_TITRE.match(ligne) or _RE_ARTICLE_SEUL.match(ligne)
        # Un titre est une ligne courte : « 12.3 Responsabilité » en est un,
        # « 12.3 % des sommes versées au titre de… » n'en est pas un.
        titre_probable = bool(m) and len(ligne.strip()) <= 110
        if titre_probable:
            if courant:
                segments.append(courant)
            courant = {"ref": m.group(1).strip(),
                       "titre": (m.group(2) or "").strip(" .:-–—"),
                       "lignes": [ligne.strip()], "debut": i}
        elif courant is not None:
            courant["lignes"].append(ligne)
        elif ligne.strip():
            courant = {"ref": "", "titre": "Préambule", "lignes": [ligne], "debut": i}
    if courant:
        segments.append(courant)

    out = []
    for s in segments:
        t = "\n".join(s["lignes"]).strip()
        if not t:
            continue
        out.append({"ref": s["ref"], "titre": s["titre"], "texte": t,
                    "debut": s["debut"], "plat": _plat(t)})
    # Un contrat collé sans numérotation ne doit pas donner un seul bloc de
    # 60 000 caractères : on retombe alors sur les paragraphes.
    if len(out) <= 1 and len(str(texte or "")) > 1500:
        out = []
        for i, par in enumerate(re.split(r"\n\s*\n", str(texte))):
            par = par.strip()
            if len(par) > 40:
                out.append({"ref": "", "titre": "Paragraphe %d" % (i + 1),
                            "texte": par, "debut": i, "plat": _plat(par)})
    return out


def _citer(segment, motif_trouve, large=190):
    """La phrase qui a déclenché la règle, telle qu'elle est écrite au contrat."""
    brut = segment["texte"]
    pos = _plat(brut).find(motif_trouve[:60]) if motif_trouve else -1
    if pos < 0:
        return brut[:large].strip() + ("…" if len(brut) > large else "")
    # L'index du texte aplati n'est pas celui du texte d'origine (accents,
    # espaces) : on se replace au mot le plus proche plutôt que de couper faux.
    mots = motif_trouve.split()
    ancre = mots[0] if mots else ""
    p = brut.lower().find(ancre[:18]) if ancre else -1
    if p < 0:
        p = 0
    d = max(0, p - 60)
    f = min(len(brut), p + large)
    return ("… " if d else "") + brut[d:f].strip() + ("…" if f < len(brut) else "")


# ═══════════════════════════════════════════════════════════════════════════
# 3. LES NOMBRES — un seuil ne se lit pas « à peu près »
# ═══════════════════════════════════════════════════════════════════════════

_MOTS_NB = {
    "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6,
    "sept": 7, "huit": 8, "neuf": 9, "dix": 10, "onze": 11, "douze": 12,
    "quinze": 15, "vingt": 20, "vingt-quatre": 24, "trente": 30, "trente-six": 36,
    "quarante-huit": 48, "soixante": 60, "soixante-douze": 72, "quatre-vingt-dix": 90,
}
_NB = r"(\d{1,4}(?:[.,]\d{1,2})?|" + "|".join(sorted(_MOTS_NB, key=len, reverse=True)) + r")"

_EN_HEURES = {"heure": 1.0, "heures": 1.0, "h": 1.0,
              "jour": 24.0, "jours": 24.0, "jour ouvre": 24.0, "jours ouvres": 24.0,
              "semaine": 168.0, "semaines": 168.0, "mois": 720.0, "an": 8760.0, "ans": 8760.0}
_EN_MOIS = {"mois": 1.0, "an": 12.0, "ans": 12.0, "annee": 12.0, "annees": 12.0,
            "jour": 1 / 30.0, "jours": 1 / 30.0, "semaine": 0.25, "semaines": 0.25}


def _nombre(s):
    s = str(s or "").strip().lower()
    if s in _MOTS_NB:
        return float(_MOTS_NB[s])
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def _convertir(valeur, unite, echelle):
    table = {"heures": _EN_HEURES, "mois": _EN_MOIS}.get(echelle, {})
    facteur = table.get(str(unite or "").strip())
    if facteur is None:
        facteur = table.get(str(unite or "").strip().rstrip("s"))
    return None if facteur is None else valeur * facteur


# ═══════════════════════════════════════════════════════════════════════════
# 4. LE PLAYBOOK
# ═══════════════════════════════════════════════════════════════════════════
#
# Une entrée par thème du clausier (juridique.CLAUSIER), qui reste la source
# unique de la clause modèle : la position standard N'EST PAS recopiée ici, elle
# est lue depuis le clausier. Deux copies d'une clause type divergent toujours.
#
# Ce qui s'ajoute ici est ce que le clausier ne dit pas :
#   replis      — jusqu'où on peut céder, et qui doit le dire
#   ligne_rouge — ce qu'on ne signe pas
#   presence    — comment reconnaître que le sujet est traité
#   rouge       — les rédactions qui déclenchent la ligne rouge
#   alerte      — les rédactions défavorables, avec leur niveau
#   seuil       — le chiffre à comparer, quand le sujet en porte un
#
# `valide` nomme l'instance (juridique.INSTANCES) qui tranche selon le niveau.

PLAYBOOK = {

    "perimetre-securite": {
        "replis": [
            {"texte": "Périmètre décrit dans une annexe technique révisable par avenant "
                      "simple, sans réévaluation formelle des risques.",
             "niveau": "repli"},
            {"texte": "Périmètre décrit dans le corps du contrat sans annexe, si les "
                      "systèmes et interfaces y sont nommés un par un.",
             "niveau": "repli"},
        ],
        "ligne_rouge": "Périmètre défini par renvoi à un document unilatéralement "
                       "modifiable par le prestataire (« documentation en vigueur »).",
        "presence": [r"perimetre", r"systemes couverts", r"champ d'application",
                     r"prestations couvertes"],
        "rouge": [
            {"motif": r"perimetre .{0,60}(?:defini|decrit|precise) .{0,40}"
                      r"(?:documentation|politique|referentiel) (?:du|de la) prestataire",
             "pourquoi": "Le périmètre devient modifiable par une seule des parties."},
            {"motif": r"(?:documentation|conditions) (?:en vigueur|applicables) "
                      r".{0,40}(?:susceptible|peuvent etre) (?:d'evoluer|modifiees) "
                      r"(?:a tout moment|unilateralement)",
             "pourquoi": "Le contenu de l'engagement peut changer sans votre accord."},
        ],
        "alerte": [
            {"motif": r"perimetre .{0,80}(?:indicatif|non exhaustif|a titre d'exemple)",
             "niveau": "ecart",
             "pourquoi": "Un périmètre « indicatif » ne permet de constater aucun manquement."},
            {"motif": r"(?:le prestataire|il) (?:peut|pourra) (?:modifier|faire evoluer) "
                      r".{0,40}perimetre",
             "niveau": "ecart",
             "pourquoi": "L'évolution du périmètre échappe à l'avenant."},
        ],
        "valide": {"repli": "metier", "ecart": "direction-juridique",
                   "absent": "direction-juridique", "ligne-rouge": "direction-juridique"},
    },

    "mesures-techniques": {
        "replis": [
            {"texte": "Renvoi à une annexe sécurité contractuelle listant les mesures, "
                      "sans mention explicite du caractère plancher.", "niveau": "repli"},
            {"texte": "Renvoi à une certification en cours de validité (ISO 27001, "
                      "SecNumCloud) DOUBLÉ d'une annexe des mesures propres au service.",
             "niveau": "repli"},
        ],
        "ligne_rouge": "Engagement limité à « l'état de l'art » ou aux « mesures "
                       "raisonnables », sans annexe opposable.",
        "presence": [r"mesures (?:techniques|de securite)", r"annexe securite",
                     r"exigences de securite", r"politique de securite"],
        "rouge": [
            {"motif": r"(?:etat de l'art|regles de l'art|mesures raisonnables|"
                      r"meilleurs efforts).{0,120}$",
             "pourquoi": "Formule inexploitable en contentieux : elle ne permet ni de "
                         "constater un manquement ni de le chiffrer.",
             "sauf": [r"annexe", r"a minima", r"au minimum", r"liste"]},
        ],
        "alerte": [
            {"motif": r"(?:le prestataire|il) (?:peut|pourra|se reserve).{0,60}"
                      r"(?:modifier|adapter|faire evoluer).{0,60}mesures",
             "niveau": "ecart",
             "pourquoi": "Les mesures peuvent être revues à la baisse sans votre accord."},
            {"motif": r"mesures .{0,50}(?:decrites|figurant).{0,40}"
                      r"(?:site (?:web|internet)|documentation en ligne)",
             "niveau": "ecart",
             "pourquoi": "Un engagement hébergé sur un site est modifiable sans trace."},
        ],
        "valide": {"repli": "rssi", "ecart": "rssi",
                   "absent": "rssi", "ligne-rouge": "direction-juridique"},
    },

    "notification-incident": {
        "replis": [
            {"texte": "Notification sous 12 heures si le contrat prévoit une astreinte "
                      "24/7 et un canal d'alerte nommé.", "niveau": "repli"},
            {"texte": "Notification sous 24 heures pour les seuls services non critiques "
                      "identifiés en annexe.", "niveau": "ecart"},
        ],
        "ligne_rouge": "Notification au-delà de 48 heures, ou subordonnée à la "
                       "qualification de l'incident par le prestataire.",
        "presence": [r"notification.{0,40}incident", r"incident de securite",
                     r"informe le client.{0,60}incident", r"violation de donnees"],
        "rouge": [
            {"motif": r"(?:apres|une fois|des lors que).{0,50}"
                      r"(?:qualification|analyse|confirmation).{0,50}par le prestataire",
             "pourquoi": "Le point de départ du délai est laissé au prestataire : le "
                         "délai devient illimité en pratique."},
        ],
        "alerte": [
            {"motif": r"dans (?:les )?meilleurs delais(?!.{0,60}au plus tard)",
             "niveau": "ecart",
             "pourquoi": "« Meilleurs délais » sans délai chiffré n'est pas opposable, "
                         "alors que NIS 2 vous impose une alerte sous 24 h."},
            {"motif": r"jours? ouvre",
             "niveau": "ecart",
             "pourquoi": "Un délai en jours ouvrés fait tomber un incident du vendredi "
                         "soir hors délai réglementaire."},
        ],
        "seuil": {
            "cle": "delai-notification", "libelle": "Délai de notification d'un incident",
            "motif": r"(?:au plus tard|dans un delai(?: maximal)? de|sous|dans les|"
                     r"dans un delai de)\s+" + _NB + r"\s*(heures?|jours?|h\b|"
                     r"jours? ouvres?|semaines?)",
            "echelle": "heures", "sens": "max",
            "standard": 8, "tolere": 24, "rouge_au_dela": 48,
            "unite_affichee": "heures",
            "pourquoi": "Une alerte précoce est due sous 24 h au titre de NIS 2 et une "
                        "notification sous 72 h au titre du RGPD. Un délai fournisseur "
                        "supérieur à 24 h rend ces obligations matériellement intenables.",
        },
        "valide": {"repli": "rssi", "ecart": "direction-juridique",
                   "absent": "rssi", "ligne-rouge": "direction-juridique"},
    },

    "cooperation-crise": {
        "replis": [
            {"texte": "Coopération engagée sans participation nommée aux cellules de "
                      "crise, si la mise à disposition des moyens techniques est écrite.",
             "niveau": "repli"},
            {"texte": "Conservation des preuves ramenée à 6 mois pour les services "
                      "hors périmètre réglementé.", "niveau": "repli"},
        ],
        "ligne_rouge": "Coopération facturée en régie sans plafond, ou droit du "
                       "prestataire de restaurer les systèmes avant investigation.",
        "presence": [r"cooperation", r"cellule de crise", r"gestion de crise",
                     r"preservation des preuves", r"investigation"],
        "rouge": [
            {"motif": r"(?:le prestataire|il).{0,60}(?:retablir|restaurer|reinstaller)"
                      r".{0,80}(?:sans|avant).{0,40}(?:accord|investigation|analyse)",
             "pourquoi": "Restaurer avant investigation détruit les preuves nécessaires "
                         "à la qualification de l'incident et à sa notification."},
        ],
        "alerte": [
            {"motif": r"(?:assistance|cooperation|concours).{0,60}"
                      r"(?:facturee|au tarif|en regie|sur devis)",
             "niveau": "ecart",
             "pourquoi": "L'assistance de crise devient une négociation commerciale au "
                         "pire moment."},
        ],
        "valide": {"repli": "rssi", "ecart": "rssi",
                   "absent": "rssi", "ligne-rouge": "direction-juridique"},
    },

    "audit": {
        "replis": [
            {"texte": "Un audit sur place par an, illimité en cas d'incident, avec "
                      "préavis de 30 jours ouvrés.", "niveau": "repli"},
            {"texte": "Audit délégué à un tiers indépendant accepté par les deux "
                      "parties, avec rapport intégral communiqué au client.",
             "niveau": "repli"},
        ],
        "ligne_rouge": "Droit d'audit limité à la remise d'un certificat ou d'un "
                       "rapport de certification, ou exclusion des autorités.",
        "presence": [r"audit", r"inspection", r"droit de controle", r"verification"],
        "rouge": [
            {"motif": r"(?:limite|restreint|se limite).{0,80}"
                      r"(?:certificat|rapport de certification|attestation)",
             "pourquoi": "Une clause limitée à un certificat ne satisfait ni l'art. "
                         "28.3.h du RGPD ni l'art. 30.3.e de DORA."},
            {"motif": r"(?:exclu|ne (?:peut|pourra) etre|refuse).{0,60}"
                      r"(?:autorite|regulateur|acpr|cnil|anssi)",
             "pourquoi": "Le droit d'inspection du régulateur ne se négocie pas."},
        ],
        "alerte": [
            {"motif": r"audit.{0,80}(?:aux frais (?:exclusifs )?du client|"
                      r"a la charge du client)",
             "niveau": "repli",
             "pourquoi": "Frais d'audit à votre charge : acceptable si le nombre "
                         "d'audits est garanti, coûteux sinon."},
            # Le préavis n'est PAS traité ici : c'est un chiffre, et il est comparé
            # par le seuil ci-dessous. Une règle textuelle doublant un seuil finit
            # toujours par le contredire — celle qui était écrite ici prenait
            # « préavis de 15 jours », parfaitement standard, pour un écart.
        ],
        "seuil": {
            "cle": "preavis-audit", "libelle": "Préavis avant audit sur place",
            "motif": r"preavis(?: (?:ecrit|minimal|prealable))?(?: de)?\s+" + _NB
                     + r"\s*(jours? ouvres?|jours?|semaines?|mois)",
            "echelle": "heures", "sens": "max",
            "standard": 360, "tolere": 720, "rouge_au_dela": 2160,
            "unite_affichee": "heures",
            "pourquoi": "Au-delà d'un mois de préavis, l'audit ne peut plus servir à "
                        "vérifier une situation en cours.",
        },
        "valide": {"repli": "direction-juridique", "ecart": "direction-juridique",
                   "absent": "direction-juridique", "ligne-rouge": "direction-juridique"},
    },

    "sous-traitance": {
        "replis": [
            {"texte": "Information préalable du client avec droit d'opposition motivé "
                      "dans un délai de 30 jours, au lieu de l'autorisation écrite.",
             "niveau": "repli"},
            {"texte": "Liste des sous-traitants en annexe, mise à jour notifiée, pour "
                      "les seuls sous-traitants sans accès aux données ni aux systèmes.",
             "niveau": "repli"},
        ],
        "ligne_rouge": "Liberté de sous-traiter sans information, ou absence de "
                       "répercussion des obligations de sécurité au sous-traitant.",
        "presence": [r"sous-trait", r"sous trait", r"prestataire secondaire",
                     r"chaine de fourniture"],
        "rouge": [
            {"motif": r"(?:libre|peut librement|sans (?:accord|autorisation|information))"
                      r".{0,60}sous-trait",
             "pourquoi": "Une sous-traitance libre vous fait perdre la maîtrise de la "
                         "chaîne, alors que la responsabilité reste la vôtre."},
        ],
        "alerte": [
            {"motif": r"sous-trait.{0,120}(?:informe|notifie).{0,60}posteriori",
             "niveau": "ecart",
             "pourquoi": "Une information a posteriori ne laisse aucune marge "
                         "d'opposition."},
            {"motif": r"(?:le prestataire )?(?:n'est pas|decline).{0,40}responsab"
                      r".{0,60}sous-trait",
             "niveau": "ecart",
             "pourquoi": "Le prestataire doit répondre de ses sous-traitants comme de "
                         "lui-même (RGPD art. 28.4)."},
        ],
        "valide": {"repli": "achats", "ecart": "direction-juridique",
                   "absent": "direction-juridique", "ligne-rouge": "direction-juridique"},
    },

    "localisation": {
        "replis": [
            {"texte": "Hébergement dans l'Union avec support depuis un pays tiers "
                      "adéquat, sans accès aux données en clair.", "niveau": "repli"},
            {"texte": "Transferts encadrés par des clauses contractuelles types avec "
                      "analyse d'impact des transferts communiquée au client.",
             "niveau": "ecart"},
        ],
        "ligne_rouge": "Transfert hors Union sans base légale identifiée, ou faculté "
                       "unilatérale de changer la localisation.",
        "presence": [r"localisation", r"heberg", r"pays tiers", r"transfert.{0,30}donnees",
                     r"lieu de traitement"],
        "rouge": [
            {"motif": r"(?:le prestataire|il).{0,60}(?:peut|pourra|se reserve)"
                      r".{0,60}(?:modifier|changer|deplacer).{0,60}"
                      r"(?:localisation|lieu|heberg)",
             "pourquoi": "La localisation devient une variable d'exploitation du "
                         "prestataire, alors qu'elle conditionne votre conformité."},
        ],
        "alerte": [
            {"motif": r"(?:etats-unis|hors (?:de l')?union|pays tiers)"
                      r"(?!.{0,140}(?:clauses contractuelles types|decision d'adequation|"
                      r"garanties appropriees))",
             "niveau": "ecart",
             # Une clause qui INTERDIT le transfert contient les mêmes mots que
             # celle qui l'autorise. Sans ce désamorçage, la meilleure rédaction
             # possible — « aucun transfert vers un pays tiers » — était signalée
             # comme un écart, ce qui est le plus sûr moyen de faire abandonner
             # l'outil au troisième contrat.
             "sauf": [r"aucun transfert", r"pays tiers n'est (?:pas )?autorise",
                      r"transfert.{0,30}(?:interdit|exclu|proscrit)",
                      r"exclusivement (?:au sein de|dans) l'union"],
             "pourquoi": "Transfert hors Union sans mention d'un encadrement : la base "
                         "légale doit être identifiée avant signature."},
        ],
        "valide": {"repli": "dpo", "ecart": "dpo",
                   "absent": "dpo", "ligne-rouge": "dpo"},
    },

    "acces-distant": {
        "replis": [
            {"texte": "Accès distant par le dispositif du prestataire si le client "
                      "conserve l'ouverture à la demande, la journalisation et "
                      "l'enregistrement de session.", "niveau": "repli"},
            {"texte": "Comptes de service partagés pour la supervision en lecture "
                      "seule, à l'exclusion de toute action d'écriture.", "niveau": "ecart"},
        ],
        "ligne_rouge": "Accès permanent, non nominatif ou non journalisé aux systèmes "
                       "industriels ; tunnel ouvert en continu vers l'extérieur.",
        "presence": [r"acces distant", r"telemaintenance", r"teleassistance",
                     r"prise en main a distance", r"acces a distance"],
        "rouge": [
            {"motif": r"acces.{0,60}(?:permanent|continu|en permanence|24 ?/ ?7)"
                      r"(?!.{0,80}(?:journalise|nominatif|a la demande))",
             "pourquoi": "Un accès permanent aux systèmes industriels est le vecteur "
                         "d'intrusion le plus fréquemment constaté."},
            {"motif": r"compte.{0,40}(?:partage|generique|commun)"
                      r"(?!.{0,60}lecture seule)",
             "pourquoi": "Un compte partagé rend impossible l'imputation d'une action, "
                         "donc l'investigation après incident."},
        ],
        "alerte": [
            {"motif": r"acces distant(?!.{0,220}(?:double facteur|multifacteur|mfa|"
                      r"deux facteurs|authentification forte))",
             "niveau": "ecart",
             "pourquoi": "Aucune authentification forte n'est exigée pour l'accès aux "
                         "systèmes industriels."},
        ],
        "valide": {"repli": "rssi", "ecart": "surete",
                   "absent": "surete", "ligne-rouge": "surete"},
    },

    "correctifs-ot": {
        "replis": [
            {"texte": "Délais de correction alignés sur les fenêtres d'arrêt "
                      "programmées, avec mesures compensatoires écrites dans l'intervalle.",
             "niveau": "repli"},
            {"texte": "Correctifs critiques sous 30 jours au lieu de 15, si une "
                      "analyse d'exposition est fournie.", "niveau": "repli"},
        ],
        "ligne_rouge": "Aucun engagement de délai, ou correctifs subordonnés à la "
                       "souscription d'un contrat de maintenance distinct.",
        "presence": [r"correctif", r"patch", r"mise a jour de securite", r"vulnerabilit"],
        "rouge": [
            {"motif": r"correctif.{0,80}(?:sous reserve|subordonne).{0,60}"
                      r"(?:contrat|souscription|option)",
             "pourquoi": "La sécurité devient une option payante alors que la "
                         "vulnérabilité existe déjà."},
        ],
        "alerte": [
            {"motif": r"correctif.{0,60}(?:selon|a la discretion|lorsque le prestataire"
                      r" (?:le )?juge)",
             "niveau": "ecart",
             "pourquoi": "Le rythme de correction dépend du seul prestataire."},
        ],
        "seuil": {
            "cle": "delai-correctif", "libelle": "Délai de correction d'une vulnérabilité critique",
            "motif": r"(?:critique|criticite (?:haute|elevee)|cvss)"
                     r".{0,80}?(?:sous|dans un delai(?: maximal)? de|au plus tard|"
                     r"dans les)\s+" + _NB + r"\s*(jours?|semaines?|mois|heures?)",
            "echelle": "heures", "sens": "max",
            "standard": 360, "tolere": 720, "rouge_au_dela": 2160,
            "unite_affichee": "heures",
            "pourquoi": "Au-delà de 30 jours sur une vulnérabilité critique exposée, "
                        "l'exploitation publique précède la correction.",
        },
        "valide": {"repli": "rssi", "ecart": "rssi",
                   "absent": "rssi", "ligne-rouge": "surete"},
    },

    "surete-securite": {
        "replis": [
            {"texte": "Priorité de la sûreté affirmée sans procédure d'arbitrage "
                      "détaillée, si l'exploitant conserve le dernier mot écrit.",
             "niveau": "repli"},
        ],
        "ligne_rouge": "Clause donnant au prestataire le pouvoir d'imposer une mesure "
                       "de cybersécurité contre l'avis de l'exploitant sur une "
                       "installation à risque.",
        "presence": [r"surete", r"safety", r"securite des personnes",
                     r"installation classee", r"seveso"],
        "rouge": [
            {"motif": r"(?:le prestataire|il).{0,60}(?:impose|decide seul|peut imposer)"
                      r".{0,80}(?:arret|mesure|intervention)",
             "pourquoi": "Sur une installation à risque, la décision d'exploitation "
                         "appartient à l'exploitant, qui en répond pénalement."},
        ],
        "alerte": [],
        "valide": {"repli": "surete", "ecart": "surete",
                   "absent": "surete", "ligne-rouge": "surete"},
    },

    "ia-fournisseur": {
        "replis": [
            {"texte": "Déclaration des systèmes d'IA en annexe avec engagement de "
                      "non-entraînement, sans obligation de notification préalable de "
                      "chaque nouvel usage.", "niveau": "repli"},
            {"texte": "Usage d'IA pour la seule assistance interne du prestataire, sans "
                      "accès aux données du client, sur déclaration écrite.",
             "niveau": "repli"},
        ],
        "ligne_rouge": "Droit d'utiliser les données du client pour entraîner des "
                       "modèles, ou silence complet sur l'usage de l'IA alors que le "
                       "service en comporte.",
        "presence": [r"intelligence artificielle", r"\bia\b", r"apprentissage automatique",
                     r"machine learning", r"modele de langage", r"systeme d'ia"],
        "rouge": [
            # `utilise\w{0,4}` et non `utilisees?` : le participe s'accorde avec ce
            # qui précède — « données utilisées », mais « contenus et données
            # traités peuvent être utilisés ». Une terminaison oubliée, et la
            # ligne rouge la plus grave du thème passait.
            {"motif": r"(?:donnees|contenus).{0,80}(?:peuvent|pourront|sont)"
                      r".{0,60}(?:utilis\w{0,4}|employ\w{0,4}|exploit\w{0,4}).{0,60}"
                      r"(?:entrainement|entrainer|amelioration des modeles|"
                      r"apprentissage)",
             "pourquoi": "Vos données alimentent un modèle dont vous ne maîtrisez ni le "
                         "périmètre ni les destinataires ultérieurs."},
            {"motif": r"(?:le prestataire|il).{0,40}(?:se reserve|dispose).{0,60}"
                      r"(?:droit|faculte).{0,60}(?:entrainer|entrainement)",
             "pourquoi": "Le droit d'entraînement sur vos données est réservé "
                         "explicitement."},
        ],
        "alerte": [
            {"motif": r"(?:intelligence artificielle|systeme d'ia)"
                      r"(?!.{0,250}(?:annexe|declare|liste|finalite))",
             "niveau": "ecart",
             "pourquoi": "L'IA est mentionnée sans que les systèmes employés soient "
                         "déclarés : l'AI Act vous impose pourtant de savoir ce qui "
                         "opère dans votre chaîne."},
        ],
        "valide": {"repli": "dpo", "ecart": "direction-juridique",
                   "absent": "direction-juridique", "ligne-rouge": "direction-juridique"},
    },

    "ia-responsabilites": {
        "replis": [
            {"texte": "Répartition des rôles AI Act décrite en annexe, sans "
                      "qualification nominative fournisseur / déployeur.",
             "niveau": "repli"},
        ],
        "ligne_rouge": "Clause faisant porter au client la qualité de fournisseur au "
                       "sens de l'AI Act sans lui en donner les moyens (documentation "
                       "technique, journaux, évaluation de conformité).",
        "presence": [r"ai act", r"reglement.{0,20}2024/1689", r"fournisseur.{0,30}"
                     r"(?:systeme d'ia|ia)", r"deployeur"],
        "rouge": [
            {"motif": r"(?:le client|celui-ci).{0,60}(?:est repute|assume|endosse)"
                      r".{0,60}(?:fournisseur|responsabilites du fournisseur)",
             "pourquoi": "Endosser la qualité de fournisseur sans la documentation "
                         "technique revient à assumer des obligations intenables."},
        ],
        "alerte": [
            {"motif": r"ai act(?!.{0,220}(?:annexe|documentation|journaux|"
                      r"evaluation de conformite))",
             "niveau": "ecart",
             "pourquoi": "L'AI Act est cité sans que les livrables associés soient dus."},
        ],
        "valide": {"repli": "direction-juridique", "ecart": "direction-juridique",
                   "absent": "direction-juridique", "ligne-rouge": "direction-juridique"},
    },

    "reversibilite": {
        "replis": [
            {"texte": "Assistance à la réversibilité de 3 mois, prolongeable une fois "
                      "sur demande écrite du client.", "niveau": "repli"},
            {"texte": "Réversibilité facturée au tarif convenu à l'avance et plafonnée, "
                      "si le format d'export est décrit.", "niveau": "repli"},
        ],
        "ligne_rouge": "Réversibilité au bon vouloir du prestataire, facturée sans "
                       "plafond, ou export dans un format propriétaire non documenté.",
        "presence": [r"reversibilite", r"restitution des donnees", r"migration",
                     r"fin de contrat", r"transferabilite"],
        "rouge": [
            {"motif": r"(?:restitution|reversibilite).{0,80}(?:sur devis|"
                      r"au tarif en vigueur|selon les conditions du prestataire)"
                      r"(?!.{0,60}plafond)",
             "pourquoi": "Le coût de sortie devient la véritable clause de "
                         "reconduction : il s'apprécie au moment où vous partez."},
            {"motif": r"format.{0,40}(?:proprietaire|specifique au prestataire)"
                      r"(?!.{0,80}documente)",
             "pourquoi": "Un export illisible ailleurs n'est pas une restitution."},
        ],
        "alerte": [
            {"motif": r"(?:suppression|effacement).{0,60}(?:immediate|des la fin|"
                      r"a l'expiration)(?!.{0,80}(?:apres|une fois).{0,40}restitution)",
             "niveau": "ecart",
             "pourquoi": "Les données peuvent être effacées avant que la restitution "
                         "soit constatée."},
        ],
        "seuil": {
            "cle": "duree-reversibilite", "libelle": "Durée de l'assistance à la réversibilité",
            "motif": r"(?:reversibilite|restitution|assistance a la migration)"
                     r".{0,110}?(?:pendant|durant|d'une duree de|sur)\s+" + _NB
                     + r"\s*(mois|semaines?|jours?|ans?|annees?)",
            "echelle": "mois", "sens": "min",
            "standard": 6, "tolere": 3, "rouge_au_dela": 1,
            "unite_affichee": "mois",
            "pourquoi": "Migrer un service industriel sous trois mois suppose une "
                        "préparation antérieure ; en dessous, la reprise se fait dans "
                        "l'urgence et à vos frais.",
        },
        "valide": {"repli": "dsi", "ecart": "direction-juridique",
                   "absent": "direction-juridique", "ligne-rouge": "direction-juridique"},
    },

    "continuite": {
        "replis": [
            {"texte": "Engagements de reprise (RTO/RPO) figurant dans l'annexe de "
                      "service sans test annuel contractualisé.", "niveau": "repli"},
            {"texte": "Test de continuité tous les deux ans, si le compte rendu du test "
                      "est communiqué au client.", "niveau": "repli"},
        ],
        "ligne_rouge": "Aucun objectif de reprise chiffré, ou exonération générale au "
                       "titre de la force majeure incluant la cyberattaque.",
        "presence": [r"continuite", r"reprise", r"\brto\b", r"\brpo\b", r"pca\b",
                     r"pra\b", r"plan de secours"],
        "rouge": [
            {"motif": r"force majeure.{0,120}(?:cyber|attaque informatique|"
                      r"rancongiciel|ransomware)",
             "pourquoi": "Qualifier la cyberattaque de force majeure vide de sa "
                         "substance l'obligation de sécurité elle-même."},
        ],
        "alerte": [
            {"motif": r"(?:rto|rpo|reprise).{0,60}(?:indicatif|objectif de moyens|"
                      r"a titre indicatif)",
             "niveau": "ecart",
             "pourquoi": "Un objectif de reprise indicatif n'ouvre droit à rien."},
        ],
        "valide": {"repli": "dsi", "ecart": "dsi",
                   "absent": "dsi", "ligne-rouge": "direction-juridique"},
    },

    "responsabilite": {
        "replis": [
            {"texte": "Plafond général à 1 fois les sommes des 12 derniers mois, "
                      "RELEVÉ à 3 fois pour les manquements à la sécurité et aux "
                      "données.", "niveau": "repli"},
            {"texte": "Plafond unique à 2 fois les sommes annuelles, sans plafond "
                      "spécifique, si les dommages liés aux données en sont exclus.",
             "niveau": "ecart"},
        ],
        "ligne_rouge": "Exclusion de responsabilité pour les manquements à la sécurité "
                       "ou à la protection des données ; exclusion de la faute lourde.",
        "presence": [r"responsabilite", r"plafond", r"limitation de responsabilite",
                     r"dommages"],
        "rouge": [
            {"motif": r"(?:exclut|decline|ne saurait etre tenu|aucune responsabilite)"
                      r".{0,110}(?:securite|violation de donnees|donnees personnelles|"
                      r"perte de donnees)",
             "pourquoi": "Exclure la responsabilité sécurité vide le contrat de sa "
                         "portée : il ne reste qu'une obligation sans sanction."},
            {"motif": r"(?:exclut|exclusion).{0,60}faute lourde",
             "pourquoi": "L'exclusion de la faute lourde est réputée non écrite en "
                         "droit français ; sa présence signale un texte non relu."},
        ],
        "alerte": [
            {"motif": r"(?:exclut|exclusion|aucun).{0,80}"
                      r"(?:dommages? indirects?|perte d'exploitation|perte de chiffre)"
                      r".{0,120}(?:perte de donnees|atteinte aux donnees)",
             "niveau": "ecart",
             "pourquoi": "Ranger la perte de données parmi les dommages indirects en "
                         "neutralise l'indemnisation."},
        ],
        "seuil": {
            "cle": "plafond-responsabilite", "libelle": "Plafond de responsabilité",
            "motif": r"plafonn?e?e?.{0,60}?" + _NB + r"\s*(?:\(\s*\d+\s*\)\s*)?"
                     r"(fois|x)\b",
            "echelle": None, "sens": "min",
            "standard": 3, "tolere": 1, "rouge_au_dela": 0.5,
            "unite_affichee": "fois les sommes annuelles",
            "pourquoi": "Un plafond inférieur au coût moyen d'un incident majeur "
                        "revient à faire porter le risque par le client, qui n'en "
                        "maîtrise pourtant pas la cause.",
        },
        "valide": {"repli": "direction-juridique", "ecart": "direction-generale",
                   "absent": "direction-juridique", "ligne-rouge": "direction-generale"},
    },

    "assurance": {
        "replis": [
            {"texte": "Attestation d'assurance fournie à la signature et sur demande, "
                      "au lieu d'un envoi annuel automatique.", "niveau": "repli"},
        ],
        "ligne_rouge": "Aucune assurance cyber, ou attestation non communicable.",
        "presence": [r"assurance", r"police d'assurance", r"attestation d'assurance",
                     r"garantie financiere"],
        "rouge": [],
        "alerte": [
            {"motif": r"assurance(?!.{0,200}(?:cyber|risques informatiques|"
                      r"responsabilite civile professionnelle))",
             "niveau": "repli",
             "pourquoi": "L'assurance mentionnée ne couvre pas explicitement le risque "
                         "cyber."},
        ],
        "valide": {"repli": "achats", "ecart": "direction-juridique",
                   "absent": "achats", "ligne-rouge": "direction-juridique"},
    },

    "certifications": {
        "replis": [
            {"texte": "Certification maintenue avec information du client en cas de "
                      "suspension, sans droit de résiliation associé.", "niveau": "repli"},
        ],
        "ligne_rouge": "Certification présentée comme un engagement alors qu'elle "
                       "couvre un autre périmètre que le service fourni.",
        "presence": [r"certification", r"iso ?/?(?:iec)? ?27001", r"secnumcloud",
                     r"hds\b", r"soc ?2", r"iec ?62443"],
        "rouge": [],
        "alerte": [
            {"motif": r"certification(?!.{0,200}(?:perimetre|portee|scope|maintien|"
                      r"validite))",
             "niveau": "repli",
             "pourquoi": "Une certification sans périmètre écrit peut couvrir un autre "
                         "service que le vôtre."},
            {"motif": r"(?:perte|suspension|retrait).{0,40}certification"
                      r"(?!.{0,120}(?:informe|notifie|resiliation))",
             "niveau": "ecart",
             "pourquoi": "Rien n'oblige le prestataire à vous prévenir s'il perd sa "
                         "certification."},
        ],
        "valide": {"repli": "rssi", "ecart": "rssi",
                   "absent": "achats", "ligne-rouge": "direction-juridique"},
    },

    "personnel": {
        "replis": [
            {"texte": "Engagement de confidentialité et habilitation des intervenants, "
                      "sans vérification d'antécédents formalisée.", "niveau": "repli"},
        ],
        "ligne_rouge": "Aucun engagement de confidentialité du personnel intervenant "
                       "sur les systèmes industriels.",
        "presence": [r"personnel", r"intervenants", r"confidentialite",
                     r"habilitation", r"salaries du prestataire"],
        "rouge": [],
        "alerte": [
            {"motif": r"confidentialite.{0,60}(?:pendant la duree du contrat)"
                      r"(?!.{0,80}(?:apres|au-dela|ans))",
             "niveau": "ecart",
             "pourquoi": "La confidentialité cesse à la fin du contrat, au moment "
                         "précis où le risque de divulgation augmente."},
        ],
        "valide": {"repli": "metier", "ecart": "direction-juridique",
                   "absent": "rssi", "ligne-rouge": "direction-juridique"},
    },

    "sbom": {
        "replis": [
            {"texte": "Inventaire des composants tiers fourni à la livraison et sur "
                      "demande, sans mise à jour automatique à chaque version.",
             "niveau": "repli"},
        ],
        "ligne_rouge": "Refus de communiquer la composition logicielle, y compris en "
                       "cas de vulnérabilité publiée touchant un composant.",
        "presence": [r"\bsbom\b", r"nomenclature logicielle", r"composition logicielle",
                     r"composants? (?:tiers|logiciels?)", r"bibliotheques? tierces?",
                     r"open source", r"logiciels? libres?"],
        "rouge": [
            {"motif": r"(?:refuse|ne (?:communique|fournit) pas|secret)"
                      r".{0,80}(?:composition|composants|sbom)",
             "pourquoi": "Sans composition logicielle, vous ne pouvez pas savoir si une "
                         "vulnérabilité publiée vous concerne."},
        ],
        "alerte": [],
        "valide": {"repli": "dsi", "ecart": "rssi",
                   "absent": "rssi", "ligne-rouge": "rssi"},
    },

    "donnees-usage": {
        "replis": [
            {"texte": "Usage des données agrégées et anonymisées pour l'amélioration du "
                      "service, sur information du client et avec droit d'opposition.",
             "niveau": "repli"},
        ],
        "ligne_rouge": "Droit d'usage des données du client à des fins propres au "
                       "prestataire, y compris statistiques, sans limite ni opposition.",
        "presence": [r"donnees du client", r"propriete des donnees", r"usage des donnees",
                     r"donnees d'usage", r"telemetrie"],
        "rouge": [
            {"motif": r"(?:le prestataire|il).{0,60}(?:peut|pourra|est autorise)"
                      r".{0,80}(?:utiliser|exploiter).{0,60}donnees"
                      r".{0,80}(?:fins? propres?|ses propres besoins|"
                      r"amelioration de ses (?:produits|services))"
                      r"(?!.{0,80}(?:anonymis|agreg))",
             "pourquoi": "Vos données deviennent un actif du prestataire sans "
                         "contrepartie ni contrôle."},
        ],
        "alerte": [],
        "valide": {"repli": "dpo", "ecart": "dpo",
                   "absent": "dpo", "ligne-rouge": "direction-juridique"},
    },

    "sla-securite": {
        "replis": [
            {"texte": "Indicateurs de sécurité mesurés et communiqués sans pénalité "
                      "associée, si le manquement répété ouvre droit à résiliation.",
             "niveau": "repli"},
        ],
        "ligne_rouge": "Pénalités constituant la réparation exclusive de tout "
                       "manquement à la sécurité.",
        "presence": [r"\bsla\b", r"niveau de service", r"penalites", r"indicateurs",
                     r"engagements de service"],
        "rouge": [
            {"motif": r"penalites?.{0,100}(?:seule|exclusive|unique).{0,60}"
                      r"(?:reparation|indemnisation|recours)",
             "pourquoi": "Des pénalités de quelques pour cent deviennent le prix "
                         "forfaitaire d'une fuite de données."},
        ],
        "alerte": [],
        "valide": {"repli": "metier", "ecart": "direction-juridique",
                   "absent": "dsi", "ligne-rouge": "direction-juridique"},
    },

    "changement-controle": {
        "replis": [
            {"texte": "Information du client en cas de changement de contrôle, avec "
                      "droit de résiliation ouvert pendant 3 mois.", "niveau": "repli"},
        ],
        "ligne_rouge": "Cession libre du contrat, y compris à un concurrent du client "
                       "ou à une entité hors Union.",
        # Un contrat titre rarement « changement de contrôle » : il titre
        # « Cession », et le corps dit « céder le présent contrat ». Les marqueurs
        # doivent suivre la langue des contrats, pas celle du playbook.
        "presence": [r"changement de controle", r"\bcession\b", r"\bceder\b",
                     r"\bcede\b", r"fusion", r"cessibilite", r"transfert du contrat"],
        "rouge": [
            {"motif": r"(?:peut|pourra) (?:librement )?ceder"
                      r"(?!.{0,120}(?:accord|information|prealable))",
             "pourquoi": "Votre cocontractant peut changer sans que vous puissiez "
                         "l'apprécier, alors que la confiance porte sur lui."},
        ],
        "alerte": [],
        "valide": {"repli": "achats", "ecart": "direction-juridique",
                   "absent": "achats", "ligne-rouge": "direction-juridique"},
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# 5. LE THÈME, VU DE L'EXTÉRIEUR
# ═══════════════════════════════════════════════════════════════════════════

_CLAUSE = {c["id"]: c for c in juridique.CLAUSIER}


def themes(domaine=None):
    """Le playbook complet, prêt à afficher. La position standard vient du
    clausier : une seule source pour la clause type."""
    out = []
    for c in juridique.CLAUSIER:
        if domaine and c["domaine"] != domaine:
            continue
        p = PLAYBOOK.get(c["id"])
        out.append({
            "id": c["id"], "titre": c["titre"], "domaine": c["domaine"],
            "criticite": c["criticite"], "fondement": list(c["fondement"]),
            "objectif": c["objectif"], "risque": c["risque"],
            "position": c["modele"],
            "replis": [dict(r) for r in (p or {}).get("replis", [])],
            "ligne_rouge": (p or {}).get("ligne_rouge", ""),
            "seuil": _seuil_public((p or {}).get("seuil")),
            "valide": dict((p or {}).get("valide", {})),
            "outille": bool(p and p.get("presence")),
        })
    return out


def _seuil_public(s):
    if not s:
        return None
    return {"libelle": s["libelle"], "sens": s["sens"], "standard": s["standard"],
            "tolere": s["tolere"], "rouge_au_dela": s["rouge_au_dela"],
            "unite": s["unite_affichee"], "pourquoi": s["pourquoi"]}


def domaines():
    return list(juridique.DOMAINES_CLAUSIER)


# ═══════════════════════════════════════════════════════════════════════════
# 6. LE MOTEUR — verdict par thème
# ═══════════════════════════════════════════════════════════════════════════

def _cherche(motifs, plat):
    for m in motifs or []:
        r = re.search(m, plat)
        if r:
            return r
    return None


def _segments_du_theme(regle, segments):
    """Les articles qui traitent le sujet. Restreindre la recherche à ces
    articles évite l'erreur classique de la lecture automatique : un « 48 heures »
    trouvé dans la clause de facturation, attribué à la notification d'incident."""
    vus = []
    for s in segments:
        if _cherche(regle.get("presence"), s["plat"]):
            vus.append(s)
    return vus


def _evaluer_seuil(seuil, segs):
    """Compare le chiffre trouvé au chiffre de la politique interne."""
    if not seuil:
        return None
    for s in segs:
        r = re.search(seuil["motif"], s["plat"])
        if not r:
            continue
        groupes = r.groups()
        brut = _nombre(groupes[0])
        if brut is None:
            continue
        unite = groupes[1] if len(groupes) > 1 else None
        valeur = _convertir(brut, unite, seuil["echelle"]) if seuil["echelle"] else brut
        if valeur is None:
            continue
        if seuil["sens"] == "max":
            if valeur <= seuil["standard"]:
                niv = "conforme"
            elif valeur <= seuil["tolere"]:
                niv = "repli"
            elif valeur > seuil["rouge_au_dela"]:
                niv = "ligne-rouge"
            else:
                niv = "ecart"
        else:                                   # « au moins » : plus c'est grand, mieux c'est
            if valeur >= seuil["standard"]:
                niv = "conforme"
            elif valeur >= seuil["tolere"]:
                niv = "repli"
            elif valeur < seuil["rouge_au_dela"]:
                niv = "ligne-rouge"
            else:
                niv = "ecart"
        return {"niveau": niv, "trouve": brut,
                "unite_trouvee": (unite or "").strip(),
                "compare": valeur, "attendu": seuil["standard"],
                "sens": seuil["sens"], "unite": seuil["unite_affichee"],
                "libelle": seuil["libelle"], "pourquoi": seuil["pourquoi"],
                "citation": _citer(s, r.group(0)), "article": s["ref"] or s["titre"]}
    return None


def _pire(a, b):
    return a if _RANG.get(a, 0) >= _RANG.get(b, 0) else b


def analyser(texte, domaines_retenus=None, ids=None):
    """Verdict déterministe, thème par thème. Aucun appel réseau, aucun modèle."""
    segments = decouper(texte)
    resultats, compte = [], {n["id"]: 0 for n in NIVEAUX}

    for c in juridique.CLAUSIER:
        if domaines_retenus and c["domaine"] not in domaines_retenus:
            continue
        if ids and c["id"] not in ids:
            continue
        regle = PLAYBOOK.get(c["id"])
        base = {"id": c["id"], "titre": c["titre"], "domaine": c["domaine"],
                "criticite": c["criticite"], "constats": [], "seuil": None,
                "articles": [], "position": c["modele"],
                "replis": [dict(r) for r in (regle or {}).get("replis", [])],
                "ligne_rouge": (regle or {}).get("ligne_rouge", ""),
                "risque": c["risque"], "fondement": list(c["fondement"])}

        # Garde-fou n° 1 : pas de règle, pas de verdict.
        if not regle or not regle.get("presence"):
            base["niveau"] = "non-outille"
            base["valideur"] = None
            resultats.append(base)
            compte["non-outille"] += 1
            continue

        segs = _segments_du_theme(regle, segments)
        base["articles"] = [{"ref": s["ref"], "titre": s["titre"]} for s in segs[:6]]

        if not segs:
            base["niveau"] = "absent"
            base["valideur"] = regle["valide"].get("absent")
            resultats.append(base)
            compte["absent"] += 1
            continue

        niveau = "conforme"

        for rouge in regle.get("rouge", []):
            for s in segs:
                r = re.search(rouge["motif"], s["plat"])
                if not r:
                    continue
                # `sauf` : un marqueur voisin qui désamorce l'alerte — « état de
                # l'art » suivi d'une annexe n'est plus la formule creuse visée.
                if any(re.search(x, s["plat"]) for x in rouge.get("sauf", [])):
                    continue
                base["constats"].append({
                    "type": "ligne-rouge", "pourquoi": rouge["pourquoi"],
                    "citation": _citer(s, r.group(0)),
                    "article": s["ref"] or s["titre"]})
                niveau = _pire(niveau, "ligne-rouge")
                break

        for al in regle.get("alerte", []):
            for s in segs:
                r = re.search(al["motif"], s["plat"])
                if not r:
                    continue
                if any(re.search(x, s["plat"]) for x in al.get("sauf", [])):
                    continue
                base["constats"].append({
                    "type": al["niveau"], "pourquoi": al["pourquoi"],
                    "citation": _citer(s, r.group(0)),
                    "article": s["ref"] or s["titre"]})
                niveau = _pire(niveau, al["niveau"])
                break

        sv = _evaluer_seuil(regle.get("seuil"), segs)
        if sv:
            base["seuil"] = sv
            niveau = _pire(niveau, sv["niveau"])
        elif regle.get("seuil"):
            # Le sujet est traité mais sans chiffre : c'est un écart en soi.
            base["constats"].append({
                "type": "ecart",
                "pourquoi": "Le sujet est abordé mais aucun %s chiffré n'a été trouvé. "
                            "Un engagement sans chiffre ne se constate pas."
                            % regle["seuil"]["libelle"].lower(),
                "citation": _citer(segs[0], ""), "article": segs[0]["ref"] or segs[0]["titre"]})
            niveau = _pire(niveau, "ecart")

        base["niveau"] = niveau
        base["valideur"] = regle["valide"].get(niveau) if niveau != "conforme" else None
        resultats.append(base)
        compte[niveau] += 1

    resultats.sort(key=lambda x: (-_RANG.get(x["niveau"], 0),
                                  0 if x["criticite"] == "haute" else 1, x["titre"]))
    return {"version_playbook": VERSION_PLAYBOOK,
            "version_referentiel": juridique.VERSION_REFERENTIEL,
            "articles_detectes": len(segments),
            "caracteres": len(str(texte or "")),
            "themes": resultats, "compte": compte,
            "bloquants": [t["id"] for t in resultats if t["niveau"] == "ligne-rouge"],
            "synthese": _synthese(resultats, compte)}


def _synthese(resultats, compte):
    n = len(resultats)
    rouge, ecart = compte["ligne-rouge"], compte["ecart"]
    absent, non = compte["absent"], compte["non-outille"]
    if rouge:
        tete = ("%d ligne%s rouge%s : en l'état, cette version ne peut pas être signée."
                % (rouge, "s" if rouge > 1 else "", "s" if rouge > 1 else ""))
    elif ecart:
        tete = ("Aucune ligne rouge, mais %d écart%s à faire valider avant signature."
                % (ecart, "s" if ecart > 1 else ""))
    elif absent:
        tete = ("Aucun écart sur ce qui est écrit ; %d sujet%s ne %s pas traité%s."
                % (absent, "s" if absent > 1 else "", "sont" if absent > 1 else "est",
                   "s" if absent > 1 else ""))
    else:
        tete = "Cette version tient dans les positions du playbook."
    queue = ""
    if non:
        queue = (" %d thème%s ne %s pas de règle automatique et %s relu%s à la main."
                 % (non, "s" if non > 1 else "", "portent" if non > 1 else "porte",
                    "doivent être" if non > 1 else "doit être", "s" if non > 1 else ""))
    return ("%s %d thème%s du playbook contrôlé%s.%s"
            % (tete, n, "s" if n > 1 else "", "s" if n > 1 else "", queue))


# ═══════════════════════════════════════════════════════════════════════════
# 7. COMPARER DEUX VERSIONS — ce qui a bougé pendant la négociation
# ═══════════════════════════════════════════════════════════════════════════

def comparer(avant, apres, domaines_retenus=None):
    """La question de la négociation : qu'est-ce qui a changé, et dans quel sens ?"""
    a = analyser(avant, domaines_retenus)
    b = analyser(apres, domaines_retenus)
    ia = {t["id"]: t for t in a["themes"]}
    mouvements = []
    for t in b["themes"]:
        av = ia.get(t["id"])
        if not av:
            continue
        ra, rb = _RANG.get(av["niveau"], 0), _RANG.get(t["niveau"], 0)
        if ra == rb:
            sens = "inchange"
        elif rb > ra:
            sens = "recul"
        else:
            sens = "progres"
        mouvements.append({
            "id": t["id"], "titre": t["titre"], "domaine": t["domaine"],
            "criticite": t["criticite"], "sens": sens,
            "avant": av["niveau"], "apres": t["niveau"],
            "avant_libelle": _NIVEAU[av["niveau"]]["libelle"],
            "apres_libelle": _NIVEAU[t["niveau"]]["libelle"],
            "valideur": t.get("valideur"),
            "seuil_avant": (av.get("seuil") or {}).get("trouve"),
            "seuil_apres": (t.get("seuil") or {}).get("trouve"),
            "unite": (t.get("seuil") or {}).get("unite"),
            "constats": t["constats"][:3]})
    ordre = {"recul": 0, "progres": 1, "inchange": 2}
    mouvements.sort(key=lambda m: (ordre[m["sens"]],
                                   -_RANG.get(m["apres"], 0), m["titre"]))
    reculs = [m for m in mouvements if m["sens"] == "recul"]
    progres = [m for m in mouvements if m["sens"] == "progres"]
    return {"avant": a, "apres": b, "mouvements": mouvements,
            "n_recul": len(reculs), "n_progres": len(progres),
            "n_inchange": len(mouvements) - len(reculs) - len(progres),
            "synthese": _synthese_comparaison(reculs, progres, len(mouvements))}


def _synthese_comparaison(reculs, progres, n):
    if not reculs and not progres:
        return ("Aucun des %d thèmes contrôlés n'a changé de niveau entre ces deux "
                "versions. Les modifications, s'il y en a, portent sur la forme." % n)
    bouts = []
    if reculs:
        pires = ", ".join(m["titre"].split(" et ")[0][:52] for m in reculs[:3])
        bouts.append("%d recul%s — %s%s"
                     % (len(reculs), "s" if len(reculs) > 1 else "", pires,
                        "…" if len(reculs) > 3 else ""))
    if progres:
        bouts.append("%d amélioration%s obtenue%s"
                     % (len(progres), "s" if len(progres) > 1 else "",
                        "s" if len(progres) > 1 else ""))
    dur = [m for m in reculs if m["apres"] == "ligne-rouge"]
    fin = (" Dont %d passage%s en ligne rouge : à traiter avant toute autre "
           "discussion." % (len(dur), "s" if len(dur) > 1 else "")) if dur else ""
    return " · ".join(bouts) + "." + fin


# ═══════════════════════════════════════════════════════════════════════════
# 8. LE CIRCUIT DE VALIDATION — qui doit dire oui, et sur quoi
# ═══════════════════════════════════════════════════════════════════════════

def circuit(analyse):
    """Regroupe les écarts par instance : une sollicitation par validateur, pas
    une par clause. Un juriste qui relance huit fois la même direction pour huit
    clauses allonge le cycle qu'on cherche à raccourcir."""
    par_instance = {}
    for t in analyse.get("themes", []):
        inst = t.get("valideur")
        if not inst or t["niveau"] == "conforme":
            continue
        d = par_instance.setdefault(inst, {"instance": inst,
                                           "libelle": juridique.INSTANCES.get(inst, {}).get("libelle", inst),
                                           "role": juridique.INSTANCES.get(inst, {}).get("role", ""),
                                           "points": [], "bloquant": False})
        d["points"].append({"id": t["id"], "titre": t["titre"], "niveau": t["niveau"],
                            "niveau_libelle": _NIVEAU[t["niveau"]]["libelle"],
                            "criticite": t["criticite"],
                            "motif": (t["constats"][0]["pourquoi"] if t["constats"]
                                      else (t["seuil"] or {}).get("pourquoi")
                                      or "Sujet non traité par le contrat.")})
        if t["niveau"] == "ligne-rouge":
            d["bloquant"] = True

    sortie = list(par_instance.values())
    for d in sortie:
        d["points"].sort(key=lambda p: -_RANG.get(p["niveau"], 0))
        d["n"] = len(d["points"])
    sortie.sort(key=lambda d: (not d["bloquant"], -d["n"]))
    manuels = [t for t in analyse.get("themes", []) if t["niveau"] == "non-outille"]
    return {"validations": sortie,
            "n_instances": len(sortie),
            "n_points": sum(d["n"] for d in sortie),
            "relecture_humaine": [{"id": t["id"], "titre": t["titre"]} for t in manuels]}


# ═══════════════════════════════════════════════════════════════════════════
# 9. LE CHAT — l'IA explique et rédige, elle ne décide pas
# ═══════════════════════════════════════════════════════════════════════════

SYSTEM_RELECTURE = """Tu accompagnes une équipe juridique et métier pendant la relecture et la négociation d'un contrat de services numériques (cybersécurité IT et OT/ICS, intelligence artificielle, ingénierie). Tu t'adresses à un juriste d'entreprise, un acheteur, un RSSI ou un chef de projet.

RÈGLE ABSOLUE — LES VERDICTS NE SONT PAS LES TIENS.
L'analyse du contrat a été faite par un moteur de règles déterministe, dont le résultat t'est fourni. Chaque thème porte un niveau : conforme, repli accepté d'avance, écart à faire valider, sujet non traité, ligne rouge, ou non outillé. Tu ne réévalues jamais ces niveaux, tu ne les nuances pas, tu ne dis jamais qu'un thème marqué « écart » te paraît finalement acceptable. Si le relecteur conteste un verdict, tu expliques la règle qui l'a produit et tu l'invites à faire trancher par l'instance nommée — c'est elle qui peut lever un écart, pas toi.
Si une information ne figure ni dans l'analyse ni dans le contexte fourni, dis-le franchement plutôt que de la supposer.

CE QU'ON ATTEND DE TOI
1. Expliquer un écart en une ou deux phrases, dans les mots du métier : ce que le contrat dit, ce que la politique interne demande, ce qui se passe concrètement si on signe en l'état.
2. Rédiger une contre-proposition PRÊTE À COLLER dans le contrat, en partant de la position standard ou de la position de repli fournie. Tu conserves les crochets [n] des valeurs à décider.
3. Préparer l'argument de négociation : ce que le fournisseur va objecter, et quoi répondre.
4. Dire qui doit valider quoi, en reprenant l'instance indiquée par l'analyse.

STYLE
Réponses courtes. Le relecteur a le contrat sous les yeux et cinq minutes. Pas de préambule, pas de rappel de la question, pas de « n'hésitez pas ». Une clause proposée est présentée telle qu'elle doit être insérée, sans commentaire enrobant. Tu cites les fondements (RGPD art. 32, NIS 2 art. 23, IEC 62443…) uniquement lorsqu'ils figurent dans le contexte fourni — jamais de mémoire.

Tu ne rends pas de consultation juridique et tu ne remplaces pas l'avocat de l'entreprise : tu prépares le travail de celui qui décide."""


def _bloc_theme(t, complet=True):
    lignes = ["• [%s] %s — %s (criticité %s)"
              % (t["id"], t["titre"], _NIVEAU[t["niveau"]]["libelle"], t["criticite"])]
    for c in t.get("constats", [])[:3]:
        lignes.append("    constat : %s\n      contrat : « %s »"
                      % (c["pourquoi"], c["citation"][:220]))
    s = t.get("seuil")
    if s:
        lignes.append("    chiffre : le contrat dit %s %s, la politique demande %s %s %s — %s"
                      % (s["trouve"], s["unite_trouvee"] or "",
                         "au plus" if s["sens"] == "max" else "au moins",
                         s["attendu"], s["unite"], s["pourquoi"]))
    if t.get("valideur"):
        lignes.append("    validation requise : %s"
                      % juridique.INSTANCES.get(t["valideur"], {}).get("libelle", t["valideur"]))
    if complet:
        if t.get("position"):
            lignes.append("    position standard : %s" % t["position"])
        for r in t.get("replis", [])[:2]:
            lignes.append("    repli (%s) : %s" % (r["niveau"], r["texte"]))
        if t.get("ligne_rouge"):
            lignes.append("    ligne rouge : %s" % t["ligne_rouge"])
        if t.get("fondement"):
            lignes.append("    fondements : %s" % " ; ".join(t["fondement"]))
    return "\n".join(lignes)


def contexte_chat(analyse, focus=None, extraits=None, budget=14000):
    """Le contexte du chat : les verdicts d'abord, le playbook des thèmes en
    cause ensuite. Les thèmes conformes tiennent en une ligne — on ne dépense
    pas le contexte à décrire ce qui va bien."""
    if not analyse:
        return ""
    parts = ["ANALYSE DÉTERMINISTE DE LA VERSION EN COURS (playbook %s, référentiel %s)"
             % (analyse.get("version_playbook", ""), analyse.get("version_referentiel", "")),
             analyse.get("synthese", ""), ""]

    themes_l = analyse.get("themes", [])
    if focus:
        vise = [t for t in themes_l if t["id"] == focus]
        autres = [t for t in themes_l if t["id"] != focus]
        if vise:
            parts.append("THÈME SUR LEQUEL PORTE LA QUESTION :")
            parts.append(_bloc_theme(vise[0], complet=True))
            parts.append("")
        themes_l = autres

    chauds = [t for t in themes_l if t["niveau"] in ("ligne-rouge", "ecart", "absent")]
    tiedes = [t for t in themes_l if t["niveau"] == "repli"]
    froids = [t for t in themes_l if t["niveau"] in ("conforme", "non-outille")]

    if chauds:
        parts.append("POINTS OUVERTS :")
        for t in chauds:
            parts.append(_bloc_theme(t, complet=not focus))
        parts.append("")
    if tiedes:
        parts.append("REPLIS ACCEPTÉS D'AVANCE (ne nécessitent pas de remontée) :")
        for t in tiedes:
            parts.append("• %s — %s" % (t["titre"], _NIVEAU[t["niveau"]]["libelle"]))
        parts.append("")
    if froids:
        parts.append("THÈMES SANS SUITE À DONNER : "
                     + " ; ".join("%s (%s)" % (t["titre"][:46], _NIVEAU[t["niveau"]]["libelle"])
                                  for t in froids))
        parts.append("")
    if extraits:
        parts.append("EXTRAITS DE LA BASE DE CONNAISSANCE INTERNE :")
        parts.append(str(extraits))

    txt = "\n".join(parts)
    return txt[:budget]


SUGGESTIONS = [
    "Quels points bloquent la signature en l'état ?",
    "Rédige la contre-proposition pour le délai de notification.",
    "Qu'est-ce que le fournisseur va objecter sur le droit d'audit, et quoi répondre ?",
    "Qui dois-je faire valider, et sur quoi exactement ?",
    "Quels écarts puis-je accepter sans remonter ?",
    "Résume en cinq lignes pour le comité d'engagement.",
]


# ═══════════════════════════════════════════════════════════════════════════
# 10. LA NOTE DE RELECTURE — ce qui sort de la séance
# ═══════════════════════════════════════════════════════════════════════════

def note_markdown(analyse, objet=None, circuit_=None, comparaison=None, echange=None):
    """Note de relecture exportable. Elle porte les verdicts déterministes, leurs
    citations et le circuit de validation : c'est la trace qui rend la décision
    opposable en interne."""
    t = ["# Note de relecture contractuelle",
         "",
         "**Objet :** %s" % (objet or "contrat de services numériques"),
         "**Playbook :** version %s · **Référentiel juridique :** version %s"
         % (VERSION_PLAYBOOK, juridique.VERSION_REFERENTIEL),
         "**Étendue :** %d thèmes contrôlés sur %d articles détectés (%d caractères)"
         % (len(analyse.get("themes", [])), analyse.get("articles_detectes", 0),
            analyse.get("caracteres", 0)),
         "", "## Ce qu'il faut retenir", "", analyse.get("synthese", ""), ""]

    if comparaison:
        t += ["## Ce qui a bougé depuis la version précédente", "",
              comparaison.get("synthese", ""), "",
              "| Thème | Avant | Après | Sens |", "|---|---|---|---|"]
        for m in comparaison.get("mouvements", []):
            if m["sens"] == "inchange":
                continue
            t.append("| %s | %s | %s | %s |"
                     % (m["titre"], m["avant_libelle"], m["apres_libelle"],
                        "recul" if m["sens"] == "recul" else "amélioration"))
        t.append("")

    ordre = ["ligne-rouge", "ecart", "absent", "repli", "non-outille", "conforme"]
    for niv in ordre:
        lot = [x for x in analyse.get("themes", []) if x["niveau"] == niv]
        if not lot:
            continue
        t += ["## %s (%d)" % (_NIVEAU[niv]["libelle"], len(lot)), "",
              "*%s*" % _NIVEAU[niv]["sens"], ""]
        if niv in ("conforme", "non-outille"):
            t += ["- " + x["titre"] for x in lot] + [""]
            continue
        for x in lot:
            t.append("### %s" % x["titre"])
            t.append("*%s · criticité %s%s*"
                     % (x["domaine"], x["criticite"],
                        " · validation : " + juridique.INSTANCES.get(x["valideur"], {}).get("libelle", "")
                        if x.get("valideur") else ""))
            t.append("")
            for c in x.get("constats", []):
                t.append("- **%s** (article %s)" % (c["pourquoi"], c["article"] or "n. c."))
                t.append("  > %s" % c["citation"])
            s = x.get("seuil")
            if s:
                t.append("- **%s :** le contrat prévoit %s %s ; la position interne "
                         "demande %s %s %s. %s"
                         % (s["libelle"], s["trouve"], s["unite_trouvee"] or "",
                            "au plus" if s["sens"] == "max" else "au moins",
                            s["attendu"], s["unite"], s["pourquoi"]))
                t.append("  > %s" % s["citation"])
            if x.get("position"):
                t += ["", "**Rédaction à proposer :**", "", "> " + x["position"].replace("\n", " ")]
            if x.get("replis"):
                t += ["", "**Positions de repli :**"] + \
                     ["- *(%s)* %s" % (r["niveau"], r["texte"]) for r in x["replis"]]
            if x.get("ligne_rouge"):
                t += ["", "**Ligne rouge :** %s" % x["ligne_rouge"]]
            t.append("")

    if circuit_ and circuit_.get("validations"):
        t += ["## Circuit de validation", "",
              "%d point(s) à faire valider par %d instance(s)."
              % (circuit_["n_points"], circuit_["n_instances"]), ""]
        for v in circuit_["validations"]:
            t.append("### %s%s" % (v["libelle"], " — bloquant" if v["bloquant"] else ""))
            for p in v["points"]:
                t.append("- **%s** (%s) : %s" % (p["titre"], p["niveau_libelle"], p["motif"]))
            t.append("")
        if circuit_.get("relecture_humaine"):
            t += ["### À relire à la main", "",
                  "Ces thèmes n'ont pas de règle de détection automatique. "
                  "Ils ne sont ni validés ni invalidés par cette note.", ""]
            t += ["- " + x["titre"] for x in circuit_["relecture_humaine"]] + [""]

    if echange:
        t += ["## Échange avec l'assistant de relecture", ""]
        for m in echange[-12:]:
            qui = "**Relecteur**" if m.get("role") == "user" else "**Assistant**"
            t.append("%s — %s" % (qui, str(m.get("content", ""))[:1500]))
            t.append("")

    t += ["---", "", juridique.AVERTISSEMENT, "", juridique.MENTION_IA]
    return "\n".join(t)


# ═══════════════════════════════════════════════════════════════════════════
# 11. SANTÉ — le playbook se contrôle lui-même
# ═══════════════════════════════════════════════════════════════════════════

def sante():
    """Vérifie que le playbook et le clausier ne divergent pas, et que chaque
    motif compile. Un motif cassé ferait taire une règle en silence."""
    ids_clausier = {c["id"] for c in juridique.CLAUSIER}
    orphelins = sorted(set(PLAYBOOK) - ids_clausier)
    sans_regle = sorted(i for i in ids_clausier if i not in PLAYBOOK)
    motifs, casses = 0, []
    for tid, p in PLAYBOOK.items():
        listes = [("presence", [{"motif": m} for m in p.get("presence", [])]),
                  ("rouge", p.get("rouge", [])), ("alerte", p.get("alerte", []))]
        if p.get("seuil"):
            listes.append(("seuil", [{"motif": p["seuil"]["motif"]}]))
        for nom, lot in listes:
            for r in lot:
                motifs += 1
                try:
                    re.compile(r["motif"])
                except re.error as exc:
                    casses.append("%s/%s : %s" % (tid, nom, exc))
    instances_inconnues = sorted({v for p in PLAYBOOK.values()
                                  for v in p.get("valide", {}).values()
                                  if v not in juridique.INSTANCES})
    ok = not orphelins and not casses and not instances_inconnues
    return {"ok": ok, "version": VERSION_PLAYBOOK,
            "themes_clausier": len(ids_clausier), "themes_outilles": len(PLAYBOOK),
            "sans_regle": sans_regle, "orphelins": orphelins,
            "motifs": motifs, "motifs_casses": casses,
            "instances_inconnues": instances_inconnues,
            "detail": ("%d thèmes outillés sur %d, %d motifs compilés"
                       % (len(PLAYBOOK), len(ids_clausier), motifs))}
