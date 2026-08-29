# -*- coding: utf-8 -*-
"""L'ÉTUDE RENDAIT DEUX SCOPES SUR TROIS, SANS LE DIRE.

CE QUE LE MOTEUR FAISAIT DÉJÀ BIEN. Le scope 2 est exemplaire : les DEUX
approches du GHG Protocol — localisée et marché — calculées et déclarées
ensemble, avec la mise en garde qui va avec. Le carbone incorporé est amorti
linéairement et porte ses durées de vie. Chaque valeur porte sa formule, ses
entrées, sa source et son incertitude.

CE QUI MANQUAIT. Le SCOPE 1. Ni le gazole des essais de groupes, ni les fuites
de fluide frigorigène n'apparaissaient nulle part. Or sur un site à détente
directe, la fuite de fluide est régulièrement le PREMIER poste direct : à
400 kg de charge, 5 % de fuite annuelle et un PRG de 2 088, elle pèse 41,8 tCO2e
quand douze mètres cubes de gazole en pèsent 35,8. Un bilan qui l'omet ne manque
pas un détail : il manque un des trois scopes que le GHG Protocol et la méthode
Bilan Carbone® exigent l'un comme l'autre.

UN ZÉRO SERAIT PIRE QUE RIEN, et c'est la décision de conception qui structure
tout ce fichier. Sans donnée d'entrée, le moteur ne rend pas « 0 tCO2e » : un
zéro se lit comme une mesure et blanchirait un poste qu'on n'a pas regardé. Il
rend « non calculé » et dit ce qui manque.

LE PRG N'EST PAS SUPPOSÉ. Le pouvoir de réchauffement global fait foi par
l'annexe I du règlement F-Gas, et varie d'un facteur mille selon le fluide.
L'inventer mettrait un nombre d'apparence officielle sur une valeur de mémoire —
c'est la même règle que `base_carbone.facteur`, qui refuse d'estimer un pays
absent de la base plutôt que d'inventer un repli.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import base_carbone  # noqa: E402
import datacenter  # noqa: E402

BASE = {"puissance_it_kw": 1000}
COMPLET = dict(BASE, gazole_m3_an=12, charge_frigorigene_kg=400,
               prg_frigorigene=2088, taux_fuite_frigorigene=0.05)


def _s1(**champs):
    return datacenter.etude(dict(BASE, **champs))["scope1"]


# ── 1. L'ABSENCE SE DIT, ELLE NE SE CHIFFRE PAS ──────────────────────────

def test_sans_donnee_le_scope1_n_est_pas_zero():
    """LA DÉCISION QUI STRUCTURE TOUT. Un zéro se lit comme une mesure : il
    blanchirait un poste qu'on n'a pas regardé, et un lecteur pressé
    conclurait que le site n'émet rien directement."""
    r = _s1()
    assert r["calcule"] is False
    assert r["total_t"] is None, (
        "un total est rendu sans aucune donnée d'entrée : ce serait un scope 1 "
        "nul, alors qu'il est seulement non mesuré")


def test_l_absence_dit_qu_elle_n_est_pas_une_nullite():
    r = _s1()
    assert "PAS un scope 1 nul" in r["lecture"], (
        "la lecture ne distingue pas « non mesuré » de « nul » : « %s »"
        % r["lecture"][:120])


def test_l_absence_nomme_ce_qui_manque():
    """« Données insuffisantes » n'aide personne à les réunir."""
    r = _s1()
    assert len(r["manques"]) >= 2
    plat = " ".join(r["manques"]).lower()
    for attendu in ("gazole", "charge", "prg", "taux de fuite"):
        assert attendu in plat, "les manques ne nomment pas « %s »" % attendu


def test_un_scope1_partiel_se_declare_partiel():
    """Un total partiel présenté comme un total est un faux — et c'est le cas
    le plus fréquent, puisque le gazole se relève plus souvent que la charge
    de fluide."""
    r = _s1(gazole_m3_an=12)
    assert r["calcule"] is True and r["complet"] is False
    assert "PARTIEL" in r["lecture"]


def test_un_scope1_complet_se_declare_complet():
    r = _s1(**{k: v for k, v in COMPLET.items() if k != "puissance_it_kw"})
    assert r["complet"] is True and "complet" in r["lecture"].lower()


# ── 2. LES DEUX POSTES, ET LEURS CHIFFRES ────────────────────────────────

