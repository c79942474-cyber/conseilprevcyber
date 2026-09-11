# -*- coding: utf-8 -*-
"""Un document déposé qu'on n'a pas su nommer verse quand même — et le dit.

CE QUI A DÉCLENCHÉ CE FICHIER. La demande était « l'ensemble des docs
téléchargées doivent être utilisées pour remplir ». Elle ne l'était pas. Un
fichier que `identifier()` ne reconnaissait pas était rangé dans `inconnues`
avec son nom et sa taille — ET SON TEXTE JETÉ. Mesuré sur une annexe portant
l'acheteur, l'objet, les lots et la procédure en première page : DOUZE
rubriques restaient vides sur cinq pièces, alors que le dossier déposé les
contenait. Élargir la reconnaissance repousse le problème sans le régler : il
restera toujours un fichier nommé « annexe 7 » que rien ne permet de classer.

LE DANGER EXACT DE CE BRANCHEMENT, ET CE QUI LE TIENT. Un fichier qu'on ne sait
pas nommer est une source faible. S'il écrasait le règlement de consultation,
on recopierait sur un DC1 l'acheteur d'un AUTRE marché. Deux garde-fous, tous
deux mesurés ici : `RANG_NON_IDENTIFIE` le fait passer APRÈS toute pièce
identifiée — il comble des trous, il n'écrase rien — et son désaccord ressort
en DIVERGENCE au lieu de disparaître.

LE TÉMOIN NÉGATIF EST LA MOITIÉ DU FICHIER. Une règle qui vérifierait seulement
que le drapeau `a_confirmer` existe passerait aussi bien si TOUTE valeur le
portait — auquel cas il ne distinguerait plus rien. On mesure donc aussi qu'une
valeur venue d'une pièce identifiée ne le porte PAS.
"""
import pytest

import ao_dc as A


# ── Les matières premières : un fichier qu'aucun marqueur ne classe ─────────
#: Une annexe telle que les plateformes acheteur en livrent : le nom ne dit
#: rien, le contenu dit tout. C'est le cas qui motive ce fichier.
NOM_MUET = "annexe-7.pdf"
TEXTE_RICHE = (
    "ANNEXE 7\n\n"
    "Maitre d'ouvrage : Communaute d'agglomeration de Sophia Antipolis\n"
    "Objet : construction d'un centre de donnees de 2 MW sur la commune "
    "de Biot.\n"
    "La consultation est allotie en 3 lots.\n"
    "Procedure adaptee ouverte.\n"
)

#: Le règlement de consultation, qui dit AUTRE CHOSE. Sert au test de priorité.
RC = (
    "REGLEMENT DE LA CONSULTATION\n\n"
    "Maitre d'ouvrage : Communaute d'agglomeration de Sophia Antipolis\n"
    "Objet : construction d'un centre de donnees de 2 MW.\n"
    "Le present reglement de la consultation fixe les modalites de remise "
    "des offres.\n"
)
INCONNU_QUI_CONTREDIT = (
    "ANNEXE 7\n"
    "Maitre d'ouvrage : Syndicat mixte du Haut-Var\n"
    "Objet : extension d'un local technique.\n"
)


def _doc(nom, texte, ext=".pdf"):
    return {"nom": nom, "texte": texte, "extension": ext}


def _rubriques_relevees(analyse):
    """Les rubriques que le REMPLISSAGE tire du dossier déposé, et rien d'autre.

    On ne compte ni les saisies, ni les calculs, ni les déclarations : on veut
    mesurer ce que les FICHIERS versent.
    """
    r = A.remplir(fiche={}, analyse=analyse)
    return [(p["cle"], l["cle"], l)
            for p in r["pieces"] for l in p["rubriques"]
            if l["statut"] == "rempli"
            and str(l.get("origine") or "").startswith("Relevé")]


# ═══════════════════════════════════════════════════════════════════════════
#  LA RÈGLE DÉCISIVE : LE FICHIER SERT VRAIMENT
# ═══════════════════════════════════════════════════════════════════════════

def test_le_fichier_non_identifie_le_reste():
    """Il verse, mais il n'est PAS promu au rang de pièce identifiée.

    Le faire entrer dans `pieces` serait une identification qu'on n'a pas
    faite : l'écran dirait « CCTP reconnu » sur un fichier dont personne ne
    sait ce qu'il est. Le classement ne bouge pas ; seul son texte sert.
    """
    a = A.analyser([_doc(NOM_MUET, TEXTE_RICHE)])
    assert a["pieces"] == [], a["pieces"]
    assert [l["fichier"] for l in a["inconnues"]] == [NOM_MUET]


