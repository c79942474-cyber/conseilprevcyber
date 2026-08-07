# -*- coding: utf-8 -*-
"""Ce qui sort de la base documentaire, remis en état d'être lu.

La base est alimentée par des PDF. Un PDF ne contient pas du texte : il
contient des glyphes posés à des coordonnées, et l'extraction les recoud dans
l'ordre où ils ont été dessinés. Sur un paragraphe ordinaire, cela marche. Sur
tout le reste, cela produit ce qu'on a lu dans un livrable remis :

  · un TABLEAU aplati en flux de mots. La matrice de criticité d'un guide
    méthodologique ressort en « Impact potentiel catastrophique Impact
    potentiel majeur … Probabilité très faible Probabilité faible … » : les
    cellules à la file, sans ligne ni colonne, donc sans le sens que portait
    leur croisement ;

  · une SÉRIE DE DONNÉES de graphique, avec la précision machine intacte —
    « Centres de données | 0.13699999999999993 | 0.168 » — et coupée en plein
    milieu d'un nombre ;

  · des LISTES à puces recousues en un seul bloc, où plus rien ne distingue
    les quatre catégories d'acteurs les unes des autres ;

  · des LETTRES DÉTACHÉES de leur mot, quand la première d'un item porte un
    crénage propre : « les o pérateurs non -propriétaires » ;

  · de la PAGINATION et des titres courants au milieu d'une phrase :
    « … Risque critique 88 OCARA – Guide méthodologique 2021 89 6. » ;

  · des RENVOIS PENDANTS — « elle répond au barème présenté dans le tableau
    suivant » — qui ne disent rien sans la figure que nous ne portons pas.

Deux gestes, et il importe de ne pas les confondre.

RÉPARER n'est pas reformuler. « o pérateurs » n'a jamais été écrit ainsi : le
mot est « opérateurs », et l'espace vient de NOTRE lecteur de PDF. Rendre à ce
mot sa forme, à ces items leur retour à la ligne, à cette virgule sa place,
c'est restituer ce que la source dit — pas le récrire. Le livrable peut donc
continuer d'annoncer des extraits reproduits mot pour mot.

REJETER est la seule réponse honnête au reste. Un tableau aplati ne se
reconstruit pas : les lignes et les colonnes ont disparu à l'extraction, et
les réinventer serait fabriquer une donnée. Une série à dix-sept décimales
coupée en plein nombre ne se rattrape pas non plus. Ces fragments sortent donc
du livrable, et le chapitre de traçabilité en donne le compte et le motif :
c'est ce qui distingue un écart assumé d'une perte silencieuse.

Un point resté sans extrait est marqué « à rédiger », ce qui est vrai. Un
point documenté par un tableau illisible était marqué comme documenté, ce qui
ne l'était pas.
"""

import re

# ═══════════════════════════════════════════════════════════════════════════
#  1. RÉPARER — rendre au texte ce que l'extraction lui a pris
# ═══════════════════════════════════════════════════════════════════════════

# Les puces, quel que soit le glyphe employé par la source. Le tiret seul n'y
# figure pas : il sert aussi de trait d'union et de tiret de dialogue, et
# couper dessus hacherait des phrases entières.
PUCES = "•▪‣◦●"
_PUCE = re.compile(r"\s*[" + PUCES + r"]\s*")

# Une lettre isolée collée au mot suivant. « a », « à » et « y » sont de vrais
# mots français : les recoudre ferait « yompris » et « adopté » là où le texte
# disait « y compris » et « a dopté »… c'est-à-dire l'inverse du service rendu.
# Les autres lettres seules n'existent pas en français hors apostrophe — et
# l'apostrophe, elle, ne laisse pas d'espace derrière elle.
_LETTRE_DETACHEE = re.compile(
    r"(?<![^\W\d_])(?<![’'])([bcdefghijklmnopqrstuvwxz])\s+([a-zà-öø-ÿ]{2,})")

# Le trait d'union séparé de l'un de ses deux mots. L'espace n'est mise QUE
# d'un côté : « non -propriétaires », « couvre- feu ». Une espace des deux
# côtés est une incise voulue par l'auteur, on n'y touche pas.
_TIRET_GAUCHE = re.compile(r"(\w)\s+-(\w)")
_TIRET_DROIT = re.compile(r"(\w)-\s+(\w)")

# L'espace avant une ponctuation qui n'en prend pas en français. Le
# point-virgule, les deux-points, le point d'interrogation et les guillemets
# en prennent une, fine : ils ne sont pas de la partie.
_ESPACE_AVANT = re.compile(r"\s+([,.)\]])")
# …et l'espace manquante après.
_ESPACE_APRES = re.compile(r"([,;])(?=[A-Za-zÀ-ÿ])")


