# -*- coding: utf-8 -*-
"""LA CHAÎNE D'AUTONOMIE — CE QUE LE MODULE PROMET, MESURÉ.

CE QUI A DÉCIDÉ DE CE FICHIER. Les deux plateformes du cabinet portaient onze
modules traitant de l'IA et aucun ne mesurait une attaque : la matrice de
risques positionnait selon la « probabilité de NON-CONFORMITÉ », le radar sur
des dimensions RÉGLEMENTAIRES. Le module mesuré ici comble ce trou, et il
repose sur une affirmation qui doit être éprouvée plutôt que crue :

    UNE CHAÎNE VAUT SON MAILLON LE PLUS FAIBLE, JAMAIS SA MOYENNE.

C'est la première règle de ce fichier, et c'est celle qui compte. Un
raisonnement remarquablement encadré derrière un maillon d'action grand ouvert
produit un incident ; une moyenne des cinq dirait que tout va plutôt bien. La
règle construit donc un cas où le maximum et la moyenne divergent fortement —
quatre maillons fermés, un ouvert à fond — et exige le maximum. Une
implémentation qui moyennerait rendrait 0,8 au lieu de 4.

À NE PAS CONFONDRE AVEC `tests/test_securite_ia.py`, qui garde `garde_ia` — la
DÉFENSE du cabinet contre l'injection indirecte. Ici c'est la MÉTHODE vendue au
client. Les deux fichiers ont failli n'en faire qu'un par voisinage de nom.
"""
import io
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import chaine_autonomie as CA  # noqa: E402

ORIGINE = {"Origin": "http://localhost"}


def _plat(d):
    return {m["cle"]: d for m in CA.MAILLONS}


# ══════════════════════════════════════════════════════════════════════════
#  1. LE PIRE MAILLON COMMANDE — LA RÈGLE QUI PORTE LE MODULE
# ══════════════════════════════════════════════════════════════════════════

def test_l_indice_est_le_PIRE_ecart_et_JAMAIS_la_moyenne():
    """QUATRE MAILLONS FERMÉS, UN GRAND OUVERT.

    Écarts : 4, 0, 0, 0, 0. Le maximum vaut 4 ; la moyenne vaut 0,8. Une
    implémentation qui moyennerait rendrait « presque rien » là où un maillon
    laisse tout passer — et c'est précisément le rapport qu'on présenterait en
    comité pour conclure que la situation est saine."""
    a, t = _plat(0), _plat(0)
    cible = CA.MAILLONS[3]["cle"]
    a[cible] = 4
    d = CA.evaluer(a, t)
    assert d["ok"]
    ecarts = [l["ecart"] for l in d["maillons"]]
    moyenne = sum(ecarts) / float(len(ecarts))
    assert moyenne < 1, moyenne
    assert d["ecart_max"] == 4, (
        "l'écart rendu est %s au lieu de 4 : une moyenne s'est-elle glissée "
        "dans le calcul ? (moyenne des cinq : %.2f)" % (d["ecart_max"], moyenne))
    assert d["commande"] == cible
    assert d["ouverts"] == [cible]


def test_a_ecart_egal_c_est_le_maillon_le_plus_TARDIF_qui_commande():
    """L'ORDRE DES MAILLONS PORTE UNE INFORMATION. À écart égal, le maillon le
    plus tardif l'emporte : tout ce qui le précède a déjà été franchi, et c'est
    là que la conséquence se paie. Désigner le premier ferait travailler le
    client sur un maillon que l'attaquant a déjà dépassé."""
    a, t = _plat(0), _plat(0)
    premier, dernier = CA.MAILLONS[0]["cle"], CA.MAILLONS[-1]["cle"]
    a[premier] = a[dernier] = 3
    d = CA.evaluer(a, t)
    assert d["ecart_max"] == 3
    assert d["commande"] == dernier, (
        "à écart égal, %s commande au lieu du maillon le plus tardif (%s)"
        % (d["commande"], dernier))