def test_un_fichier_non_identifie_verse_au_remplissage():
    """LA RÈGLE QUI COMPTE. On mesure le nombre de rubriques remplies.

    Sans ce branchement le compte est zéro — c'était l'état du module. La
    mesure porte sur le RÉSULTAT (`remplir`), pas sur la présence d'un appel
    à `relever_sans_piece` : un branchement présent mais inopérant passerait
    une règle de présence et laisserait l'écran vide.
    """
    a = A.analyser([_doc(NOM_MUET, TEXTE_RICHE)])
    lignes = _rubriques_relevees(a)
    assert len(lignes) >= 8, (
        "un fichier portant acheteur, objet, lots et procédure ne verse que "
        "%d rubrique(s) : %r" % (len(lignes), [(p, c) for p, c, _ in lignes]))
    # Et ce sont bien les valeurs du fichier, pas des libellés vides.
    valeurs = {c: l["valeur"] for _, c, l in lignes}
    assert "acheteur" in valeurs, sorted(valeurs)
    assert "Sophia Antipolis" in valeurs["acheteur"], valeurs["acheteur"]


def test_l_apport_vient_bien_du_fichier_inconnu_et_de_lui_seul():
    """Le témoin : on retire les inconnues de l'analyse, le compte retombe.

    C'est la seule façon d'établir la CAUSE. Compter douze rubriques remplies
    ne prouve rien tant qu'on n'a pas montré qu'elles disparaissent quand le
    fichier inconnu n'est plus là.
    """
    a = A.analyser([_doc(NOM_MUET, TEXTE_RICHE)])
    avec = len(_rubriques_relevees(a))
    prive = dict(a, inconnues=[])
    sans = len(_rubriques_relevees(prive))
    assert sans == 0, (
        "sans le fichier inconnu il reste %d rubrique(s) : le témoin ne "
        "prouve plus rien" % sans)
    assert avec > sans, (avec, sans)


def test_les_apports_annonces_sont_ceux_qui_sont_rendus():
    """`apports` est un résumé lisible ; il doit résumer ce qui est là.

    Un résumé qui diverge de la matière est pire qu'absent : il se lit sans
    être vérifié.
    """
    a = A.analyser([_doc(NOM_MUET, TEXTE_RICHE)])
    ligne = a["inconnues"][0]
    assert ligne["apports"] == sorted(r["cle"] for r in ligne["releves"])
    assert ligne["apports"], ligne


# ═══════════════════════════════════════════════════════════════════════════
#  LES DEUX GARDE-FOUS
# ═══════════════════════════════════════════════════════════════════════════

def test_une_piece_identifiee_l_emporte_sur_un_fichier_inconnu():
    """Le RC dit « Sophia Antipolis », l'inconnu dit « Haut-Var ».

    C'est le scénario qui ferait déposer une candidature au nom du mauvais
    acheteur. La valeur retenue doit être celle de la pièce qu'on sait nommer,
    quel que soit l'ordre de dépôt des fichiers.
    """
    for ordre in ((RC, INCONNU_QUI_CONTREDIT), (INCONNU_QUI_CONTREDIT, RC)):
        noms = ["RC.pdf", NOM_MUET] if ordre[0] is RC else [NOM_MUET, "RC.pdf"]
        a = A.analyser([_doc(n, t) for n, t in zip(noms, ordre)])
        idx = A._index_releves(a)
        retenu = idx["acheteur"][0]
        assert retenu["non_identifie"] is False, retenu
        assert "Sophia" in retenu["valeur"], retenu


def test_le_desaccord_d_un_fichier_inconnu_ressort_en_divergence():
    """Il ne gagne pas, mais il ne disparaît pas non plus.

    Un fichier du dossier qui nomme un autre acheteur est un signal : soit il
    n'appartient pas à ce marché, soit le RC a été mal lu. Le taire au motif
    qu'il a perdu l'arbitrage ferait perdre l'information.
    """
    a = A.analyser([_doc("RC.pdf", RC),
                    _doc(NOM_MUET, INCONNU_QUI_CONTREDIT)])
    idx = A._index_releves(a)
    autres = [p for p in idx["acheteur"][1:] if p["non_identifie"]]
    assert autres, idx["acheteur"]
    assert "Haut-Var" in autres[0]["valeur"], autres[0]

    lignes = {c: l for _, c, l in _rubriques_relevees(a)}
    assert lignes["acheteur"].get("divergences"), lignes["acheteur"]
    assert "divergence" in (lignes["acheteur"].get("message") or "").lower()


