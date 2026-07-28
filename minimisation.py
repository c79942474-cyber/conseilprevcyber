"""Détection des données personnelles avant transmission à un modèle.

POURQUOI CE MODULE EXISTE. Le site ne conserve ni les conversations ni les
pièces analysées, mais il les TRANSMET à un fournisseur de modèle. La
minimisation (RGPD art. 5.1.c) ne se joue donc pas au stockage — il n'y en a
pas — elle se joue à l'envoi : ce qui n'est pas nécessaire à la réponse n'a pas
à quitter le poste de l'utilisateur. Or personne ne relit sa question avant de
l'envoyer ; c'est au produit de le signaler.

CE QU'IL FAIT, ET CE QU'IL NE FAIT PAS. Il repère des données personnelles
DIRECTEMENT IDENTIFIANTES et de forme stable — adresse électronique, téléphone,
IBAN, carte de paiement, numéro de sécurité sociale — puis avertit. Il ne
prétend pas repérer un nom, une adresse postale ou une donnée de santé : une
détection par apprentissage sur ces catégories serait bruyante, non reproductible
et, surtout, supposerait d'envoyer le texte à un modèle — c'est-à-dire de faire
exactement ce que l'on cherche à éviter. Mieux vaut une détection étroite et
sûre, annoncée comme telle, qu'une détection large et fausse : un avertissement
qui se déclenche à tort est désactivé mentalement par l'utilisateur au bout de
trois fois, et ne protège plus rien.

TROIS RÈGLES DE CONCEPTION.
  1. RIEN N'EST CONSERVÉ. Le texte analysé n'est ni stocké, ni journalisé, ni
     renvoyé tel quel. Le résultat ne contient que des catégories, des comptes,
     des positions et des exemples MASQUÉS.
  2. AUCUN MODÈLE. Expressions régulières et clés de contrôle uniquement :
     le résultat est reproductible et vérifiable par un contrôle.
  3. ON N'INTERDIT PAS, ON AVERTIT. L'utilisateur reste maître : il corrige,
     demande le caviardage automatique, ou confirme l'envoi en connaissance de
     cause. Bloquer une revue de contrat parce qu'un signataire y est nommé
     rendrait l'outil inutilisable, ce qui n'aiderait personne.

CLÉS DE CONTRÔLE. IBAN, carte et numéro de sécurité sociale portent une clé
mathématique : elle est VÉRIFIÉE. Une référence de commande à seize chiffres,
un identifiant de norme, un numéro de série ne passent pas la clé et ne sont
donc pas signalés. L'adresse électronique et le téléphone n'ont pas de clé et
sont reconnus par forme, avec des garde-fous de voisinage.

Module autonome : bibliothèque standard uniquement.
"""
import re

VERSION = "2026-07"

# ═══════════════════════════════════════════════════════════════════════════
#  Motifs
# ═══════════════════════════════════════════════════════════════════════════
# (?<![\w.]) / (?![\w.]) : évite de couper au milieu d'un identifiant.
_RE_EMAIL = re.compile(
    r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,24}(?![\w.-])")

# Téléphone français ou international en +33. Le voisinage interdit un chiffre
# collé de part et d'autre : « 0102030405 » est un numéro, « 60102030405678 »
# est autre chose.
_RE_TEL = re.compile(
    r"(?<![\d])(?:(?:\+|00)\s?33\s?(?:\(0\)\s?)?[1-9]|0[1-9])"
    r"(?:[\s.\-]?\d{2}){4}(?![\d])")

# IBAN : 2 lettres de pays, 2 chiffres de clé, puis 11 à 30 alphanumériques
# éventuellement groupés par 4. La clé mod 97 est vérifiée ensuite.
_RE_IBAN = re.compile(
    r"(?<![A-Z0-9])[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{2,4}){2,8}(?![A-Z0-9])")

# Carte de paiement : 13 à 19 chiffres, groupés ou non. Luhn vérifié ensuite.
_RE_CARTE = re.compile(r"(?<![\d.,])(?:\d[ \-]?){12,18}\d(?![\d.,])")

