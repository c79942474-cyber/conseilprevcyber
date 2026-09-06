# -*- coding: utf-8 -*-
"""Quels moteurs tracent — et le site ne promet pas plus qu'ils ne tiennent.

CE QUI A ÉTÉ TROUVÉ EN MESURANT. Le site affirmait, sur deux pages publiques,
que « chaque valeur porte sa formule ». Mesuré en faisant tourner les moteurs :
QUATRE sur quatorze produisent une équation substituable — énergie, eau,
carbone, chaleur. Les dix autres n'en produisent aucune, et la page
/datacenter, qui portait la promesse, sert justement un panneau « équipements »
sans la moindre trace.

LA PROMESSE A DONC ÉTÉ RESSERRÉE, et une règle la tient désormais à la mesure :
si un moteur perd ses équations, ou si la promesse se relâche, l'une des deux
tombe.
"""
import os
import re
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import tracabilite as T                                          # noqa: E402

ORIGINE = {"Origin": "http://localhost"}
ETAT = T.etat()


def lire(nom):
    with open(os.path.join(ICI, nom), encoding="utf-8") as f:
        return f.read()


# ── LA MESURE MESURE ──────────────────────────────────────────────────────

def test_tous_les_moteurs_declares_sont_JOIGNABLES():
    """Un moteur qu'on ne sait pas appeler n'est pas un moteur sans équation.

    La distinction n'est pas théorique : au premier passage, DOUZE moteurs sur
    quinze sont sortis « non joignables » parce que j'avais deviné leurs
    signatures. Sans cette séparation, le rapport aurait accusé le code d'un
    défaut qui était dans la mesure.
    """
    assert ETAT["non_joignables"] == [], ETAT["non_joignables"]
    assert ETAT["joignables"] == ETAT["moteurs"] >= 14, ETAT["moteurs"]


def test_les_quatre_degres_de_tracabilite_sont_comptes_SEPAREMENT():
    """Les additionner ferait passer une méthode lisible pour une équation
    vérifiable — c'est exactement l'amalgame que ce module défait."""
    assert ETAT["equations"] > 0, "aucune équation nulle part"
    assert ETAT["formules_seules"] > 0, (
        "plus aucune formule sans entrées : le témoin du degré 3 a disparu, "
        "et la règle ne distingue plus rien")
    assert ETAT["traces_seules"] > 0, "plus aucune trace sans formule"
    for l in ETAT["lignes"]:
        somme = l["equations"] + l["formules_seules"] + l["traces_seules"]
        assert somme == l["traces"], (l["cle"], somme, l["traces"])


def test_le_triptyque_trace_ses_equations():
    """Le témoin POSITIF. Sans lui, une mesure qui rendrait zéro partout
    passerait pour un constat au lieu d'être une panne."""
    par_cle = {l["cle"]: l for l in ETAT["lignes"]}
    for cle in ("energie", "eau", "carbone", "chaleur"):
        assert par_cle[cle]["equations"] >= 3, (cle, par_cle[cle]["equations"])


def test_les_moteurs_sans_equation_sont_NOMMES_un_par_un():
    """Un pourcentage global laisserait croire à une couverture uniforme."""
    sans = ETAT["sans_equation"]
    assert sans, "la mesure ne trouve plus aucun moteur sans équation"
    for x in sans:
        assert x["nom"] and x["page"], x
        assert x["cle"] not in ETAT["avec_equation"], x["cle"]


def test_une_equation_exige_la_formule_ET_les_entrees():
    """C'est la définition du degré 4, et elle décide de tout le décompte."""
    assert T._degre({"formule": "a = b × c", "entrees": {"b": 1, "c": 2}}) == "equation"
    assert T._degre({"formule": "a = b × c", "entrees": {}}) == "formule_seule"
    assert T._degre({"formule": "a = b × c"}) == "formule_seule"
    assert T._degre({"nom": "x", "valeur": 1}) == "trace_seule"


def test_le_parcours_ne_tourne_pas_en_rond():
    """Un moteur qui rendrait un objet cyclique ferait boucler la mesure —
    et une mesure qui ne rend rien ne mesure rien."""
    a = {"nom": "x", "valeur": 1}
    a["moi"] = a
    assert len(T.parcourir(a)) == 1


def test_le_rapport_est_serialisable_en_JSON():
    """Chaque moteur porte son appel — une FONCTION. La laisser dans le
    rapport ferait échouer la route qui le sert, sur un module dont le seul
    rôle est de dire la vérité sur les autres."""
    import json
    json.dumps(ETAT)
    for l in ETAT["lignes"]:
        assert "lancer" not in l, l["cle"]


# ── ET LA PROMESSE PUBLIQUE NE DÉPASSE PAS LA MESURE ──────────────────────