def test_le_rang_des_inconnus_passe_apres_toute_piece_du_catalogue():
    """La priorité tient à un NOMBRE ; si le catalogue grandit, il doit tenir.

    Une pièce ajoutée au rang 950 renverserait l'ordre en silence — aucune
    autre règle ne le verrait.
    """
    plus_haut = max(p["rang_lecture"] for p in A.PIECES_MARCHE.values())
    assert A.RANG_NON_IDENTIFIE > plus_haut, (A.RANG_NON_IDENTIFIE, plus_haut)


# ═══════════════════════════════════════════════════════════════════════════
#  CE QUE LA VALEUR DIT D'ELLE-MÊME
# ═══════════════════════════════════════════════════════════════════════════

def test_la_valeur_tiree_d_un_fichier_inconnu_se_declare_a_confirmer():
    """Ce qui se recopie sur un formulaire de l'État porte d'où il vient.

    Trois choses à la fois : le drapeau (exploitable par la page), l'origine
    (lisible par l'utilisateur) et le message (qui dit quoi faire). Un drapeau
    sans texte lisible ne protégerait que le programme.
    """
    a = A.analyser([_doc(NOM_MUET, TEXTE_RICHE)])
    lignes = [l for _, c, l in _rubriques_relevees(a) if c == "acheteur"]
    assert lignes, "aucune rubrique acheteur remplie"
    for l in lignes:
        assert l.get("a_confirmer") is True, l
        assert "NON IDENTIFIÉ" in l["origine"], l["origine"]
        assert NOM_MUET in l["origine"], l["origine"]
        assert "confirmez" in (l.get("message") or "").lower(), l.get("message")


def test_une_valeur_venue_d_une_piece_identifiee_ne_porte_pas_ce_drapeau():
    """LE TÉMOIN NÉGATIF. Sans lui, la règle ci-dessus passerait si TOUT
    était marqué « à confirmer » — et le drapeau ne distinguerait plus rien.
    """
    a = A.analyser([_doc("RC.pdf", RC)])
    lignes = [l for _, c, l in _rubriques_relevees(a) if c == "acheteur"]
    assert lignes, "le RC ne verse plus l'acheteur : le témoin est cassé"
    for l in lignes:
        assert not l.get("a_confirmer"), l
        assert "NON IDENTIFIÉ" not in l["origine"], l["origine"]


# ═══════════════════════════════════════════════════════════════════════════
#  CE QU'ON NE PRODUIT PAS
# ═══════════════════════════════════════════════════════════════════════════

def test_un_fichier_inconnu_sans_rien_a_relever_ne_rend_aucune_ligne():
    """Vingt lignes « non trouvé » par fichier inconnu noieraient les vraies.

    Sur une pièce identifiée, « non trouvé » informe — un CCAP sans pénalités
    se remarque. Sur un fichier dont on ignore la nature, cela n'apprend rien.
    """
    a = A.analyser([_doc("truc.pdf", "Bonjour, ceci est une note de service.")])
    ligne = a["inconnues"][0]
    assert "releves" not in ligne, ligne
    assert "apports" not in ligne, ligne
    assert _rubriques_relevees(a) == []


def test_un_fichier_inconnu_sans_texte_ne_casse_rien():
    """Une archive, un PDF image : aucun texte extrait, donc aucun relevé.

    (Un .dwg ne convient PAS comme cas d'essai : `_EXT_INDICE` le range en
    « plans » sur sa seule extension. C'est le bon comportement, et c'est
    pourquoi l'archive sert ici de fichier vraiment inclassable.)
    """
    a = A.analyser([_doc("annexe-7.zip", "", ".zip")])
    assert a["inconnues"], a
    assert "releves" not in a["inconnues"][0], a["inconnues"][0]
    assert _rubriques_relevees(a) == []


def test_relever_sans_piece_ne_rend_que_ce_qu_il_a_trouve():
    """Chaque ligne rendue porte des citations ET son avertissement.

    Une ligne `trouve: True` sans citation ferait afficher une valeur venue de
    nulle part.
    """
    lignes = A.relever_sans_piece(TEXTE_RICHE)
    assert lignes
    cles = {r["cle"] for r in A.RELEVES}
    for r in lignes:
        assert r["trouve"] is True, r
        assert r["citations"], r
        assert r["non_identifie"] is True, r
        assert r["cle"] in cles, r
        assert "PISTE" in r["note"], r["note"]