# Numéro de sécurité sociale : sexe, année, mois, département (dont 2A/2B pour
# la Corse), commune, ordre, puis clé sur deux chiffres. Clé vérifiée ensuite.
_RE_NIR = re.compile(
    r"(?<![\dA-Z])([12])[ .]?(\d{2})[ .]?(0[1-9]|1[0-2]|[2-9]\d)[ .]?"
    r"(\d{2}|2[AB])[ .]?(\d{3})[ .]?(\d{3})[ .]?(\d{2})(?![\dA-Z])")

LIBELLES = {
    "email": "Adresse électronique",
    "telephone": "Numéro de téléphone",
    "iban": "Coordonnées bancaires (IBAN)",
    "carte": "Numéro de carte de paiement",
    "nir": "Numéro de sécurité sociale",
}

# Catégories dont la divulgation est la plus lourde de conséquences : elles
# justifient un avertissement plus ferme. Le NIR est un identifiant national
# dont l'usage est encadré ; l'IBAN et la carte ouvrent un risque de fraude
# immédiat, sans rapport avec la question posée à un assistant juridique.
SENSIBLES = ("nir", "iban", "carte")

MARQUEURS = {
    "email": "[ADRESSE EMAIL RETIREE]",
    "telephone": "[TELEPHONE RETIRE]",
    "iban": "[IBAN RETIRE]",
    "carte": "[CARTE RETIREE]",
    "nir": "[NUMERO SECURITE SOCIALE RETIRE]",
}


# ═══════════════════════════════════════════════════════════════════════════
#  Clés de contrôle
# ═══════════════════════════════════════════════════════════════════════════
def _mod97(chaine):
    """Reste modulo 97, calculé par tranches pour éviter les entiers géants."""
    reste = 0
    for c in chaine:
        reste = (reste * 10 + int(c)) % 97
    return reste


def _iban_valide(brut):
    s = re.sub(r"[^A-Z0-9]", "", brut.upper())
    if not (15 <= len(s) <= 34) or not s[:2].isalpha() or not s[2:4].isdigit():
        return False
    reordonne = s[4:] + s[:4]
    chiffres = ""
    for c in reordonne:
        chiffres += str(ord(c) - 55) if c.isalpha() else c
    return _mod97(chiffres) == 1


def _luhn_valide(brut):
    s = re.sub(r"\D", "", brut)
    if not (13 <= len(s) <= 19):
        return False
    if len(set(s)) == 1:          # 0000…, 1111… : gabarit, pas une carte
        return False
    total, double = 0, False
    for c in reversed(s):
        n = int(c)
        if double:
            n *= 2
            if n > 9:
                n -= 9
        total += n
        double = not double
    return total % 10 == 0


def _nir_valide(m):
    """Clé du NIR : 97 − (numéro mod 97), sur les 13 premiers chiffres."""
    corps = "".join(m.group(i) for i in range(1, 7))
    corps = corps.replace("2A", "19").replace("2B", "18")
    if not corps.isdigit() or len(corps) != 13:
        return False
    return _mod97(corps) == (97 - int(m.group(7))) % 97


_VALIDATEURS = {
    "iban": lambda m: _iban_valide(m.group(0)),
    "carte": lambda m: _luhn_valide(m.group(0)),
    "nir": _nir_valide,
}

# L'ordre compte : un NIR à 15 chiffres pourrait ressembler à une carte, un
# IBAN contient des chiffres. On reconnaît d'abord le plus spécifique et on
# écarte ensuite tout chevauchement.
_ORDRE = (
    ("email", _RE_EMAIL),
    ("iban", _RE_IBAN),
    ("nir", _RE_NIR),
    ("carte", _RE_CARTE),
    ("telephone", _RE_TEL),
)


# ═══════════════════════════════════════════════════════════════════════════
#  Analyse
# ═══════════════════════════════════════════════════════════════════════════
def _masquer_exemple(brut, categorie):
    """Exemple reconnaissable par celui qui a écrit le texte, inexploitable
    par quiconque le lirait ailleurs (journal, capture d'écran, ticket)."""
    s = (brut or "").strip()
    if categorie == "email":
        avant, _, apres = s.partition("@")
        return (avant[:1] or "?") + "***@" + (apres[:1] or "?") + "***"
    compact = re.sub(r"[\s.\-]", "", s)
    if len(compact) <= 4:
        return "*" * len(compact)
    return compact[:2] + "*" * (len(compact) - 4) + compact[-2:]