def test_un_maillon_non_renseigne_n_est_PAS_un_maillon_a_zero():
    """LE COMPTER POUR ZÉRO FERAIT REMONTER UNE ALERTE SUR DU VIDE, et le
    lecteur cesserait de croire l'écran au deuxième essai."""
    cible = CA.MAILLONS[1]["cle"]
    d = CA.evaluer({cible: 3}, {cible: 1})
    vides = [l for l in d["maillons"] if l["cle"] != cible]
    assert vides, "le relevé ne compte qu'un maillon : la règle ne mesure rien"
    for l in vides:
        assert l["autonomie"] is None and l["maitrise"] is None, l
        assert l["ecart"] is None and not l["ouvert"], l
    assert d["renseignes"] == 1
    r = CA.restitution_ebios({cible: 3}, {cible: 1})
    assert [s["maillon"] for s in r["scenarios"]] == [cible]


def test_un_degre_hors_echelle_ou_illisible_vaut_NON_RENSEIGNE():
    """Ni zéro, ni le maximum : un nombre qui n'est pas un degré n'est pas un
    degré. Le borner silencieusement inventerait une mesure."""
    cible = CA.MAILLONS[0]["cle"]
    for valeur in (9, -1, "beaucoup", None):
        d = CA.evaluer({cible: valeur}, {cible: 2})
        l = [x for x in d["maillons"] if x["cle"] == cible][0]
        assert l["autonomie"] is None, (valeur, l["autonomie"])


def test_un_maillon_inconnu_est_REFUSE_et_pas_ignore():
    """L'ignorer laisserait croire que la chaîne a été cotée entièrement."""
    d = CA.evaluer({"cantine": 2}, {})
    assert not d["ok"] and d["erreur"] == "maillons_inconnus"
    assert d["maillons"] == ["cantine"]


# ══════════════════════════════════════════════════════════════════════════
#  2. LA TABLE NE MENT PAS
# ══════════════════════════════════════════════════════════════════════════

def test_chaque_menace_vise_un_maillon_qui_existe():
    """UNE MENACE MAL RATTACHÉE NE LÈVE AUCUNE ERREUR À L'USAGE : elle
    disparaît du relevé, et le maillon qu'elle visait paraît plus sain qu'il ne
    l'est. C'est le défaut le moins visible d'une table de correspondance."""
    cles = {m["cle"] for m in CA.MAILLONS}
    perdues = [m["cle"] for m in CA.MENACES if m["maillon"] not in cles]
    assert not perdues, perdues
    assert len(CA.MENACES) >= 13, len(CA.MENACES)


def test_aucun_maillon_n_est_sans_menace_ni_sans_evenement_redoute():
    """Un maillon qu'aucune menace ne vise fait répondre à une question dont la
    réponse ne change rien — et il dilue l'écart en restant toujours fermé."""
    vises = {m["maillon"] for m in CA.MENACES}
    for m in CA.MAILLONS:
        assert m["cle"] in vises, m["cle"]
        assert m["cle"] in CA.REDOUTES, m["cle"]
        assert len(m["socle"]) >= 3, (m["cle"], m["socle"])


def test_les_trois_familles_ANSSI_ne_sont_pas_avalees_par_OWASP():
    """DEUX CATALOGUES QUI NE SE RECOUVRENT PAS, et c'est la raison d'en tenir
    deux. Les dix risques agentiques décrivent l'atteinte PAR l'agent ; les
    trois familles ANSSI décrivent l'atteinte AU MODÈLE. Un module qui n'aurait
    gardé qu'OWASP serait aveugle à l'empoisonnement d'un jeu d'entraînement."""
    cles = {m["cle"] for m in CA.MENACES}
    assert {"ANSSI-INF", "ANSSI-MAN", "ANSSI-EXF"} <= cles, sorted(cles)
    assert len([c for c in cles if c.startswith("ASI")]) == 10, sorted(cles)


# ══════════════════════════════════════════════════════════════════════════
#  3. LES SOURCES, ET CE QU'ON A LE DROIT D'EN FAIRE
# ══════════════════════════════════════════════════════════════════════════

