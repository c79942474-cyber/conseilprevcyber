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


# ── L'évaluateur de chiffre annoncé ────────────────────────────────────────
# Le moteur ne fait ni simulation TMY ni profil horaire — mais il JUGE un
# chiffre annoncé avec ses propres plages. Doctrine : jamais un second
# barème. Chaque borne testée ici est DÉRIVÉE des constantes du module ;
# écrite en dur, elle survivrait à un changement de plage et mentirait.

def test_evaluer_pue_est_le_meme_calcul_que_l_etude():
    """Le PUE que l'étude elle-même produit doit être jugé cohérent, dans
    EXACTEMENT la bande que l'étude publie. Si ce test tombe, l'évaluateur
    est devenu un second barème — l'interdit central."""
    import datacenter as d
    e = d.etude({"puissance_it_kw": 1000, "refroidissement": "adiabatique",
                 "taux_charge": 0.4})
    pue = e["energie"]["pue"]["valeur"]
    bande = e["energie"]["pue"]["bande"]
    ev = d.evaluer_pue(pue, "adiabatique", 0.4)
    assert ev["ok"] and ev["verdict"] == "coherent"
    assert ev["plage_attendue"] == [round(bande["min"], 3), round(bande["max"], 3)]
    assert ev["penalite_charge"] == round(d.penalite_charge(0.4), 3)


def test_evaluer_pue_verdicts_aux_bornes_de_la_famille():
    import datacenter as d
    bas, haut = d.REFROIDISSEMENT["adiabatique"]["pue_partiel"]
    pen = d.penalite_charge(0.30)
    assert pen > 0, "sous le point de conception la pénalité doit exister, " \
                    "sinon ce test ne sépare plus les verdicts"
    assert d.evaluer_pue(bas - 0.01, "adiabatique", 0.30)["verdict"] == "sous_plage"
    assert d.evaluer_pue(bas + pen / 2, "adiabatique", 0.30)["verdict"] \
        == "plausible_pleine_charge"
    assert d.evaluer_pue(bas + pen + 0.01, "adiabatique", 0.30)["verdict"] == "coherent"
    assert d.evaluer_pue(haut + pen + 0.01, "adiabatique", 0.30)["verdict"] == "au_dessus"
    # Au point de conception, plus de pénalité : « plausible à pleine charge »
    # ne peut PAS exister — la plage attendue EST la plage pleine charge.
    ev = d.evaluer_pue(bas + 0.001, "adiabatique", d.CHARGE_POINT_CONCEPTION)
    assert ev["verdict"] == "coherent" and ev["penalite_charge"] == 0


def test_evaluer_pue_refuse_l_impossible_avec_motif():
    import datacenter as d
    r = d.evaluer_pue(0.8)
    assert r["ok"] is False and "physiquement impossible" in r["motif"]
    r = d.evaluer_pue("n/a")
    assert r["ok"] is False
    r = d.evaluer_pue(1.2, "magnetique")
    assert r["ok"] is False and "adiabatique" in r["motif"]  # liste les connues
    r = d.evaluer_pue(1.2, "adiabatique", 0.01)
    assert r["ok"] is False and "bornes" in r["motif"]


def test_evaluer_intensite_verdicts_derives_de_la_moyenne():
    import datacenter as d
    m = d.INTENSITE_RESEAU["FR"]
    assert d.evaluer_intensite(0.49 * m, "FR")["verdict"] == "market_based_probable"
    assert d.evaluer_intensite(m, "FR")["verdict"] == "coherent_location"
    assert d.evaluer_intensite(1.51 * m, "FR")["verdict"] == "au_dessus"
    ev = d.evaluer_intensite(m, "fr")  # la casse ne décide pas d'un pays
    assert ev["ok"] and ev["moyenne_location_g"] == m
    r = d.evaluer_intensite(-3, "FR")
    assert r["ok"] is False
    r = d.evaluer_intensite(50, "ZZ")
    assert r["ok"] is False and "FR" in r["motif"]  # liste les connus