def analyser(texte, limite=200000):
    """Repère les données personnelles d'un texte. Ne conserve rien.

    Retourne :
      {"detections": [{"type","libelle","occurrences","exemples","sensible",
                       "positions":[[debut,fin],…]}],
       "total": int, "sensible": bool, "message": str}
    """
    texte = texte if isinstance(texte, str) else ""
    if len(texte) > limite:                # borne de coût : un contrat de 6 Mo
        texte = texte[:limite]             # ne doit pas immobiliser un worker

    pris = []                              # intervalles déjà attribués
    trouve = {}
    for categorie, motif in _ORDRE:
        valider = _VALIDATEURS.get(categorie)
        for m in motif.finditer(texte):
            if valider and not valider(m):
                continue
            debut, fin = m.span()
            if any(debut < f and d < fin for d, f in pris):
                continue                   # chevauche une catégorie plus précise
            pris.append((debut, fin))
            e = trouve.setdefault(categorie, {"positions": [], "exemples": []})
            e["positions"].append([debut, fin])
            if len(e["exemples"]) < 3:
                ex = _masquer_exemple(m.group(0), categorie)
                if ex not in e["exemples"]:
                    e["exemples"].append(ex)

    detections = []
    for categorie, _ in _ORDRE:
        if categorie not in trouve:
            continue
        e = trouve[categorie]
        detections.append({
            "type": categorie,
            "libelle": LIBELLES[categorie],
            "occurrences": len(e["positions"]),
            "exemples": e["exemples"],
            "sensible": categorie in SENSIBLES,
            "positions": sorted(e["positions"]),
        })

    total = sum(d["occurrences"] for d in detections)
    sensible = any(d["sensible"] for d in detections)
    return {"detections": detections, "total": total, "sensible": sensible,
            "message": _message(detections, total, sensible), "version": VERSION}


def _message(detections, total, sensible):
    if not total:
        return ""
    liste = ", ".join("%s (%d)" % (d["libelle"], d["occurrences"]) for d in detections)
    if total > 1:
        base = ("Ce texte contient %d données personnelles : %s. Elles seraient "
                "transmises au fournisseur du modèle." % (total, liste))
    else:
        base = ("Ce texte contient une donnée personnelle : %s. Elle serait "
                "transmise au fournisseur du modèle." % liste)
    if sensible:
        base += (" Un numéro de sécurité sociale, un IBAN ou une carte de paiement "
                 "n'est jamais utile à une analyse juridique : retirez-le.")
    else:
        base += " Retirez ce qui n'est pas nécessaire à votre question."
    return base


def masquer(texte, limite=200000):
    """Remplace les données détectées par des marqueurs explicites.

    Le marqueur est LISIBLE et indique la nature de ce qui a été retiré : un
    modèle qui lit « [ADRESSE EMAIL RETIREE] » comprend qu'il manquait une
    adresse, là où une suppression pure lui ferait lire une phrase incohérente.
    """
    res = analyser(texte, limite=limite)
    remplacements = []
    for d in res["detections"]:
        for debut, fin in d["positions"]:
            remplacements.append((debut, fin, MARQUEURS[d["type"]]))
    if not remplacements:
        return texte if isinstance(texte, str) else ""
    remplacements.sort(reverse=True)
    out = texte
    for debut, fin, marque in remplacements:
        out = out[:debut] + marque + out[fin:]
    return out


def controler(texte, accepte=False):
    """Contrôle avant envoi au modèle. Retourne None si l'envoi peut se faire.

    Sinon, retourne la charge utile à renvoyer au navigateur pour qu'il propose
    de corriger, de caviarder ou de confirmer. Le contrôle est fait ICI, côté
    serveur, et non dans le navigateur : un avertissement contournable en
    changeant d'onglet ne serait pas une mesure de minimisation, seulement son
    apparence.
    """
    if accepte:
        return None
    res = analyser(texte)
    if not res["total"]:
        return None
    return {"ok": False, "error": "donnees_personnelles",
            "minimisation": res, "message": res["message"]}


def resume_journal(res):
    """Trace journalisable : catégories et comptes, JAMAIS le texte ni un exemple."""
    if not res or not res.get("total"):
        return "aucune donnée personnelle détectée"
    return ", ".join("%s×%d" % (d["type"], d["occurrences"])
                     for d in res["detections"])