def test_aucune_source_n_est_declaree_certifiable():
    """« CONFORME ISO 27090 » NE VEUT RIEN DIRE et ne doit jamais être écrit :
    le texte est informatif et ne porte aucune exigence. Plus largement, aucune
    de ces huit sources ne se certifie sur la base d'un relevé de chaîne. Le
    jour où l'une passerait à `certifiable: True`, c'est une promesse
    commerciale qui serait engagée — cette règle demande qu'on la prenne
    exprès."""
    certifiables = [s["cle"] for s in CA.SOURCES if s["certifiable"]]
    assert not certifiables, certifiables


def test_les_sources_reutilisables_sont_celles_sous_licence_ouverte():
    """CE CHAMP DÉCIDE DE CE QU'ON PEUT BÂTIR. Deux sources sont sous Licence
    Ouverte : elles s'adaptent, y compris commercialement, avec mention de
    paternité. Les six autres se citent. Les ranger sur la même étagère ferait
    tôt ou tard recopier le mauvais texte."""
    ouvertes = {s["cle"] for s in CA.SOURCES if s["reutilisable"]}
    assert ouvertes == {"pa048", "pa102"}, sorted(ouvertes)
    for s in CA.SOURCES:
        if s["reutilisable"]:
            assert "Licence Ouverte" in s["licence"], (s["cle"], s["licence"])


def test_chaque_source_porte_sa_reserve():
    """UNE SOURCE DONT ON NE DIT PAS LA LIMITE FINIT CITÉE HORS DE SON DOMAINE.
    Le Code of Practice s'adresse aux fournisseurs de modèles à usage général ;
    prEN 18286 est un PROJET. Les citer sans cela serait faux."""
    courtes = [s["cle"] for s in CA.SOURCES if len(s.get("reserve") or "") < 60]
    assert not courtes, courtes


# ══════════════════════════════════════════════════════════════════════════
#  4. LA RESTITUTION, ET LE DOCUMENT QUI CIRCULE SANS SA PAGE
# ══════════════════════════════════════════════════════════════════════════

def test_la_restitution_emploie_le_vocabulaire_du_GUIDE_et_pas_le_notre():
    """C'EST TOUT L'INTÉRÊT DE LA SECONDE SORTIE. La chaîne mesure bien et ne
    se défend pas — aucun régulateur ne la connaît. Restituée dans les termes
    du guide ANSSI, la même mesure se lit sans qu'on ait à expliquer une
    méthode neuve. Si ces termes disparaissent, il ne reste qu'une méthode que
    personne ne reconnaît."""
    cible = CA.MAILLONS[3]["cle"]
    r = CA.restitution_ebios({cible: 4}, {cible: 0},
                             valeur_metier="Conduite du réseau", gravite=3)
    assert r["ok"] and r["scenarios"]
    s = r["scenarios"][0]
    for champ in ("bien_support_critique", "evenement_redoute",
                  "besoin_de_securite", "vraisemblance", "actions_elementaires",
                  "socle_applicable"):
        assert s.get(champ), (champ, s)
    assert r["sources_de_risque"] and r["socle_de_securite"]


def test_la_gravite_n_est_JAMAIS_deduite_et_le_module_le_dit():
    """ELLE DÉPEND DU MÉTIER, PAS DE L'ARCHITECTURE. Aucune mesure faite ici ne
    la donne, et l'inventer produirait un risque calculé sur une gravité
    inventée."""
    cible = CA.MAILLONS[0]["cle"]
    r = CA.restitution_ebios({cible: 3}, {cible: 0})
    assert r["gravite"] is None
    assert "gravite" in r["manque"] and "valeur_metier" in r["manque"]
    assert len(r["a_fournir"]) > 80
    r2 = CA.restitution_ebios({cible: 3}, {cible: 0},
                              valeur_metier="X", gravite=7)
    assert r2["gravite"] is None, "une gravité hors échelle a été acceptée"