def test_evaluer_intensite_borne_le_pilotage_en_tonnes():
    """g/kWh et t/GWh sont la même unité : l'écart se lit en tonnes par GWh
    déplacé, et le passage aux tonnes/an n'emploie QUE les valeurs du client."""
    import datacenter as d
    m = d.INTENSITE_RESEAU["FR"]
    ev = d.evaluer_intensite(m, "FR", heures_basses_g=m - 26)
    p = ev["pilotage"]
    assert p["ecart_g_kwh"] == 26.0 == p["tonnes_par_gwh_deplace"]
    ev = d.evaluer_intensite(m, "FR", heures_basses_g=m - 26,
                             part_differable_pct=20, energie_mwh_an=10_000)
    # 10 000 MWh × 20 % × 26 g/kWh = 52 t/an — vérifiable à la main.
    assert ev["pilotage"]["tonnes_an_max"] == 52.0
    assert "vos valeurs" in ev["pilotage"]["hypotheses"]
    # Des heures « basses » au-dessus de la moyenne : gain nul, dit tel quel,
    # jamais un gain négatif ni une correction silencieuse.
    ev = d.evaluer_intensite(m, "FR", heures_basses_g=m + 10)
    assert ev["pilotage"]["tonnes_par_gwh_deplace"] == 0.0
    assert "Aucun gain" in ev["pilotage"]["lecture"]
    # Sans données client : pas de bloc pilotage du tout — le moteur ne
    # fabrique pas d'étude de pilotage à partir de rien.
    assert "pilotage" not in d.evaluer_intensite(m, "FR")


# ── Les évaluateurs eau et carbone incorporé ───────────────────────────────
# Même doctrine que le PUE et l'intensité : jamais un second barème. La
# référence eau est RECALCULÉE par energie()+eau(), les bornes viennent des
# constantes d'incertitude du module — les mêmes qui écrivent « ±15 % » et
# « ±50 % » dans les notes de calcul de l'étude.

def test_evaluer_eau_est_le_meme_calcul_que_l_etude():
    import datacenter as d
    pr = {"puissance_it_kw": 1000, "refroidissement": "adiabatique"}
    w = d.eau(pr, d.energie(pr))
    appoint = w["appoint_m3"]["valeur"]
    ev = d.evaluer_eau(pr, appoint)
    assert ev["ok"] and ev["verdict"] == "coherent_etude"
    assert ev["reference"]["appoint_m3"] == round(appoint, 1)
    assert ev["reference"]["evaporation_m3"] == round(w["evaporation_m3"]["valeur"], 1)
    # Les bornes sont DÉRIVÉES des constantes du module, pas réécrites.
    evap = w["evaporation_m3"]["valeur"]
    assert d.evaluer_eau(pr, evap * (1 - d.INCERTITUDE_EVAPORATION) * 0.99)["verdict"] \
        == "sous_borne_physique"
    assert d.evaluer_eau(pr, appoint * (1 + d.INCERTITUDE_APPOINT) * 1.01)["verdict"] \
        == "au_dessus_etude"


def test_evaluer_eau_refuse_sans_puissance_et_l_impossible():
    import datacenter as d
    r = d.evaluer_eau({}, 100)
    assert r["ok"] is False and "puissance" in r["motif"]
    r = d.evaluer_eau({"puissance_it_kw": 1000}, -5)
    assert r["ok"] is False
    r = d.evaluer_eau({"puissance_it_kw": 1000}, "beaucoup")
    assert r["ok"] is False


def test_evaluer_eau_famille_seche_zero_est_coherent():
    """0 m³ n'est pas refusé : pour un rejet sec, c'est LE bon chiffre — et
    un volume non nul y devient une question de périmètre, pas une erreur."""
    import datacenter as d
    sec = {"puissance_it_kw": 1000, "refroidissement": "air_dx"}
    assert d.evaluer_eau(sec, 0)["verdict"] == "coherent_etude"
    ev = d.evaluer_eau(sec, 500)
    assert ev["verdict"] == "au_dessus_etude" and "décomposition" in ev["lecture"]


def test_evaluer_eau_pointe_arithmetique():
    """Le moteur n'a pas le climat local : sur la pointe il ne juge QUE
    l'arithmétique — max ≥ moyenne — et nomme le profil mensuel pour le reste."""
    import datacenter as d
    pr = {"puissance_it_kw": 1000, "refroidissement": "adiabatique"}
    ev = d.evaluer_eau(pr, 3650, pointe_jour_m3=8)   # jour moyen = 10
    assert ev["pointe"]["recevable"] is False
    assert "impossible" in ev["pointe"]["lecture"]
    ev = d.evaluer_eau(pr, 3650, pointe_jour_m3=10)  # 365 jours identiques
    assert ev["pointe"]["recevable"] is False
    assert "évaporatif" in ev["pointe"]["lecture"]
    ev = d.evaluer_eau(pr, 3650, pointe_jour_m3=25)
    assert ev["pointe"]["recevable"] is True and ev["pointe"]["facteur"] == 2.5
    assert "profil mensuel" in ev["pointe"]["lecture"]