def reparer(txt):
    """Rend au texte la forme qu'il avait avant de passer par l'extraction."""
    t = " ".join((txt or "").replace(" ", " ").split())
    if not t:
        return ""
    # Les lettres détachées d'abord : « non -propriétaires » se répare mieux
    # quand « p ropriétaires » a déjà retrouvé son p.
    for _ in range(2):        # « d e s » demande deux passes, « d es » une
        neuf = _LETTRE_DETACHEE.sub(r"\1\2", t)
        if neuf == t:
            break
        t = neuf
    t = _TIRET_GAUCHE.sub(r"\1-\2", t)
    t = _TIRET_DROIT.sub(r"\1-\2", t)
    t = _ESPACE_AVANT.sub(r"\1", t)
    t = _ESPACE_APRES.sub(r"\1 ", t)
    return " ".join(t.split())


def morceler(txt):
    """Rend leur ligne aux items d'une liste recousue en un seul bloc.

    Quatre catégories d'acteurs à la file dans un paragraphe de six lignes ne
    se distinguent plus : on les relit trois fois pour trouver où finit la
    troisième. La source les avait mises à la ligne ; l'extraction les a
    recollées. On les rend, préfixées d'un tiret — ce qui reste une citation,
    puisque c'est la mise en forme d'origine qu'on restitue.
    """
    t = reparer(txt)
    if not t:
        return []
    if sum(t.count(c) for c in PUCES) < 2:
        return [t]
    bouts = [b.strip(" ;,") for b in _PUCE.split(t)]
    bouts = [b for b in bouts if b]
    if len(bouts) < 3:        # une intro et un seul item : rien à séparer
        return [t]
    # Le premier morceau est l'annonce (« … agissent dans l'écosystème : »),
    # pas un item. Il ne prend donc pas de tiret.
    return [bouts[0]] + ["– " + b for b in bouts[1:]]


# ═══════════════════════════════════════════════════════════════════════════
#  2. REJETER — ce qui ne se répare pas ne s'écrit pas
# ═══════════════════════════════════════════════════════════════════════════

# CE QUI SÉPARE UNE PHRASE D'UNE COLONNE : les mots outils.
#
# Une phrase française en compte 35 à 50 % — articles, prépositions,
# pronoms, auxiliaires : ce sont eux qui relient les mots pleins entre eux.
# Une suite de cellules de tableau n'en a aucun, puisqu'il n'y avait rien à
# relier : « Impact potentiel catastrophique Impact potentiel majeur Impact
# potentiel grave » tombe à 3 %.
#
# C'est la mesure qui distingue, et non le fait qu'un mot se répète : quatre
# items de liste parlant tous de « centres de données » répètent
# légitimement, et une première version qui comptait les répétitions jetait
# la liste des acteurs avec la matrice de criticité.
_OUTILS = set("""
le la les l un une des du de d au aux a à et ou en dans sur pour par avec
sans sous ce cet cette ces qui que qu dont où il elle ils elles on se sa son
ses leur leurs est sont ont été être plus ne pas ni y si mais donc or car
chez vers entre selon lors afin ainsi comme aussi tout tous toute toutes
chaque nous vous je tu mon ma notre votre cela ceci celui celle ceux celles
doit doivent peut peuvent était étaient sera seront leurs même mêmes
""".split())
_MOT = re.compile(r"[A-Za-zÀ-ÿ']+")
# En deçà de cette part de mots outils, ce n'est plus une phrase.
_SEUIL_OUTILS = 0.15
_FENETRE = 250
_PAS = 60
# La précision machine d'un tableur, échappée dans un texte : personne n'écrit
# 0,13699999999999993 à la main.
_FLOTTANT = re.compile(r"\d[.,]\d{6,}")
# Un renvoi à ce que nous ne portons pas. La figure est restée dans le PDF
# d'origine ; la phrase qui l'annonce ne dit plus rien toute seule.
_RENVOI = re.compile(
    r"\b(tableau|figure|graphique|schéma|annexe|encadré)x?\s+"
    r"(suivant|ci-dessous|ci-après|ci-contre|précédent)", re.I)
_LEGENDE = re.compile(r"^\s*(figure|tableau|graphique|schéma)\s*\d+\s*[:.]",
                      re.I)


def _part_outils(txt):
    """Part des mots outils, et le nombre de mots sur lequel elle est prise."""
    mots = [m.lower().strip("'’") for m in _MOT.findall(txt)]
    mots = [m for m in mots if m]
    if not mots:
        return 1.0, 0
    return sum(1 for m in mots if m in _OUTILS) / float(len(mots)), len(mots)


def _pire_fenetre(txt):
    """La fenêtre la plus pauvre en mots outils, et son début.

    Prise sur une fenêtre glissante : un fragment peut être une phrase sur
    ses deux premières lignes et une colonne de tableau sur les six
    suivantes, ce qui est précisément le cas d'une matrice précédée de son
    commentaire. Une moyenne sur l'ensemble noierait la queue dans la tête.
    """
    part, mots = _part_outils(txt)
    if mots < 10:
        # Trop court pour qu'une fenêtre ait un sens : on juge sur l'ensemble,
        # et seulement s'il y a de quoi juger.
        return (part, txt[:60]) if mots >= 5 else (1.0, "")
    pire, ou = part, txt[:60]
    for i in range(0, max(1, len(txt) - _FENETRE + 1), _PAS):
        bout = txt[i:i + _FENETRE]
        p, n = _part_outils(bout)
        if n >= 12 and p < pire:
            pire, ou = p, bout
    return pire, ou


