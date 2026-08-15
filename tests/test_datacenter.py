"""Le moteur d'ingénierie de centres de données.

Ce que ces tests vérifient n'est pas « le code s'exécute », mais que les
résultats tiennent devant un examen technique — parce que c'est exactement ce
qui leur arrivera. Une note de calcul annexée à une offre se fait vérifier
ligne à ligne, et trois choses s'y contrôlent en premier :

  1. LA PHYSIQUE. L'évaporation d'eau par kWh thermique a une borne basse
     incontournable. Un chiffre en dessous signale une erreur, jamais une
     performance.
  2. LA COHÉRENCE INTERNE. E_total = E_IT × PUE, ERE = PUE × (1 − ERF),
     WUE_source ≥ WUE_site. Ces identités ne sont pas des approximations : si
     l'une casse, tout le reste est suspect.
  3. LE DÉTERMINISME. Deux exécutions identiques donnent le même résultat.
     Sans cela, une note ne peut pas être annexée à un engagement.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import datacenter as dc  # noqa: E402


PROFIL_TEMOIN = {
    "puissance_it_kw": 2000,
    "taux_charge": 0.65,
    "pays": "FR",
    "refroidissement": "tour_evaporative",
}


@pytest.fixture()
def etude():
    return dc.etude(PROFIL_TEMOIN)


# ── 1. Physique ────────────────────────────────────────────────────────────

def test_borne_physique_evaporation():
    """1 kWh de chaleur évacué par évaporation demande ~1,47 L d'eau.

    C'est 3 600 kJ divisés par la chaleur latente de vaporisation. Aucune tour
    ne fait mieux : ce n'est pas une question de technologie, c'est la quantité
    d'eau qu'il faut changer d'état pour emporter cette chaleur.
    """
    l = dc.CONSTANTES["eau_evaporee_par_kWh_thermique_L"]["valeur"]
    assert 1.40 < l < 1.55, f"borne physique invraisemblable : {l}"


def test_evaporation_respecte_sa_borne(etude):
    e_evap = (etude["energie"]["energie_totale_MWh"]["valeur"]
              * etude["eau"]["part_evaporative"] * 1000.0)
    attendu = e_evap * dc.CONSTANTES["eau_evaporee_par_kWh_thermique_L"]["valeur"] / 1000.0
    assert abs(etude["eau"]["evaporation_m3"]["valeur"] - attendu) < 1.0


def test_appoint_superieur_a_evaporation(etude):
    """La purge s'ajoute toujours à l'évaporation : sans elle, les sels
    s'accumulent jusqu'à l'entartrage. Un appoint égal à l'évaporation
    signalerait un cycle de concentration infini, qui n'existe pas."""
    assert (etude["eau"]["appoint_m3"]["valeur"]
            > etude["eau"]["evaporation_m3"]["valeur"])


# ── 2. Cohérence interne ───────────────────────────────────────────────────

def test_identite_energie(etude):
    e = etude["energie"]
    assert abs(e["energie_totale_MWh"]["valeur"]
               - e["energie_it_MWh"]["valeur"] * e["pue"]["valeur"]) < 0.5


def test_identite_ere():
    """ERE = PUE × (1 − ERF). Vérifié avec une réutilisation non nulle : à ERF
    nul l'identité serait vraie par accident."""
    r = dc.etude(dict(PROFIL_TEMOIN, part_chaleur_reutilisee=0.35))
    attendu = r["energie"]["pue"]["valeur"] * (1 - 0.35)
    assert abs(r["chaleur"]["ere"]["valeur"] - attendu) < 0.001


def test_ere_peut_passer_sous_un():
    """Ce n'est pas une anomalie : au-delà d'un certain taux de réutilisation,
    la chaleur valorisée dépasse les pertes d'infrastructure. C'est précisément
    ce qui justifie d'implanter près d'un réseau de chaleur."""
    r = dc.etude(dict(PROFIL_TEMOIN, refroidissement="liquide_dlc",
                      part_chaleur_reutilisee=0.60))
    assert r["chaleur"]["ere"]["valeur"] < 1.0


