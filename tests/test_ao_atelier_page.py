# -*- coding: utf-8 -*-
"""L'ATELIER, VU DE LA PAGE — ce que le bouton envoie vraiment.

POURQUOI CE FICHIER EXISTE. `tests/test_ao_atelier.py` éprouve le moteur :
la boucle, l'éventail, les rejets, les réclamations. Il le fait en appelant
`ao_atelier.atelier(documents=[{"nom": …, "texte": …}])` — avec le bon champ,
puisque c'est le test qui le compose. Rien n'éprouvait le TRAJET : la page
envoyait `AO_DOCS`, dont les entrées portent `contenu` (le base64 du
téléversement) et jamais `texte`. La route remplaçait donc chaque pièce par
une chaîne vide, l'atelier partait pour dix-huit appels de modèle sur un
dossier sans un caractère, ne retrouvait aucune citation, refusait tout, et
consommait un des six passages de la demi-heure.

Un moteur vert et un bouton inerte : le défaut ne vivait ni dans l'un ni dans
l'autre, mais dans l'espace entre les deux. Les règles ci-dessous mesurent cet
espace — elles lisent le nom du champ DANS la route, et exigent que la page
l'émette. Aucune ne se satisfait d'un mot trouvé dans un commentaire.
"""
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)


def lire(nom):
    with open(os.path.join(ICI, nom), encoding="utf-8") as f:
        return f.read()


def sans_commentaires_js(src):
    """Ôte blocs et lignes de commentaire : une règle ne doit pas pouvoir
    être satisfaite par de la prose."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", " ", src)


def corps_route_atelier():
    """Le corps de `api_datacenter_marche_atelier`, jusqu'à la route suivante."""
    py = lire("app.py")
    d = py.index("def api_datacenter_marche_atelier(")
    f = py.index("@app.route(", d)
    return py[d:f]


def champs_lus_par_la_route():
    """Les champs que la route lit sur CHAQUE document reçu."""
    corps = corps_route_atelier()
    m = re.search(r"documents\s*=\s*\[\{(.+?)\}\s*\n?\s*for d in documents",
                  corps, re.S)
    assert m, "la route ne recompose plus les documents comme attendu"
    return set(re.findall(r'd\.get\(\s*"([a-z_]+)"', m.group(1)))


def corps_js(nom_fonction):
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    m = re.search(r"function %s\s*\([^)]*\)\s*\{" % re.escape(nom_fonction), js)
    assert m, "fonction introuvable : " + nom_fonction
    i, prof = m.end(), 1
    while i < len(js) and prof:
        if js[i] == "{":
            prof += 1
        elif js[i] == "}":
            prof -= 1
        i += 1
    return js[m.end():i - 1]


# ═══════════════════════════════════════════════════════════════════════════
#  1. LE CHAMP ENVOYÉ EST CELUI QUE LA ROUTE LIT
# ═══════════════════════════════════════════════════════════════════════════

def test_la_page_emet_exactement_les_champs_que_la_route_lit():
    """LA RÈGLE QUI MANQUAIT. Elle ne vérifie pas que la page dit « texte » :
    elle LIT dans la route le nom du champ, et exige que la page l'émette.
    Renommer le champ d'un côté seulement fait tomber la règle."""
    attendus = champs_lus_par_la_route()
    assert attendus, "aucun champ lu : l'extraction de la route a dérivé"
    emis = set(re.findall(r"([a-z_]+)\s*:",
                          re.search(r"out\.push\(\{(.*?)\}\)",
                                    corps_js("atelierDocuments"), re.S).group(1)))
    assert emis == attendus, (
        "la page envoie %s alors que la route lit %s" % (sorted(emis), sorted(attendus)))


def test_le_texte_est_bien_le_champ_en_jeu():
    """Témoin : si la route cessait de lire « texte », la règle précédente
    resterait verte en accompagnant la dérive. Celle-ci fixe le point."""
    assert "texte" in champs_lus_par_la_route()


def test_le_bouton_n_envoie_plus_le_televersement_brut():
    """`AO_DOCS` porte `contenu`, le base64 lu par `aoLire` — jamais `texte`.
    L'envoyer tel quel était le défaut."""
    corps = corps_js("atelierLancer")
    assert "atelierDocuments()" in corps
    assert not re.search(r"documents\s*:\s*AO_DOCS", corps), (
        "l'atelier repart avec le téléversement brut")


# ═══════════════════════════════════════════════════════════════════════════
#  2. UNE PIÈCE SANS TEXTE NE PART PAS, ET NE PASSE PAS POUR PRÊTE
# ═══════════════════════════════════════════════════════════════════════════