def test_le_gazole_est_calcule_depuis_la_base_carbone():
    """Sur un poste de scope 1 destiné à une déclaration française, c'est le
    facteur ADEME qui fait foi — pas une valeur de mémoire."""
    if not base_carbone.disponible():
        pytest.skip("Base Carbone absente de ce poste")
    p = [x for x in _s1(gazole_m3_an=12)["postes"]
         if "groupes" in x["nom"]][0]
    assert "Base Carbone" in p["source"]
    assert "millésime du facteur" in p["entrees"], (
        "le facteur est employé sans son millésime : un facteur non daté ne se "
        "défend pas")


def test_le_gazole_donne_le_bon_ordre_de_grandeur():
    """12 m³ × 845 kg/m³ × 3 527 kgCO2e/t = 35,8 tCO2e. Le contrôle porte sur
    le RÉSULTAT, pas sur la formule écrite : une formule juste appliquée à
    l'envers passerait."""
    if not base_carbone.disponible():
        pytest.skip("Base Carbone absente de ce poste")
    p = [x for x in _s1(gazole_m3_an=12)["postes"] if "groupes" in x["nom"]][0]
    assert 33 < p["valeur"] < 39, (
        "12 m³ de gazole donnent %.1f tCO2e : la conversion volume → masse → "
        "émissions est fausse" % p["valeur"])


def test_les_fuites_suivent_charge_fois_taux_fois_prg():
    """400 × 0,05 × 2 088 / 1 000 = 41,8 tCO2e."""
    r = _s1(charge_frigorigene_kg=400, prg_frigorigene=2088,
            taux_fuite_frigorigene=0.05)
    p = [x for x in r["postes"] if "frigorigène" in x["nom"]][0]
    assert abs(p["valeur"] - 41.76) < 0.1, p["valeur"]


def test_les_fuites_peuvent_depasser_le_carburant():
    """C'EST LA RAISON D'ÊTRE DE CE POSTE. Un moteur qui n'aurait chiffré que
    le carburant aurait manqué le premier contributeur direct d'un site froid,
    et l'aurait manqué en silence."""
    r = _s1(**{k: v for k, v in COMPLET.items() if k != "puissance_it_kw"})
    par_nom = {p["nom"]: p["valeur"] for p in r["postes"]}
    fuite = [v for n, v in par_nom.items() if "frigorigène" in n][0]
    carbu = [v for n, v in par_nom.items() if "groupes" in n][0]
    assert fuite > carbu, (
        "sur ce profil, les fuites devraient dépasser le carburant "
        "(%.1f contre %.1f)" % (fuite, carbu))


def test_le_total_est_la_somme_des_postes():
    r = _s1(**{k: v for k, v in COMPLET.items() if k != "puissance_it_kw"})
    assert abs(r["total_t"] - sum(p["valeur"] for p in r["postes"])) < 1e-9


# ── 3. AUCUNE VALEUR N'EST INVENTÉE ──────────────────────────────────────

def test_le_prg_n_est_jamais_suppose():
    """Il varie d'un facteur mille selon le fluide : un PRG deviné mettrait un
    nombre d'apparence officielle sur une valeur de mémoire, et fausserait le
    poste entier."""
    r = _s1(charge_frigorigene_kg=400, taux_fuite_frigorigene=0.05)
    assert not [p for p in r["postes"] if "frigorigène" in p["nom"]], (
        "les fuites ont été chiffrées sans PRG : une valeur a été supposée")
    assert "PRG" in " ".join(r["manques"])


def test_le_moteur_ne_se_replie_sur_aucun_facteur_de_gazole():
    """Même règle que `base_carbone.facteur`, qui refuse d'estimer un pays
    absent plutôt que d'inventer un repli."""
    # SUR L'ARBRE, PAS SUR LE TEXTE. La première version cherchait un nombre à
    # trois chiffres dans un `return {` — et a accusé le retour LÉGITIME, qui
    # contient « 1000.0 » pour convertir des kilos en tonnes. Ce qu'on veut
    # savoir n'est pas s'il y a un nombre, mais si une VALEUR DE FACTEUR est
    # une constante au lieu d'être lue dans la base.
    import ast
    src = open(os.path.join(ICI, "datacenter.py"), encoding="utf-8").read()
    fonction = next(n for n in ast.walk(ast.parse(src))
                    if isinstance(n, ast.FunctionDef)
                    and n.name == "_facteur_gazole")
    assert any(isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)
               and n.value.value is None for n in ast.walk(fonction)), (
        "la fonction ne rend jamais None : elle a donc un repli")
    for n in ast.walk(fonction):
        if not (isinstance(n, ast.Return) and isinstance(n.value, ast.Dict)):
            continue
        for cle, val in zip(n.value.keys, n.value.values):
            if getattr(cle, "value", None) not in ("densite", "kg_par_tonne"):
                continue
            assert not isinstance(val, ast.Constant), (
                "« %s » est rendu comme une constante écrite ici : le facteur "
                "partirait sous l'apparence d'une valeur ADEME"
                % getattr(cle, "value", "?"))
    # LE REPLI NE SE MET PAS TOUJOURS DANS LE RETOUR, et une mutation l'a
    # prouvé : il suffit d'AFFECTER les variables juste avant. La règle qui ne
    # regardait que le `return` l'a laissée passer. On surveille donc les
    # affectations elles-mêmes — c'est là que la valeur de mémoire entre.
    for n in ast.walk(fonction):
        if not isinstance(n, ast.Assign):
            continue
        noms = [c.id for c in n.targets if isinstance(c, ast.Name)]
        if isinstance(n.targets[0], ast.Tuple):
            noms += [e.id for e in n.targets[0].elts if isinstance(e, ast.Name)]
        if not ({"densite", "kg_tonne"} & set(noms)):
            continue
        valeurs = (n.value.elts if isinstance(n.value, ast.Tuple) else [n.value])
        for v in valeurs:
            assert not (isinstance(v, ast.Constant)
                        and isinstance(v.value, (int, float))
                        and abs(v.value) >= 1), (
                "un facteur chiffré (%s) est affecté dans la fonction : c'est "
                "un repli, et il partirait sous l'apparence d'une valeur ADEME"
                % v.value)