def test_wue_source_superieur_au_wue_site(etude):
    """Le WUE de source contient le WUE de site plus l'eau de production
    électrique. Il ne peut pas lui être inférieur — et si le calcul le
    permettait, l'arbitrage évaporatif / rejet sec serait faussé."""
    assert (etude["eau"]["wue_source"]["valeur"]
            >= etude["eau"]["wue_site"]["valeur"])


def test_rejet_sec_a_un_wue_site_nul_mais_pas_de_source():
    """Le piège que le moteur doit rendre visible : un rejet sec affiche zéro
    eau sur le site, tout en consommant de l'eau à la source. Présenter le seul
    WUE de site conduit à conclure à l'inverse de ce qu'il faut faire."""
    r = dc.etude(dict(PROFIL_TEMOIN, refroidissement="free_cooling_air"))
    assert r["eau"]["wue_site"]["valeur"] == 0.0
    assert r["eau"]["wue_source"]["valeur"] > 0.5


def test_cue_suit_pue_et_intensite(etude):
    attendu = (etude["energie"]["pue"]["valeur"]
               * dc.INTENSITE_RESEAU["FR"] / 1000.0)
    assert abs(etude["carbone"]["cue"]["valeur"] - attendu) < 0.002


# ── 3. Ce que le moteur doit RÉVÉLER ───────────────────────────────────────

def test_incorpore_domine_sur_mix_decarbone(etude):
    """Sur un mix français, le carbone de construction et des serveurs dépasse
    celui de l'exploitation. C'est le résultat qui change les décisions :
    optimiser le PUE quand l'incorporé pèse deux fois plus, c'est se tromper de
    combat — et un évaluateur technique le verra."""
    assert etude["carbone"]["part_incorpore_pct"]["valeur"] > 50


def test_charge_partielle_degrade_le_pue():
    """L'erreur la plus courante des dossiers, et la plus visible en
    exploitation : les auxiliaires ne suivent pas la charge proportionnellement.
    """
    plein = dc.etude(dict(PROFIL_TEMOIN, taux_charge=0.85))
    creux = dc.etude(dict(PROFIL_TEMOIN, taux_charge=0.30))
    assert creux["energie"]["pue"]["valeur"] > plein["energie"]["pue"]["valeur"]


def test_arbitrage_eau_energie_est_explicite(etude):
    """Le levier « rejet sec » doit apparaître avec un gain d'eau POSITIF et un
    gain d'énergie NÉGATIF. Un levier qui ne montrerait que son bon côté serait
    un argument commercial déguisé en recommandation."""
    sec = [l for l in etude["leviers"] if "sec" in l["titre"].lower()]
    assert sec, "le levier du rejet sec n'est pas proposé sur un site évaporatif"
    assert sec[0]["gain_eau_m3"] > 0
    assert sec[0]["gain_energie_MWh"] < 0
    assert sec[0]["contrepartie"]


def test_chaque_levier_porte_sa_contrepartie(etude):
    for l in etude["leviers"]:
        assert l["contrepartie"].strip(), f"levier sans contrepartie : {l['titre']}"
        assert l["condition"].strip(), f"levier sans condition : {l['titre']}"
        assert l["fondement"].strip(), f"levier sans fondement : {l['titre']}"


# ── 4. Traçabilité et honnêteté ────────────────────────────────────────────

def test_chaque_valeur_porte_sa_methode(etude):
    """Un chiffre sans sa formule n'est pas opposable. Le contrôle porte sur
    toutes les grandeurs calculées, pas sur un échantillon."""
    manquantes = []
    for section in ("energie", "eau", "carbone", "chaleur"):
        for cle, v in (etude[section] or {}).items():
            if isinstance(v, dict) and "valeur" in v and "nom" in v:
                if not v.get("formule"):
                    manquantes.append(f"{section}.{cle}")
    assert not manquantes, "valeurs sans formule : " + ", ".join(manquantes)