def motif_rejet(txt):
    """Pourquoi ce fragment ne peut pas figurer dans un livrable, ou "".

    Rendu en clair et non par un code : il part au chapitre de traçabilité,
    que lit un relecteur et non un exploitant.
    """
    t = (txt or "").strip()
    if not t:
        return "fragment vide"
    # UN TABLEAU APLATI. Les barres verticales survivent souvent à
    # l'extraction alors que les lignes, elles, ont disparu : il reste les
    # séparateurs de colonnes d'une grille qui n'existe plus.
    if t.count("|") >= 3:
        return "tableau aplati par l'extraction, lignes et colonnes perdues"
    if _FLOTTANT.search(t):
        return "série de données brutes, à la précision du tableur"
    # UNE ÉNUMÉRATION DE CELLULES. On la reconnaît à ce qu'il n'y a rien pour
    # relier ses mots : ni article, ni préposition, ni verbe. La mesure se
    # fait sur la PIRE fenêtre et non sur l'ensemble — une matrice précédée
    # de deux phrases d'introduction ressort à 27 % globalement, ce qui la
    # ferait passer, alors que sa queue de cellules est à 3 %.
    part, ou = _pire_fenetre(t)
    if part < _SEUIL_OUTILS:
        return ("cellules de tableau mises bout à bout, sans phrase pour les "
                "relier (« %s… »)" % ou[:44])
    # UN RENVOI PENDANT. Court ET suspendu à une figure absente : il ne reste
    # rien à en tirer. Long, la phrase porte au moins son propre contenu.
    if len(t) < 260 and (_RENVOI.search(t) or _LEGENDE.match(t)):
        return "renvoi à une figure que le livrable ne porte pas"
    return ""


def lisible(txt):
    """Ce fragment peut-il être lu par quelqu'un qui n'a pas le PDF ?"""
    return not motif_rejet(txt)


# ═══════════════════════════════════════════════════════════════════════════
#  3. LA CHAÎNE COMPLÈTE
# ═══════════════════════════════════════════════════════════════════════════

def phrases_entieres(txt, maxi=1400):
    """Un extrait qui commence et finit sur une phrase.

    La base est découpée en fragments de taille fixe : un fragment commence au
    milieu d'un mot (« luer l'état actuel… ») et s'arrête de même. Reproduit
    tel quel dans un livrable, cela se lit comme une faute de frappe — et un
    lecteur qui bute sur la première ligne d'une citation ne lit pas la suite.

    On coupe donc aux frontières de phrase : on jette l'amorce jusqu'à la
    première majuscule qui suit un point, et la fin après le dernier point. Si
    aucune phrase entière ne se dégage, on ne cite rien : mieux vaut un point
    sans extrait qu'un extrait illisible.
    """
    t = " ".join((txt or "").split())
    if not t:
        return ""
    # Début : la première phrase complète. Un fragment qui commence déjà par
    # une majuscule est intact, on n'y touche pas.
    if not (t[:1].isupper() or t[:1].isdigit()):
        m = re.search(r"(?<=[.!?])\s+(?=[A-ZÀÂÉÈÊËÎÏÔÙÛÜÇ0-9])", t)
        if not m:
            return ""
        t = t[m.end():]
    coupe = len(t) > maxi
    if coupe:
        t = t[:maxi]
    # Fin : après le dernier point. Un extrait qui se termine DÉJÀ sur une
    # phrase est gardé tel quel, si court soit-il — exiger une longueur
    # minimale écartait « Le régime d'eau glacée retenu est 18/24 °C. », qui
    # est pourtant une phrase entière et la seule qui documente son point.
    if not coupe and t.endswith((".", "!", "?")):
        return t
    fin = max(t.rfind("."), t.rfind("!"), t.rfind("?"))
    if fin < 40:
        return ""
    return t[:fin + 1].strip()


def preparer(txt, maxi=1400):
    """Réparer, puis borner aux phrases, puis juger. Rend "" si inutilisable.

    L'ordre compte. Réparer d'abord : une lettre détachée en tête de fragment
    empêchait d'y reconnaître une phrase. Juger en dernier : un fragment
    devient parfois lisible une fois sa queue de tableau tombée à la coupe.
    """
    t = phrases_entieres(reparer(txt), maxi)
    if not t:
        return ""
    return "" if motif_rejet(t) else t


def paragraphes(txt, maxi=1400):
    """Le fragment prêt à citer, découpé en paragraphes — [] si inutilisable.

    C'est la forme que consomment les livrables : chaque paragraphe part dans
    sa propre ligne de citation, faute de quoi les items d'une liste se
    recolleraient à l'affichage après avoir été séparés ici.
    """
    t = preparer(txt, maxi)
    return morceler(t) if t else []