def test_chaque_poste_porte_sa_source_et_son_incertitude():
    r = _s1(**{k: v for k, v in COMPLET.items() if k != "puissance_it_kw"})
    for p in r["postes"]:
        assert p.get("source"), "%s sans source" % p["nom"]
        assert p.get("incertitude"), "%s sans incertitude" % p["nom"]
        assert p.get("formule"), "%s sans formule" % p["nom"]


def test_chaque_poste_se_rattache_au_scope_1():
    """Un poste d'émission qui ne dit pas son scope se retrouve compté deux
    fois, ou pas du tout, dans le bilan qui l'agrège."""
    r = _s1(**{k: v for k, v in COMPLET.items() if k != "puissance_it_kw"})
    for p in r["postes"]:
        assert "cope 1" in (p.get("note") or ""), (
            "%s ne dit pas qu'il relève du scope 1" % p["nom"])


# ── 4. LES ENTRÉES SONT BORNÉES COMME LES AUTRES ─────────────────────────

@pytest.mark.parametrize("champ", ["gazole_m3_an", "charge_frigorigene_kg",
                                   "prg_frigorigene", "taux_fuite_frigorigene"])
def test_chaque_nouveau_champ_porte_son_domaine(champ):
    """Les quatre champs du scope 1 sont des saisies comme les autres : sans
    domaine, un taux de fuite de −99 ou de 40 entrerait dans le calcul."""
    c = [x for x in datacenter.CHAMPS if x["id"] == champ][0]
    assert c.get("domaine"), "%s n'a pas de domaine déclaré" % champ
    assert len(c["domaine"].get("pourquoi") or "") > 25


def test_un_taux_de_fuite_superieur_a_un_est_ecarte():
    """On ne peut pas perdre plus que la charge en une année."""
    c = [x for x in datacenter.CHAMPS if x["id"] == "taux_fuite_frigorigene"][0]
    import app
    v, motif = app._lire_nombre(1.5, c)
    assert v is None and motif


def test_les_quatre_champs_restent_vides_par_defaut():
    """S'ils portaient une valeur par défaut, le scope 1 se calculerait tout
    seul sur des hypothèses — et le « non calculé » qui fait tout l'intérêt de
    ce poste ne se produirait jamais."""
    for champ in ("gazole_m3_an", "charge_frigorigene_kg", "prg_frigorigene",
                  "taux_fuite_frigorigene"):
        c = [x for x in datacenter.CHAMPS if x["id"] == champ][0]
        assert "defaut" not in c, (
            "%s a une valeur par défaut : le scope 1 se chiffrera sur une "
            "hypothèse que personne n'a saisie" % champ)


# ── 5. LE SCOPE 2 N'A PAS ÉTÉ ABÎMÉ ──────────────────────────────────────

def test_les_deux_approches_du_scope_2_restent_declarees():
    """Le double reporting du GHG Protocol existait et devait survivre à
    l'ajout : c'est la partie que le moteur faisait déjà bien."""
    c = datacenter.etude(BASE)["carbone"]
    assert "co2_exploitation_localise_t" in c
    assert "co2_exploitation_marche_t" in c
    for k in ("co2_exploitation_localise_t", "co2_exploitation_marche_t"):
        assert "GHG Protocol" in c[k]["source"]