def test_relever_sans_piece_cherche_au_dela_des_pieces_d_un_seul_type():
    """Il ne doit pas se restreindre à ce qu'une pièce donnée porterait.

    C'est tout l'intérêt : on ne sait pas ce qu'on tient, donc on cherche
    tout. Un texte qui porte des relevés visant des pièces DIFFÉRENTES doit
    les rendre tous.
    """
    lignes = A.relever_sans_piece(TEXTE_RICHE)
    cles = {r["cle"] for r in lignes}
    par_cle = {r["cle"]: set(r["pieces"]) for r in A.RELEVES}
    pieces_visees = set()
    for c in cles:
        pieces_visees |= par_cle[c]
    assert len(cles) >= 3, sorted(cles)
    assert len(pieces_visees) >= 2, (sorted(cles), sorted(pieces_visees))


# ═══════════════════════════════════════════════════════════════════════════
#  CE QUE L'ÉCRAN EN MONTRE
# ═══════════════════════════════════════════════════════════════════════════
# POURQUOI CES RÈGLES EXISTENT. Le gain de ce tour est invisible s'il reste
# dans le JSON : l'utilisateur continue de lire « non reconnu » et d'en
# conclure que son dépôt n'a servi à rien. Et une mise en garde posée dans une
# couleur illisible est pire qu'absente — le premier essai posait #9C3C20 sur
# --panel, soit 1,32:1. Mesuré, pas supposé.
import html
import io
import json
import os
import re
import subprocess

from test_ao_formulaires import _js_source          # noqa: E402

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _lire(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


def _luminance(hexa):
    h = hexa.lstrip("#")
    def lin(c):
        c = int(h[c:c + 2], 16) / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return .2126 * lin(0) + .7152 * lin(2) + .0722 * lin(4)


def _contraste(a, b):
    la, lb = _luminance(a), _luminance(b)
    return (max(la, lb) + .05) / (min(la, lb) + .05)


def _rendu_analyse(analyse):
    """Le HTML que `aoRendre` produit RÉELLEMENT, obtenu en l'exécutant.

    POURQUOI EXÉCUTER ET NON RELIRE — LA LEÇON D'UNE MUTATION DE CE TOUR. La
    première version de cette règle cherchait « p.releves » et « r.citations »
    dans le fichier. Mettre le bloc dans une branche morte — `if (false)` —
    les y laissait : la règle restait VERTE pendant que l'écran ne montrait
    plus rien. Une règle qui constate la présence d'un code ne mesure pas
    qu'il s'exécute. (Le même piège est consigné dans test_ao_lot.py : c'est
    la deuxième fois, d'où ce banc.)
    """
    prog = (_js_source("esc", "info", "aoIgnores", "aoRendre")
            + "\nvar zone = { innerHTML: '' }, ignores = { innerHTML: '' };"
            + "\nfunction $(s) { return s === '#ig-ao-out' ? zone"
              " : (s === '#ig-ao-ign' ? ignores : null); }"
            + "\nvar CADRE = { glossaire: {} };"
            + "\nglobal.document = { querySelectorAll: function () { return []; },"
              " querySelector: function () { return null; } };"
            + "\naoRendre(JSON.parse(process.env.AO_ANALYSE));"
            + "\nprocess.stdout.write(zone.innerHTML);\n")
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60,
                         env=dict(os.environ, AO_ANALYSE=json.dumps(analyse)))
    assert out.returncode == 0, out.stderr[-2000:]
    return html.unescape(out.stdout)


def test_la_page_montre_ce_qu_un_fichier_non_reconnu_a_quand_meme_donne():
    """Le bloc des inconnues rend leurs relevés — mesuré sur le HTML produit.

    Sans cela le gain reste dans le JSON : l'utilisateur lit « non reconnu »
    et en conclut, comme avant, que son dépôt n'a servi à rien.
    """
    a = A.analyser([_doc(NOM_MUET, TEXTE_RICHE)])
    h = _rendu_analyse(a)
    assert NOM_MUET in h, h[:400]
    assert "Sophia Antipolis" in h, (
        "l'écran ne montre pas ce que le fichier non reconnu a donné")
    assert "EN DERNIER" in h, (
        "l'écran présente ces valeurs comme des sources ordinaires")