# LES DEUX PAGES QUI PROMETTAIENT TROP. Elles servent des moteurs sans
# équation — /datacenter porte le panneau « équipements », qui n'a aucune
# trace.
#
# DEUX AUTRES ENDROITS DISENT LA MÊME PHRASE ET SONT JUSTES, parce que leur
# PORTÉE est le triptyque : la docstring de `datacenter.py`, qui EST le moteur
# du triptyque, et la description du livrable « Note de calcul — énergie, eau
# et carbone », qui ne couvre que lui. Les corriger aurait affaibli deux
# affirmations vraies ; la faute n'était pas la phrase mais son périmètre.
PAGES_QUI_PROMETTENT = ("datacenter.html", "faq.html")
PORTEE_JUSTE = ("datacenter.py", "livrables.py")


def test_aucune_page_publique_ne_promet_la_formule_pour_TOUTE_valeur():
    """LA RÈGLE QUI TIENT LE TOUT.

    « Chaque valeur porte sa formule » est faux depuis que la page sert des
    moteurs qui n'en portent pas. La promesse doit nommer son périmètre — le
    triptyque — et dire que les autres n'en produisent pas.
    """
    for nom in PAGES_QUI_PROMETTENT:
        page = lire(nom)
        for trop in ("Chaque valeur porte sa formule",
                     "Chaque résultat porte sa formule"):
            assert trop not in page, (
                "%s promet la formule pour TOUTE valeur, alors que %d moteurs "
                "sur %d n'en produisent aucune"
                % (nom, len(ETAT["sans_equation"]), ETAT["joignables"]))
        assert "triptyque" in page, (
            "%s ne dit plus de QUOI la promesse est vraie" % nom)
        assert "sans équation vérifiable" in page or "n'en produisent pas" in page, (
            "%s ne dit pas que les autres moteurs n'en produisent pas" % nom)


def test_la_phrase_reste_intacte_la_ou_sa_PORTEE_est_le_triptyque():
    """LE TÉMOIN NÉGATIF de la règle précédente.

    Sans lui, on satisferait la règle en supprimant la phrase partout — y
    compris là où elle est vraie. Ce qui était faux n'était pas la phrase,
    c'était son périmètre.
    """
    for nom in PORTEE_JUSTE:
        page = lire(nom)
        assert "porte sa formule" in page, (
            "%s a perdu une affirmation qui était JUSTE : sa portée est le "
            "triptyque, qui trace bel et bien" % nom)


def test_la_FAQ_dit_la_meme_chose_dans_son_balisage_et_dans_sa_page():
    """La réponse est écrite deux fois : visible, et recopiée dans le JSON-LD.

    CETTE RÈGLE A ÉTÉ REPRISE : elle ne comparait qu'une PHRASE D'OUVERTURE.
    Une mutation qui changeait la fin de la réponse dans une seule des deux
    copies ne faisait rien tomber — les deux commençaient toujours pareil.
    On compare donc la RÉPONSE ENTIÈRE, ce qui est le sens de « dit la même
    chose ». C'est le balisage qui est cité par les moteurs de recherche : le
    laisser diverger fait répondre au site autre chose que ce qu'il affiche.
    """
    import json
    page = lire("faq.html")
    blocs = re.findall(r"<script[^>]*ld\+json[^>]*>(.*?)</script>", page, re.S)
    assert blocs, "la FAQ n'a plus de balisage"

    def net(t):
        t = re.sub(r"<[^>]+>", "", t)
        return " ".join(t.replace("&nbsp;", " ").replace("&amp;", "&").split())

    balise = []
    for b in blocs:
        d = json.loads(b)
        for q in d.get("mainEntity", []):
            balise.append(net((q.get("acceptedAnswer") or {}).get("text", "")))
    visibles = [net(x) for x in re.findall(r'<div class="ans">(.*?)</div>',
                                           page, re.S)]
    assert balise and visibles, (len(balise), len(visibles))
    manquantes = [b for b in balise if b not in visibles]
    assert not manquantes, (
        "le balisage dit une chose que la page n'affiche pas : « %s… »"
        % manquantes[0][:160])


def test_la_mesure_n_est_servie_qu_a_l_administration(anonyme, connecte):
    for c in (anonyme, connecte):
        r = c.get("/api/admin/tracabilite", headers=ORIGINE)
        assert r.status_code in (401, 403), r.status_code


def test_l_administration_recoit_la_mesure_et_la_page_l_affiche(admin):
    r = admin.get("/api/admin/tracabilite", headers=ORIGINE)
    assert r.status_code == 200, r.status_code
    j = r.get_json()
    assert j["ok"] and j["tracabilite"]["moteurs"] >= 14
    page = lire("admin-rgpd.html")
    assert "/api/admin/tracabilite" in page, "la page ne demande pas la mesure"
    assert "AUCUNE" in page, "l'écran ne nomme pas l'absence d'équation"