def test_les_limites_sont_declarees(etude):
    """Un moteur qui ne déclare pas ses limites les fait porter par son lecteur,
    qui ne les connaît pas."""
    av = " ".join(etude["avertissements"]).lower()
    assert len(etude["avertissements"]) >= 3
    assert "incorporé" in av or "incorpore" in av
    assert "modèle de langage" in av


def test_seuil_reglementaire_europeen():
    petit = dc.etude(dict(PROFIL_TEMOIN, puissance_it_kw=300))
    grand = dc.etude(dict(PROFIL_TEMOIN, puissance_it_kw=800))
    st = {c["sujet"]: c["statut"] for c in petit["conformite"]}
    assert "hors seuil" in list(st.values())
    st2 = {c["sujet"]: c["statut"] for c in grand["conformite"]}
    assert "assujetti" in list(st2.values())


# ── 5. Déterminisme ────────────────────────────────────────────────────────

def test_deux_executions_donnent_le_meme_resultat():
    """Sans cette propriété, une note de calcul ne peut pas être annexée à un
    engagement contractuel : elle ne serait pas reproductible par le client."""
    import json
    a = dc.etude(PROFIL_TEMOIN)
    b = dc.etude(PROFIL_TEMOIN)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_pue_impose_est_respecte():
    """Un PUE au cahier des charges est un engagement contractuel, pas une
    hypothèse : le moteur ne doit pas le « corriger »."""
    r = dc.etude(dict(PROFIL_TEMOIN, pue_cible=1.22))
    assert r["energie"]["pue"]["valeur"] == 1.22


def test_profil_vide_ne_casse_pas():
    r = dc.etude({})
    assert r["energie"]["energie_it_MWh"]["valeur"] == 0
    assert r["eau"]["wue_site"]["valeur"] == 0


# ── 6. Intégration : thèmes et livrables ───────────────────────────────────

def test_themes_data_center_presents():
    import rag_store
    dcs = [t for t in rag_store.THEMES if t.startswith("Data center")]
    assert len(dcs) >= 15
    assert len(set(rag_store.THEMES)) == len(rag_store.THEMES), "thème dupliqué"


def test_livrables_data_center_presents():
    """Le catalogue ne doit RIEN perdre — il a le droit de grandir.

    Ce contrôle figeait le nombre à huit ; il y en a quatorze. Chaque ajout
    légitime le faisait tomber, et un test qu'on répare machinalement à chaque
    version ne protège plus rien. Ce qui doit tenir, c'est qu'aucun livrable ne
    DISPARAISSE et qu'aucun ne soit proposé sans plan.
    """
    import livrables
    dcs = [t for t in livrables.TYPES if t["groupe"] == "Centres de données"]
    assert len(dcs) >= 8, "des livrables du groupe ont disparu"
    ids = [t["id"] for t in dcs]
    assert len(set(ids)) == len(ids), "identifiant de livrable dupliqué"
    for t in dcs:
        assert t["sections"], f"{t['id']} sans sections"


def test_le_modele_recoit_les_chiffres_comme_des_faits(etude):
    """Le point qui décide de la qualité du livrable : le modèle doit recevoir
    les résultats AVEC leur formule et leur source, et l'interdiction explicite
    de les recalculer. Un modèle à qui l'on transmet un chiffre nu brode."""
    import livrables
    _, user = livrables.build_prompts(
        "dc-note-calcul",
        {"client": "Témoin", "secteur": "Numérique", "perimetre": "Site",
         "etude": etude})
    assert "INTERDICTIONS ABSOLUES" in user
    assert "ne recalcule aucune" in user
    assert "ISO/IEC 30134" in user
    assert "Avertissements à reproduire" in user