def test_le_document_dit_AVANT_TOUT_CHIFFRE_qu_il_n_est_pas_un_audit():
    """LE DOCUMENT CIRCULE SANS SA PAGE, et il ressemble à un audit. Un lecteur
    qui ne verra jamais l'écran doit le savoir avant de lire un degré."""
    cible = CA.MAILLONS[3]["cle"]
    md = CA.markdown({cible: 4}, {cible: 1}, "Conduite du réseau", 4)
    assert md
    i = md.lower().index("n'est pas un audit")
    chiffres = [m.start() for m in re.finditer(r"\|\s*\d\s*\|", md)]
    assert chiffres, "le document ne porte aucun tableau chiffré"
    assert i < chiffres[0], (
        "la réserve arrive après le premier chiffre du document")
    assert "Licence Ouverte" in md and "Certifiable" in md


def test_un_maillon_ferme_ne_fabrique_aucun_scenario():
    """UN DOCUMENT QUI HURLE PARTOUT CESSE D'ÊTRE LU. Un maillon dont la
    maîtrise couvre l'autonomie ne porte pas de scénario, et en écrire un pour
    faire nombre décrédibiliserait les autres."""
    a, t = _plat(2), _plat(3)
    r = CA.restitution_ebios(a, t, "X", 2)
    assert r["scenarios"] == []
    md = CA.markdown(a, t, "X", 2)
    assert "Aucun maillon ouvert" in md
    assert "n'est pas un maillon sain" in md


# ══════════════════════════════════════════════════════════════════════════
#  5. L'ÉCRAN NE RECOPIE RIEN, ET LES ROUTES TIENNENT LA MÊME PORTE
# ══════════════════════════════════════════════════════════════════════════

def test_l_ecran_ne_recopie_AUCUN_maillon(anonyme):
    """UNE SECONDE LISTE DIVERGE : l'écran annoncerait une méthode que le
    calcul ne tient plus, et rien ne le signalerait.

    La mesure porte sur les chaînes DISTINCTIVES — question et constat de
    chaque maillon, libellés de degrés — et non sur le seul nom du maillon :
    « Action » est un mot courant, et le chercher tel quel rendrait une fausse
    alerte sur « Actions élémentaires »."""
    html = anonyme.get("/securite-ia").data.decode("utf-8")
    fuites = []
    for m in CA.MAILLONS:
        for champ in ("question", "constat"):
            if m[champ][:48] in html:
                fuites.append("%s.%s" % (m["cle"], champ))
    for e, nom in ((CA.AUTONOMIE, "autonomie"), (CA.MAITRISE, "maitrise")):
        for d in e:
            if d["dit"][:40] in html:
                fuites.append("%s degré %d" % (nom, d["degre"]))
    assert not fuites, (
        "ces libellés sont recopiés dans le gabarit au lieu d'être servis par "
        "/api/securite-ia/referentiel : %s" % fuites)


def test_la_route_sert_TOUT_ce_que_l_ecran_doit_dresser(anonyme):
    """Le pendant de la règle précédente : si la route ne servait pas tout,
    l'écran serait bien obligé de recopier."""
    j = anonyme.get("/api/securite-ia/referentiel").get_json()
    assert j and j["ok"]
    ref = j["referentiel"]
    assert len(ref["maillons"]) == len(CA.MAILLONS)
    assert len(ref["autonomie"]) == 5 and len(ref["maitrise"]) == 5
    assert len(ref["sources"]) == len(CA.SOURCES)
    for m in ref["maillons"]:
        assert m["menaces"] and m["redoute"] and m["question"] and m["constat"]


def test_LE_POINT_QUI_DECIDE_l_export_refuse_ce_que_l_ecran_refuse(anonyme):
    """Un format de sortie ne doit jamais devenir le chemin de contournement
    d'un contrôle : le maillon inconnu refusé à l'écran l'est aussi en PDF, en
    Word et en classeur, et pour le même motif."""
    for fmt in ("pdf", "docx", "xlsx"):
        r = anonyme.post("/api/securite-ia/emporter",
                         json={"format": fmt, "autonomie": {"cantine": 2}},
                         headers=ORIGINE)
        assert r.status_code == 400, (fmt, r.status_code)
        assert r.get_json()["erreur"] == "maillons_inconnus", fmt