def test_evaluer_incorpore_bornes_derivees_du_referentiel():
    import datacenter as d
    ref = d.INCORPORE["serveur_kgCO2e"]["valeur"]
    marge = d.INCERTITUDE_INCORPORE
    assert d.evaluer_incorpore("serveur_kgCO2e", ref)["verdict"] == "coherent_secteur"
    assert d.evaluer_incorpore("serveur_kgCO2e", ref * (1 - marge) * 0.99)["verdict"] \
        == "sous_plage_sectorielle"
    assert d.evaluer_incorpore("serveur_kgCO2e", ref * (1 + marge) * 1.01)["verdict"] \
        == "au_dessus_secteur"
    r = d.evaluer_incorpore("gpu_rack", 100)
    assert r["ok"] is False and "serveur_kgCO2e" in r["motif"]  # liste les connus
    # Nul ou négatif : refus qui ENSEIGNE — modules séparés, pas d'effacement.
    r = d.evaluer_incorpore("batiment_kgCO2e_par_kW_IT", -5)
    assert r["ok"] is False and "A1-A3" in r["motif"]


def test_evaluer_incorpore_amortit_sur_la_duree_annoncee():
    import datacenter as d
    ref = d.INCORPORE["serveur_kgCO2e"]
    ev = d.evaluer_incorpore("serveur_kgCO2e", ref["valeur"], duree_vie_ans=6)
    a = ev["amorti"]
    assert a["annonce_kg_an"] == round(ref["valeur"] / 6, 1)
    assert a["reference_kg_an"] == round(ref["valeur"] / ref["duree_vie_ans"], 1)
    assert "durée de vie" in a["lecture"]
    r = d.evaluer_incorpore("serveur_kgCO2e", 1200, duree_vie_ans=0)
    assert r["ok"] is False


def test_les_quatre_evaluateurs_disent_a_qui_exiger():
    """« pour BE fluides et AMO carbone » : chaque verdict nomme la main qui
    doit produire les pièces — c'est elle que le client appellera."""
    import datacenter as d
    pr = {"puissance_it_kw": 1000}
    assert d.evaluer_pue(1.3)["exige_de"] == "du BE fluides"
    assert d.evaluer_intensite(56)["exige_de"] == "de l'énergéticien"
    assert d.evaluer_eau(pr, 1000)["exige_de"] == "du BE fluides"
    assert d.evaluer_incorpore("serveur_kgCO2e", 1200)["exige_de"] == "de l'AMO carbone"


def test_exigences_incorpore_portent_les_normes_demandees():
    """ISO 14025, EN 15804+A2, ISO 14040/14044 et les quatre normes
    d'écoconception fournies : chacune doit être NOMMÉE dans les exigences ou
    la marche — une norme utilisée est une norme citée."""
    import datacenter as d
    txt = " ".join(d.evaluer_incorpore("serveur_kgCO2e", 1200)["exigences"])
    for norme in ("ISO 14025", "EN 15804+A2", "ISO 14040/14044",
                  "IEC 62430", "ISO 14006", "NF X30-264", "ISO/TR 14062"):
        assert norme in txt, norme
    # …et l'eau cite l'écoconception pour l'arbitrage eau/énergie.
    txt_eau = " ".join(d.evaluer_eau({"puissance_it_kw": 1000}, 1000)["exigences"])
    for norme in ("ISO 14046", "ISO 46001", "ISO/IEC 30134-9", "IEC 62430"):
        assert norme in txt_eau, norme


def test_les_sources_consultables_portent_afnor_et_inies():
    import datacenter as d
    cles = {s["cle"] for s in d.SOURCES_CONSULTABLES}
    assert {"afnor", "inies"} <= cles
    # Toujours à la racine, toujours en https — le garde général le prouve
    # déjà, mais ces deux-là sont neuves : les nommer rend l'échec lisible.
    for s in d.SOURCES_CONSULTABLES:
        if s["cle"] in ("afnor", "inies"):
            assert s["lien"].startswith("https://") and s["verifier"]