# ── Les sources consultables du référentiel ─────────────────────────────────
# Dix organismes, chacun avec son lien officiel. La règle qui rend ces liens
# durables : https, et RIEN après le domaine — un lien profond pourrit en
# quelques mois, la racine d'un organisme de normalisation est stable depuis
# des décennies.

def test_au_moins_huit_sources_consultables_completes():
    import datacenter as d
    assert len(d.SOURCES_CONSULTABLES) >= 8
    cles = [x["cle"] for x in d.SOURCES_CONSULTABLES]
    assert len(set(cles)) == len(cles)
    for x in d.SOURCES_CONSULTABLES:
        for champ in ("organisme", "nature", "porte", "lien", "verifier"):
            assert str(x[champ]).strip(), (x["cle"], champ)


def test_tous_les_liens_sont_https_et_a_la_racine():
    import re
    import datacenter as d
    for x in d.SOURCES_CONSULTABLES:
        assert re.match(r"^https://[^/]+/?$", x["lien"]), (x["cle"], x["lien"])


def test_le_referentiel_sert_les_sources():
    import datacenter as d
    assert d.referentiel()["sources_consultables"] is d.SOURCES_CONSULTABLES


def test_le_garde_TOMBE_sur_un_lien_profond():
    """La règle de la racine n'existe que si sa violation est détectée. On
    mutile une copie, on vérifie, on restaure — dans un try/finally."""
    import datacenter as d
    sauve = d.SOURCES_CONSULTABLES[0]["lien"]
    try:
        d.SOURCES_CONSULTABLES[0]["lien"] = sauve.rstrip("/") + "/page/profonde"
        fautes = d._verifier_sources()
        assert any("lien profond" in f for f in fautes)
    finally:
        d.SOURCES_CONSULTABLES[0]["lien"] = sauve
    assert not d._verifier_sources()


# ── Les limites du moteur, chacune avec sa réponse ─────────────────────────
# On n'efface aucune limite vraie ; chacune porte la norme, le calcul, la
# main. Et une limite « levable » doit l'être par un champ du profil qui
# EXISTE : nommer un champ disparu enverrait chercher une case absente.

def test_chaque_limite_porte_sa_reponse_complete():
    import datacenter as d
    assert len(d.LIMITES) == 4
    for x in d.LIMITES:
        for champ in ("quoi", "moteur_fait", "leve_note", "calcul", "qui", "quand"):
            assert str(x[champ]).strip(), (x["cle"], champ)
        assert x["normes"], x["cle"]


def test_deux_limites_se_levent_par_un_champ_du_profil():
    import datacenter as d
    champs = {c["id"] for c in d.CHAMPS}
    levables = [x for x in d.LIMITES if x["leve_par"]]
    assert len(levables) == 2
    for x in levables:
        assert x["leve_par"] in champs, x["cle"]
    # …et les avertissements du résultat tombent bien quand la donnée arrive.
    sans = d.etude({"puissance_it_kw": 1000})
    avec = d.etude({"puissance_it_kw": 1000, "pue_cible": 1.25,
                    "intensite_reseau_g": 42})
    txt_sans = " ".join(sans["avertissements"])
    txt_avec = " ".join(avec["avertissements"])
    assert "ESTIMÉ" in txt_sans and "MOYENNE ANNUELLE" in txt_sans
    assert "ESTIMÉ" not in txt_avec and "MOYENNE ANNUELLE" not in txt_avec


def test_le_garde_TOMBE_sur_un_champ_de_levee_inconnu():
    import datacenter as d
    sauve = d.LIMITES[0]["leve_par"]
    try:
        d.LIMITES[0]["leve_par"] = "champ_disparu"
        assert any("champ de levée inconnu" in f for f in d._verifier_limites())
    finally:
        d.LIMITES[0]["leve_par"] = sauve
    assert not d._verifier_limites()