def test_une_piece_sans_texte_est_ecartee_de_l_envoi():
    """La règle porte sur la PROPRIÉTÉ, pas sur l'orthographe de la garde :
    le `push` doit être commandé par une condition qui éprouve à la fois le
    TYPE de `t` et sa non-vacuité. Écrite contre une formulation précise, elle
    serait tombée sur une réécriture équivalente — et aurait fait corriger du
    code juste."""
    corps = corps_js("atelierDocuments")
    m = re.search(r"if\s*\((.+?)\)\s*out\.push\(", corps, re.S)
    assert m, "le push n'est plus commandé par une condition"
    garde = m.group(1)
    assert "typeof t" in garde, "le type de t n'est pas éprouvé"
    assert re.search(r"&&\s*t\b|\|\|\s*!t\b", garde), (
        "une pièce au texte vide n'est pas écartée")


def test_le_bouton_se_mesure_sur_ce_qu_il_peut_envoyer():
    """LE DÉFAUT SYMÉTRIQUE. S'armer sur `AO_DOCS.length` allumait le bouton
    à la reprise d'un projet, où `AO_DOCS` est reconstruit avec `texte: ""`."""
    corps = corps_js("atelierArmer")
    assert "atelierDocuments()" in corps
    assert not re.search(r"disabled\s*=\s*!+\(?\s*AO_DOCS\s*&&\s*AO_DOCS\.length",
                         corps), "le bouton s'arme encore sur le nombre de fichiers"


def test_l_etat_distingue_le_dossier_absent_du_texte_manquant():
    """Deux causes, deux phrases. « Déposez d'abord les pièces » devant un
    dossier déjà déposé enverrait chercher ce qui est déjà là."""
    corps = corps_js("atelierArmer")
    assert "AO_DOCS && AO_DOCS.length" in corps, (
        "l'état ne distingue plus les deux causes")
    assert corps.count("e.textContent") >= 3


# ═══════════════════════════════════════════════════════════════════════════
#  3. L'ORDRE : ON S'ARME APRÈS AVOIR POSÉ LE TEXTE
# ═══════════════════════════════════════════════════════════════════════════

def test_l_atelier_s_arme_apres_que_le_texte_a_ete_pose():
    """Armé une ligne trop tôt, le bouton resterait éteint alors que tout est
    là — et la règle précédente, elle, serait verte."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    pose = js.index("aoTextesPoser(j.textes, true)")
    apres = js.index("atelierArmer()", pose)
    avant = js.rfind("atelierArmer()", 0, pose)
    # Il y a bien un armement APRÈS la pose du texte, et aucun entre
    # l'affectation de AO_DOCS et cette pose.
    assert apres > pose
    depot = js.index("AO_DOCS = docs")
    assert avant < depot, "l'atelier s'arme encore avant que le texte soit posé"


def test_la_reprise_d_un_projet_arme_l_atelier():
    """On revenait sur un projet, le relevé réapparaissait, et le bouton
    restait éteint en réclamant un dépôt que le coffre avait déjà rendu."""
    assert "atelierArmer()" in corps_js("aoProjetReprendre")


def test_le_coffre_pose_son_texte_avant_la_reprise():
    """Sans cet ordre, `atelierArmer` dans la reprise mesurerait un
    `AO_TEXTES` encore vide — vert ici, éteint dans la page.

    LA PREMIÈRE ÉCRITURE DE CETTE RÈGLE ÉTAIT FAUSSE, et la mutation l'a
    montrée : `js.index(x, pose)` cherche À PARTIR de `pose`, donc le résultat
    était toujours supérieur à `pose`. La règle était verte par construction —
    elle ne pouvait pas tomber, quel que soit l'ordre réel. On compare
    désormais des positions absolues, et l'APPEL est distingué de la
    DÉFINITION (`function aoProjetReprendre()`), qui vit plus bas dans le
    fichier et rendrait la comparaison toujours favorable."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    pose = js.index("aoTextesPoser(aoTextesDuCoffre(")
    appels = [m.start() for m in
              re.finditer(r"(?<!function )aoProjetReprendre\(\)", js)]
    assert appels, "aoProjetReprendre n'est plus appelée nulle part"
    assert min(appels) > pose, (
        "la reprise passe avant que le coffre ait posé son texte")


# ═══════════════════════════════════════════════════════════════════════════
#  4. CE QUE LA ROUTE REFUSE, ELLE LE DIT
# ═══════════════════════════════════════════════════════════════════════════

def test_la_route_refuse_un_dossier_vide_en_le_disant():
    corps = corps_route_atelier()
    assert '"sans_dossier"' in corps
    assert "400" in corps