def test_l_ecran_ne_fabrique_pas_ce_bloc_quand_il_n_y_a_rien_a_montrer():
    """LE TÉMOIN NÉGATIF du banc : un fichier inconnu muet ne produit
    ni avertissement ni citation — sinon la règle ci-dessus passerait sur un
    bloc affiché en toutes circonstances."""
    a = A.analyser([_doc("truc.pdf", "Bonjour, ceci est une note de service.")])
    h = _rendu_analyse(a)
    assert "truc.pdf" in h, h[:400]
    assert "EN DERNIER" not in h, h


def test_la_mise_en_garde_a_une_couleur_lisible_sur_le_fond_de_la_page():
    """LA RÈGLE QUI MESURE. `.ig-ao-og-conf` doit se voir.

    Le contraste est CALCULÉ contre les trois fonds où la ligne peut se poser
    — --panel, --panel2, --bg — et non constaté par la présence d'une
    déclaration de couleur. C'est exactement la différence qui avait laissé
    passer un rouge à 1,32:1.
    """
    page = _lire("ingenierie-datacenter.html")
    m = re.search(r"\.ig-ao-og-conf\{[^}]*color:\s*var\(--([\w-]+)\s*,\s*"
                  r"(#[0-9A-Fa-f]{6})\)", page)
    assert m, "la couleur de .ig-ao-og-conf n'est pas lisible dans la feuille"
    nom, repli = m.group(1), m.group(2)

    css = _lire("styles.css")
    mv = re.search(r"--%s\s*:\s*(#[0-9A-Fa-f]{6})" % re.escape(nom), css)
    assert mv, "la variable --%s n'est déclarée nulle part" % nom
    assert mv.group(1).lower() == repli.lower(), (
        "le repli (%s) ne vaut pas la variable (%s) : sur un navigateur qui "
        "n'a pas la variable, la couleur change" % (repli, mv.group(1)))

    fonds = {}
    for v in ("panel", "panel2", "bg"):
        mf = re.search(r"--%s\s*:\s*(#[0-9A-Fa-f]{6})" % v, css)
        assert mf, v
        fonds[v] = mf.group(1)
    for v, f in fonds.items():
        c = _contraste(mv.group(1), f)
        assert c >= 3.0, (
            "la mise en garde tient %.2f:1 sur --%s : elle disparaît" % (c, v))


def test_la_couleur_decorative_reste_interdite_au_texte_de_cette_ligne():
    """--terra est réservée aux bordures et dégradés ; la feuille le dit.

    Le témoin : si un jour `.ig-ao-og-conf` passait sur --terra, le contraste
    retomberait sans qu'aucune autre règle ne le voie.
    """
    page = _lire("ingenierie-datacenter.html")
    m = re.search(r"\.ig-ao-og-conf\{([^}]*)\}", page)
    assert m, "la règle a disparu"
    assert "--terra" not in m.group(1), m.group(1)


def test_l_origine_non_identifiee_se_distingue_a_l_ecran():
    """La classe qui sort l'avertissement du gris atteint VRAIMENT le HTML.

    Mesurée en exécutant `aoRempliRendre`, pour la même raison que ci-dessus :
    une mutation qui remplace `l.a_confirmer` par `false` laisse la classe
    écrite dans le fichier — seule l'exécution le voit.

    LE TÉMOIN NÉGATIF EST DANS LA MÊME RÈGLE : la classe ne doit PAS apparaître
    quand le dossier n'a que des pièces identifiées, sinon elle ne distingue
    rien et l'avertissement devient du décor.
    """
    from test_ao_formulaires import _carte_rendue

    inconnu = A.analyser([_doc(NOM_MUET, TEXTE_RICHE)])
    h = _carte_rendue(A.remplir(fiche={}, analyse=inconnu))
    assert "ig-ao-og-conf" in h, (
        "l'origine d'un fichier non identifié se rend comme toutes les autres")
    assert "FICHIER NON IDENTIFIÉ" in h, h[:400]

    identifie = A.analyser([_doc("RC.pdf", RC)])
    h2 = _carte_rendue(A.remplir(fiche={}, analyse=identifie))
    assert "Relevé dans RC" in h2, "le témoin est cassé : le RC ne verse plus"
    assert "ig-ao-og-conf" not in h2, (
        "la classe d'avertissement s'applique aussi aux pièces identifiées : "
        "elle ne distingue plus rien")