def test_un_document_sans_le_moindre_maillon_n_est_pas_servi(anonyme):
    """Le servir produirait un livrable vide qui circulerait comme les autres."""
    r = anonyme.post("/api/securite-ia/emporter",
                     json={"format": "pdf", "autonomie": {}, "maitrise": {}},
                     headers=ORIGINE)
    assert r.status_code == 400
    assert r.get_json()["error"] == "rien_de_constate"


@pytest.mark.parametrize("fmt", ["pdf", "docx", "xlsx"])
def test_les_trois_formats_sont_reellement_servis(anonyme, fmt):
    cible = CA.MAILLONS[3]["cle"]
    r = anonyme.post("/api/securite-ia/emporter",
                     json={"format": fmt, "autonomie": {cible: 4},
                           "maitrise": {cible: 1}}, headers=ORIGINE)
    assert r.status_code == 200, (fmt, r.data[:200])
    assert len(r.data) > 2000, (fmt, len(r.data))


# ══════════════════════════════════════════════════════════════════════════
#  6. LA GARDE D'IMPORT, ÉPROUVÉE EN LUI DONNANT UN DÉFAUT À TROUVER
# ══════════════════════════════════════════════════════════════════════════
# POURQUOI CES RÈGLES INJECTENT UNE FAUTE. Une garde qui protège un état
# correct ne prouve rien en restant verte : l'état est correct, elle n'a rien
# eu à faire. Ce dépôt a déjà porté trois règles de ce genre, toutes vertes et
# toutes vides. On lui donne donc le défaut à trouver, et on exige qu'elle le
# trouve.

def test_la_garde_refuse_une_menace_mal_rattachee(monkeypatch):
    monkeypatch.setattr(CA, "MENACES",
                        CA.MENACES + [{"cle": "X", "nom": "x", "dit": "x",
                                       "maillon": "cantine"}])
    with pytest.raises(RuntimeError) as e:
        CA._verifier()
    assert "cantine" in str(e.value)


def test_la_garde_refuse_un_maillon_que_plus_AUCUNE_menace_ne_vise(monkeypatch):
    orphelin = CA.MAILLONS[2]["cle"]
    monkeypatch.setattr(CA, "MENACES",
                        [m for m in CA.MENACES if m["maillon"] != orphelin])
    with pytest.raises(RuntimeError) as e:
        CA._verifier()
    assert orphelin in str(e.value)


def test_la_garde_refuse_une_source_sans_reserve_ecrite(monkeypatch):
    monkeypatch.setattr(CA, "SOURCES",
                        [dict(CA.SOURCES[0], reserve="")] + list(CA.SOURCES[1:]))
    with pytest.raises(RuntimeError) as e:
        CA._verifier()
    assert "réserve" in str(e.value)


def test_la_garde_refuse_un_trou_dans_l_ordre_des_maillons(monkeypatch):
    """L'ordre porte une information — le maillon ouvert le plus TARDIF est le
    plus coûteux. Un rang manquant rendrait cette lecture fausse sans que rien
    ne plante."""
    casse = [dict(m) for m in CA.MAILLONS]
    casse[2]["rang"] = 9
    monkeypatch.setattr(CA, "MAILLONS", casse)
    with pytest.raises(RuntimeError) as e:
        CA._verifier()
    assert "rangs" in str(e.value)


def test_la_garde_est_bien_armee_a_l_import():
    """Le garde-fou des quatre règles ci-dessus : si `_verifier` cessait d'être
    appelé au chargement, elles continueraient de passer — elles l'appellent
    elles-mêmes — et le module accepterait en production ce qu'elles refusent
    en recette."""
    src = io.open(os.path.join(ICI, "chaine_autonomie.py"), encoding="utf-8").read()
    corps = src[src.index("def _verifier()"):]
    assert re.search(r"^_verifier\(\)$", corps, re.M), (
        "`_verifier()` n'est plus appelé au niveau du module")
