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
    assert d.evaluer_eau(pr, evap * d.PART_LATENTE_MIN * 0.99)["verdict"] \
        == "sous_borne_physique"
    # …et JUSTE AU-DESSUS du plancher latent-minimal, plus d'accusation : une
    # tour réelle qui rejette du sensible évapore moins que le tout-latent.
    assert d.evaluer_eau(pr, evap * d.PART_LATENTE_MIN * 1.01)["verdict"] \
        != "sous_borne_physique"
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


def test_part_evaporative_adiabatique_ne_contredit_plus_sa_propre_suggestion():
    """LE DÉFAUT CORRIGÉ. Le moteur retombait sur 0,25 quand le champ était
    laissé vide pour la famille « adiabatique », tandis que ce même champ
    proposait 0,5 sous l'étiquette « assistance adiabatique saisonnière » —
    donc suivre la suggestion du formulaire ou laisser le champ vide, pour
    la même intention, produisait deux résultats différents. Les deux
    valeurs viennent maintenant d'une source unique."""
    import datacenter as d
    suggestion = next(s["valeur"] for s in d.SUGGESTIONS["part_evaporative"]
                       if "adiabatique" in s["nom"])
    assert suggestion == d.PART_EVAPORATIVE_PAR_FAMILLE["adiabatique"]

    pr = {"puissance_it_kw": 1000, "refroidissement": "adiabatique"}
    w = d.eau(pr, d.energie(pr))
    assert w["part_evaporative"] == d.PART_EVAPORATIVE_PAR_FAMILLE["adiabatique"]


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


# ── L'audit scientifique : ce que la page affirme doit rester vrai ─────────
# Chaque contrôle fige une CORRECTION ou une exigence de l'audit d'août 2026 :
# l'évaporation tout-latent est un majorant (pas un plancher), l'intensité
# porte son millésime, les identités normées (ERE, WUE source, bilan de
# masse) sont celles des textes — pas des variantes maison.

def test_l_evaporation_tout_latent_est_un_majorant_declare():
    """L'ancienne note disait « borne basse : aucune tour ne fait mieux » —
    c'est l'INVERSE : une tour réelle rejette 20-25 % en sensible (jusqu'à
    75-80 % par temps froid, ASHRAE) et évapore donc MOINS que le tout-latent.
    Le texte doit dire « majorant », et le plancher de jugement doit être
    latent-minimal, jamais le majorant lui-même."""
    import datacenter as d
    c = d.CONSTANTES["eau_evaporee_par_kWh_thermique_L"]
    assert "MAJORANT" in c["note"] and "SENSIBLE" in c["note"]
    assert "ASHRAE" in c["note"]
    assert 0.5 <= d.PART_LATENTE_MIN < 1.0
    pr = {"puissance_it_kw": 1000, "refroidissement": "tour_evaporative"}
    ev = d.etude(pr)["eau"]["evaporation_m3"]
    assert "majorant" in ev["incertitude"] or "Majorant" in ev["note"]
    # L'identité elle-même : V_évap = chaleur évaporative × 3600/2442.
    w = d.eau(pr, d.energie(pr))
    e_tot = d.energie(pr)["energie_totale_MWh"]["valeur"]
    attendu = e_tot * w["part_evaporative"] * (3600.0 / 2442.0)
    # Tolérance : la valeur tracée est arrondie à 4 décimales.
    assert abs(w["evaporation_m3"]["valeur"] - attendu) < 1e-3


def test_le_bilan_de_masse_de_tour_est_exact_et_source():
    """Appoint = évap × CoC/(CoC−1), purge = évap/(CoC−1) : le bilan de masse
    d'une tour ouverte, avec sa source — plus aucune grandeur d'eau muette."""
    import datacenter as d
    pr = {"puissance_it_kw": 1000, "refroidissement": "tour_evaporative",
          "cycles_concentration": 5}
    w = d.eau(pr, d.energie(pr))
    ev, ap, pu = (w["evaporation_m3"]["valeur"], w["appoint_m3"]["valeur"],
                  w["purge_m3"]["valeur"])
    # Tolérance : les valeurs tracées sont arrondies à 4 décimales chacune.
    assert abs(ap - ev * 5 / 4) < 1e-3
    assert abs(pu - ev / 4) < 1e-3
    assert "ASHRAE" in w["appoint_m3"]["source"]
    assert "ASHRAE" in w["purge_m3"]["source"]


def test_l_intensite_porte_son_millesime_partout():
    """« Un facteur sans millésime ne se défend pas » est la leçon que la page
    donne au client : elle vaut d'abord pour le moteur. Le millésime est une
    donnée SERVIE — pas une phrase — et les verdicts le répètent."""
    import datacenter as d
    import re
    assert re.search(r"20\d\d", d.INTENSITE_MILLESIME)
    assert d.INTENSITE_MILLESIME in d.INTENSITE_SOURCE
    assert d.referentiel()["intensite_millesime"] == d.INTENSITE_MILLESIME
    assert d.INTENSITE_MILLESIME in d.evaluer_intensite(56, "FR")["lecture"]
    assert d.INTENSITE_MILLESIME in d.evaluer_intensite(20, "FR")["lecture"]
    # Les valeurs recoupées en ligne pendant l'audit (Ember / AEE) : FR et UE
    # sont les publications 2023 au gramme près — si quelqu'un les « corrige »,
    # ce test exige de re-vérifier la source, pas de deviner.
    assert d.INTENSITE_RESEAU["FR"] == 56 and d.INTENSITE_RESEAU["UE"] == 242


def test_les_identites_normees_ere_wue_cue():
    """ERE = PUE × (1 − ERF) (EN 50600-4-6), WUE_source = WUE_site + EWIF × PUE
    (The Green Grid), CUE = PUE × intensité (ISO/IEC 30134-8) : des identités,
    pas des choix — si l'une casse, c'est le moteur qui a tort."""
    import datacenter as d
    pr = {"puissance_it_kw": 2000, "refroidissement": "eau_glacee",
          "part_chaleur_reutilisee": 0.3, "pays": "FR"}
    res = d.etude(pr)
    pue = res["energie"]["pue"]["valeur"]
    assert abs(res["chaleur"]["ere"]["valeur"] - pue * 0.7) < 1e-6
    w = res["eau"]
    ewif = d.EWIF_PAYS["FR"]["valeur"]
    assert abs(w["wue_source"]["valeur"]
               - (w["wue_site"]["valeur"] + ewif * pue)) < 1e-6
    cue = res["carbone"]["cue"]["valeur"]
    assert abs(cue - pue * d.INTENSITE_RESEAU["FR"] / 1000.0) < 1e-3


def test_les_reserves_de_methode_sont_ecrites():
    """Hydraulique (évaporation des retenues non comptée), plages recommandée
    contre admissible ASHRAE, provenance des plages PUE, gisements nommés de
    l'incorporé : les réserves qui rendent le référentiel défendable."""
    import datacenter as d
    assert "retenues" in d.EWIF_SOURCE and "Macknick" in d.EWIF_SOURCE
    assert "RECOMMANDÉE" in d.ASHRAE_SOURCE and "18-27" in d.ASHRAE_SOURCE
    assert "Uptime" in d.REFROIDISSEMENT_SOURCE
    assert d.referentiel()["refroidissement_source"] == d.REFROIDISSEMENT_SOURCE
    for gisement in ("Boavizta", "INIES", "ISO 14025"):
        assert gisement in d.INCORPORE_SOURCE, gisement


def test_les_sources_consultables_portent_ember_et_boavizta():
    import datacenter as d
    cles = {s["cle"] for s in d.SOURCES_CONSULTABLES}
    assert {"ember", "boavizta"} <= cles
    ember = next(s for s in d.SOURCES_CONSULTABLES if s["cle"] == "ember")
    assert "millésim" in ember["porte"]  # la raison d'être de cette entrée


# ── L'ancrage management : ISO 50001 et RSE (ISO 26000) dans l'étude ───────
# Nourri des deux guides versés à la base documentaire (livre blanc ISO 50001,
# guide RSE 2022). Le point décisif : les seuils de l'art. 11 EED sont JUGÉS
# sur l'énergie que l'étude calcule — TJ = MWh × 3,6/1000, une conversion,
# pas un modèle — et les seuils du verdict sont ceux du référentiel servi.

def test_l_article_11_est_juge_sur_l_energie_calculee():
    import datacenter as d
    seuils = d.CADRE_UE["eed_audit_smen"]
    for p_kw in (300, 1000, 12000):
        res = d.etude({"puissance_it_kw": p_kw})
        tj = res["energie"]["energie_totale_MWh"]["valeur"] * 3.6 / 1000.0
        pt = [x for x in res["conformite"] if "art. 11" in x["sujet"]][0]
        if tj >= seuils["seuil_smen_tj"]:
            attendu = "assujetti — SMÉn ISO 50001"
        elif tj >= seuils["seuil_audit_tj"]:
            attendu = "assujetti — audit énergétique"
        else:
            attendu = "sous les seuils — site seul"
        assert pt["statut"] == attendu, (p_kw, tj, pt["statut"])
        # Le détail porte le chiffre — et la bonne mise en garde par étage :
        # sous les seuils, le périmètre ENTREPRISE (le site s'additionne) ;
        # au-dessus du seuil SMÉn, « ce seul site » suffit à y entrer.
        assert fr_ok(pt["detail"], tj)
        if tj >= seuils["seuil_smen_tj"]:
            assert "ce seul site" in pt["detail"]
        else:
            assert "entreprise" in pt["detail"].lower()
    # Les trois puissances doivent couvrir les trois étages, sinon le test
    # ne prouve qu'une branche.
    statuts = {[x for x in d.etude({"puissance_it_kw": p})["conformite"]
                if "art. 11" in x["sujet"]][0]["statut"]
               for p in (300, 1000, 12000)}
    assert len(statuts) == 3


def fr_ok(texte, tj):
    """Le TJ affiché (virgule française) doit être celui du calcul."""
    import datacenter as d
    return d.fr(tj, 1) in texte


def test_le_referentiel_management_est_servi_et_complet():
    import datacenter as d
    m = d.referentiel()["management"]
    i50 = m["iso_50001"]
    for morceau in ("6.3", "6.4", "6.5", "usages énergétiques significatifs"):
        assert morceau in i50["apporte"], morceau
    assert "30134-2" in i50["ipe_naturel"]
    assert "dispense" in i50["certifiable"]
    i26 = m["iso_26000"]
    assert len(i26["questions_centrales"]) == 7
    assert "ISO 14025" in i26["achats"] and "EN 15804" in i26["achats"]
    assert "AFAQ 26000" in i26["certifiable"] and "LUCIE" in i26["certifiable"]
    assert "guide RSE 2022" in m["source"] and "ISO 50001" in m["source"]


def test_l_evaluateur_pue_exige_la_situation_de_reference():
    import datacenter as d
    exigences = " ".join(d.evaluer_pue(1.3)["exigences"])
    assert "ISO 50001" in exigences and "situation énergétique de référence" in exigences
    # …et la carte de la limite porte la norme de management.
    lim = [x for x in d.LIMITES if x["cle"] == "pue_climat"][0]
    assert any("ISO 50001" in n for n in lim["normes"])


def test_les_livrables_portent_les_chapitres_management():
    """La stratégie exporte son ancrage RSE, le dossier de décarbonation son
    ancrage SMÉn — les chapitres viennent du MÊME référentiel MANAGEMENT que
    la page, pas d'un texte parallèle."""
    import strategie_dd
    md = strategie_dd.markdown(strategie_dd.strategie({}, {"puissance_it_kw": 1000}))
    assert "Ancrage de cette stratégie dans la RSE (ISO 26000)" in md
    assert "sept questions centrales" in md and "AFAQ 26000" in md
    assert "85 TJ" in md  # le renvoi aux seuils calculés de la note

    import app as A
    import decarbonation
    d = decarbonation.dossier({"puissance_it_kw": 1000}, "PERIM", {})
    md2 = A._dossier_decarbonation_markdown(d)
    assert "Ancrage dans le management de l'énergie (ISO 50001)" in md2
    assert "situation énergétique de référence" in md2
    assert "plan de mesurage" in md2


# ── L'écoconception phase par phase (ISO/TR 14062 art. 8 · ISO 14006) ──────
# Le management des produits de construction : chaque phase du cadre — MOE
# comme industrielle — porte SON geste, sa preuve et sa clause, servis avec
# le dossier et imprimés dans l'étude de phase. Une phase sans geste
# laisserait croire que l'écoconception s'y suspend.

def test_chaque_phase_porte_son_geste_d_ecoconception():
    import ingenierie_dc as g
    assert g._verifier_ecoconception() == []
    codes = {p["code"] for p in g.PHASES}
    assert set(g.ECOCONCEPTION["gestes"]) == codes and len(codes) == 14
    # Les gestes disent le MÉTIER au bon moment : les données de cycle de vie
    # à la spécification, l'exigence écrite au marché, la revue en clôture.
    gestes = g.ECOCONCEPTION["gestes"]
    assert "FDES" in gestes["PRO"]["geste"]
    assert "CCTP" in gestes["DCE"]["geste"]
    assert "revue" in gestes["AOR"]["geste"].lower()
    assert "8.3.3" in gestes["ESQ"]["clause"]
    # …et la direction est nommée : la démarche vit dans le SME (14006).
    assert "14006" in g.ECOCONCEPTION["direction"] or "direction" in g.ECOCONCEPTION["direction"]


def test_le_dossier_et_l_etude_de_phase_portent_le_geste():
    import ingenierie_dc as g
    import app as A
    d = g.dossier({"puissance_it_kw": 1000}, "PRO")
    assert d["ecoconception"]["clause"] == g.ECOCONCEPTION["gestes"]["PRO"]["clause"]
    md = A._etude_phase_markdown(d)
    assert "Écoconception de la phase (ISO 14006 · ISO/TR 14062)" in md
    assert g.ECOCONCEPTION["gestes"]["PRO"]["preuve"][:40] in md
    assert "ISO/TR 14062, art. 8.3.5" in md
    # Le référentiel servi l'expose aussi — la page le lit là.
    assert g.referentiel()["ecoconception"]["gestes"]["DCE"]["clause"]


def test_le_garde_TOMBE_sur_une_phase_sans_geste():
    import ingenierie_dc as g
    sauve = g.ECOCONCEPTION["gestes"].pop("PRO")
    try:
        fautes = g._verifier_ecoconception()
        assert any("phase sans geste" in f and "PRO" in f for f in fautes)
    finally:
        g.ECOCONCEPTION["gestes"]["PRO"] = sauve
    assert g._verifier_ecoconception() == []


def test_le_management_datacenter_pointe_l_ecoconception():
    import datacenter as d
    m = d.referentiel()["management"]["ecoconception"]
    assert "14006" in m["titre"] and "14062" in m["titre"]
    assert "phase" in m["apporte"] and "FDES" in m["apporte"]
    assert "rapport technique" in m["certifiable"]


# ── L'AUDIT DES FICHES DE CALCUL, figé en test ────────────────────────────
# Une note de calcul annexée à une offre se défend fiche par fiche : chaque
# grandeur porte sa formule, ses entrées, sa source et son incertitude. Sur
# les vingt-trois grandeurs du moteur, quatorze avaient une case vide — dont
# des sources et, plus grave, des incertitudes absentes qui se lisent comme
# « exact ». Ce test interdit le retour du trou : une grandeur ajoutée sans
# provenance le fait tomber, quel que soit le profil.

def _grandeurs(res):
    for bloc, contenu in res.items():
        if not isinstance(contenu, dict):
            continue
        for cle, v in contenu.items():
            if isinstance(v, dict) and "valeur" in v:
                yield bloc + "." + cle, v


def test_chaque_grandeur_tracee_porte_sa_provenance_complete():
    import datacenter as d
    profils = [
        {"puissance_it_kw": 2000, "refroidissement": "tour_evaporative",
         "pays": "FR", "part_chaleur_reutilisee": 0.25, "part_renouvelable": 0.3},
        {"puissance_it_kw": 50},                       # petit site, valeurs nulles
        {"puissance_it_kw": 50000, "refroidissement": "immersion",
         "pays": "PL", "pue_cible": 1.15},             # gros site, PUE imposé
    ]
    for pr in profils:
        res = d.etude(pr)
        n = 0
        for nom, v in _grandeurs(res):
            n += 1
            for champ in ("formule", "entrees", "source", "incertitude"):
                val = v.get(champ)
                plein = bool(val) if champ == "entrees" else bool(str(val or "").strip())
                assert plein, "%s : %s manquant (profil %s)" % (nom, champ, pr)
        assert n >= 20, "seulement %d grandeurs tracées" % n


def test_les_formules_disent_leur_unite_quand_elles_multiplient_par_cent():
    """LE PIÈGE TROUVÉ PAR L'AUDIT : la fiche ERF affichait « 25 % » sous une
    formule qui rend 0,25, pendant que la fiche ERE voisine employait bien la
    fraction. Un lecteur qui applique littéralement PUE × (1 − 25) obtient un
    ERE négatif. Toute grandeur servie en % doit porter le ×100 dans sa
    formule, et toute formule qui CONSOMME une fraction doit le dire."""
    import datacenter as d
    res = d.etude({"puissance_it_kw": 2000, "part_chaleur_reutilisee": 0.25,
                   "part_renouvelable": 0.3})
    for nom, v in _grandeurs(res):
        if v.get("unite") == "%" and "/" in v.get("formule", ""):
            assert "100" in v["formule"], "%s : servi en %% sans ×100 — %s" % (nom, v["formule"])
    ere = res["chaleur"]["ere"]
    assert "FRACTION" in ere["formule"] or "fraction" in ere["formule"]
    assert any("fraction" in k for k in ere["entrees"]), ere["entrees"]
    # …et la cohérence numérique des deux fiches, pas seulement leur libellé.
    erf_pct = res["chaleur"]["erf"]["valeur"]
    pue = res["energie"]["pue"]["valeur"]
    assert abs(ere["valeur"] - pue * (1 - erf_pct / 100.0)) < 1e-6


def test_les_grandeurs_derivees_declarent_leur_heritage():
    """Une incertitude inventée est pire qu'une incertitude absente : elle se
    cite. Les grandeurs dérivées nomment donc la CHAÎNE dont elles héritent —
    le lecteur remonte jusqu'à la grandeur mesurée."""
    import datacenter as d
    res = d.etude({"puissance_it_kw": 2000, "part_chaleur_reutilisee": 0.25})
    for nom in ("energie.dcie", "energie.energie_non_it_MWh", "eau.wue_site",
                "eau.purge_m3", "chaleur.ere", "carbone.empreinte_totale_t",
                "carbone.part_incorpore_pct"):
        bloc, cle = nom.split(".")
        inc = res[bloc][cle]["incertitude"]
        assert "hérite" in inc, "%s ne déclare pas son héritage : %r" % (nom, inc)
    # Les deux grandeurs CONTRACTUELLES disent qu'elles sont exactes — et
    # pourquoi ce n'est pas une garantie de performance.
    for nom in ("carbone.ref", "chaleur.erf"):
        bloc, cle = nom.split(".")
        inc = res[bloc][cle]["incertitude"]
        assert inc.startswith("exact"), nom
        assert "contract" in inc or "déclarée" in inc, nom


# ── LE RAG AU SERVICE DE LA RÉDACTION : la couverture point par point ─────
# Une pièce déclare ce qu'elle doit contenir ; la base répond, ou non. Ce que
# ces tests protègent : le silence de la base sur un point est DIT, et il est
# distingué du cas où la base n'a pas répondu du tout.

def _chercheur(sujets_connus):
    """Une base qui ne connaît que certains sujets — injectée, donc testable
    sans PostgreSQL ni embeddings."""
    def chercher(requete, k):
        for mot in sujets_connus:
            if mot.lower() in requete.lower():
                return [{"doc_id": "d" * 32, "title": "Doc " + mot, "score": 0.7}]
        return []
    return chercher


def test_la_couverture_nomme_les_points_que_la_base_ne_documente_pas():
    import ingenierie_dc as g
    c = g.couverture_documentaire("PRO", "PRO-04", _chercheur(["livraison"]))
    assert c["resume"]["total"] == len(g.piece("PRO", "PRO-04")["contenu"])
    assert c["resume"]["couverts"] == 1
    assert c["resume"]["a_ecrire"] == c["resume"]["total"] - 1
    aecrire = [p for p in c["points"] if p["etat"] == "a_ecrire"]
    assert aecrire and all(not p["documents"] for p in aecrire)
    md = g.couverture_markdown(c)
    for p in aecrire:
        assert p["point"] in md and "à écrire depuis le projet" in md
    # La réserve accompagne TOUJOURS le constat : « couvert » ne veut pas dire
    # « répondu ». Sans elle, le tableau se lit comme un quitus.
    assert "jamais qu'il répond" in md


def test_une_base_muette_n_est_pas_une_base_sans_reponse():
    """Distinction qui compte : « aucun document sur ce point » est un
    constat ; « la base n'a pas répondu » est une panne. Les confondre ferait
    annoncer un trou documentaire là où il y a une base éteinte."""
    import ingenierie_dc as g
    vide = g.couverture_documentaire("PRO", "PRO-04", lambda r, k: [])
    assert vide["resume"]["a_ecrire"] == vide["resume"]["total"]
    assert vide["resume"]["inconnus"] == 0
    assert "AUCUN" in vide["lecture"]

    def morte(r, k):
        raise RuntimeError("base injoignable")
    ko = g.couverture_documentaire("PRO", "PRO-04", morte)
    assert ko["resume"]["inconnus"] == ko["resume"]["total"]
    assert ko["resume"]["a_ecrire"] == 0
    assert "INDÉTERMINÉE" in ko["lecture"]
    assert "indéterminée" in g.couverture_markdown(ko)


def test_la_couverture_interroge_avec_le_contexte_du_projet():
    """La requête d'un point porte la requête de la pièce — donc le profil du
    projet : famille de refroidissement, pays, secteur. Sans cela, la base
    répondrait la même chose pour tous les projets."""
    import ingenierie_dc as g
    vues = []

    def espion(requete, k):
        vues.append(requete)
        return []
    # Une pièce dont la DISCIPLINE rend le choix de refroidissement
    # discriminant : sur une pièce où il ne l'est pas (un tableau de surfaces),
    # le module l'écarte volontairement, et c'est ce qui protège la pertinence.
    g.couverture_documentaire("APD", "SPC-HVAC", espion,
                              {"refroidissement": "immersion", "pays": "SE"})
    assert vues, "aucune recherche lancée"
    assert all("centre de données" in r for r in vues)
    # Chaque requête est propre à SON point : autant de requêtes que de points.
    assert len(set(vues)) == len(vues)
    joint = " ".join(vues).lower()
    assert "immersion" in joint, joint[:200]
    # …et le PAYS, lui, n'entre PAS dans une pièce CVC : il ne discrimine que
    # là où le mix électrique ou l'eau comptent (environnement, élec, fluides).
    # L'y ajouter partout diluerait la recherche — ce contrôle protège cette
    # retenue autant que l'ajout ci-dessus.
    assert "suède" not in joint, "le pays s'est invité dans une pièce CVC"
    env = []
    g.couverture_documentaire("APD", "SPC-CONSO", lambda r, k: env.append(r) or [],
                              {"refroidissement": "immersion", "pays": "SE"})
    assert env, "SPC-CONSO introuvable : le contrôle du pays ne prouve rien"
    assert "suède" in " ".join(env).lower(), env[0][-160:]


def test_une_piece_inconnue_ne_produit_pas_de_couverture_inventee():
    import ingenierie_dc as g
    assert g.couverture_documentaire("PRO", "PRO-999", _chercheur([])) is None
    assert g.couverture_markdown(None) == ""


# ── nb_serveurs par défaut : une hypothèse, déclarée comme telle ───────────
#
# LE DÉFAUT CORRIGÉ. Quand "nb_serveurs" n'est pas saisi, le moteur l'estime
# depuis la puissance informatique — un littéral nu (0,5 kW/serveur), sans
# nom ni source, et le résultat partait dans les entrées comme si c'était une
# donnée du projet. Le bloc "équipements informatiques" de la même page
# dérive SON PROPRE compte, par densité de baie : les deux ne se recoupent
# pas, et rien ne le disait au lecteur.

def test_nb_serveurs_par_defaut_est_declare_comme_une_hypothese():
    etude = dc.etude(dict(PROFIL_TEMOIN, nb_serveurs=None))
    inc = etude["carbone"]["incorpore_serveurs_t"]
    assert inc["entrees"]["nb serveurs"] == int(
        PROFIL_TEMOIN["puissance_it_kw"]
        / dc.CONSTANTES["kw_par_serveur_estime"]["valeur"])
    assert "hypothèse du moteur" in inc["entrees"]["origine"], inc["entrees"]


def test_nb_serveurs_saisi_n_est_pas_requalifie_en_hypothese():
    """Le contraste qui prouve que la clé "origine" suit vraiment la
    provenance, plutôt que d'afficher toujours le même texte."""
    etude = dc.etude(dict(PROFIL_TEMOIN, nb_serveurs=750))
    inc = etude["carbone"]["incorpore_serveurs_t"]
    assert inc["entrees"]["nb serveurs"] == 750
    assert inc["entrees"]["origine"] == "valeur fournie"


def test_le_kw_par_serveur_estime_est_nomme_et_publie_au_referentiel():
    """La constante ne doit plus être un littéral nu au point d'usage."""
    c = dc.referentiel()["constantes"]["kw_par_serveur_estime"]
    assert c["valeur"] == 0.5
    assert "hypothèse" in c["source"].lower()


# ── « Climat froid » : une seule table, lue aux deux endroits ──────────────
#
# LE DÉFAUT CORRIGÉ. conformite() et leviers() codaient chacun leur propre
# tuple de pays « climat froid », et les deux tuples différaient (l'Irlande
# figurait dans l'un, pas dans l'autre) : le verdict de conformité PUE d'un
# site irlandais ou balte dépendait de l'écran consulté plutôt que d'une
# source unique. Une seule table nommée, désormais — CADRE_UE["cndcp"]
# ["pays_climat_froid"] — lue par les deux fonctions.

def test_les_deux_fonctions_lisent_la_meme_table_climat_froid():
    """Prouvé par mutation, pas par lecture du code : on remplace la table par
    une liste de contrôle, et on vérifie que LES DEUX fonctions en tiennent
    compte — la preuve qu'aucune des deux n'a sa propre copie figée."""
    sauve = dc.CADRE_UE["cndcp"]["pays_climat_froid"]
    try:
        dc.CADRE_UE["cndcp"]["pays_climat_froid"] = ("PL",)
        etude_pl = dc.etude({"puissance_it_kw": 1000, "pays": "PL",
                             "refroidissement": "eau_glacee", "taux_charge": 0.65})
        conf = dc.conformite({"puissance_it_kw": 1000, "pays": "PL"}, etude_pl)
        pue_pt = next(p for p in conf if p["sujet"] == "PUE — repère de marché")
        assert "1,3" in pue_pt["detail"], (
            "conformite() n'a pas suivi la table mutée — elle garde son "
            "propre tuple en dur")

        etude_evap = dc.etude({"puissance_it_kw": 1000, "pays": "PL",
                               "refroidissement": "tour_evaporative",
                               "taux_charge": 0.65, "part_evaporative": 0.05})
        lv = dc.leviers({"puissance_it_kw": 1000, "pays": "PL"}, etude_evap)
        assert any("adiabatique" in l["titre"].lower() for l in lv), (
            "leviers() n'a pas suivi la table mutée — elle garde son propre "
            "tuple en dur")
    finally:
        dc.CADRE_UE["cndcp"]["pays_climat_froid"] = sauve


def test_la_table_climat_froid_est_publiee_et_coherente_entre_pays():
    pays = dc.CADRE_UE["cndcp"]["pays_climat_froid"]
    assert set(pays) <= set(dc.EWIF_PAYS), (
        "la table climat froid cite un pays absent du référentiel des pays")


def test_conformite_et_leviers_s_accordent_desormais_sur_l_irlande():
    """L'Irlande est le cas qui divergeait avant correctif (présente dans le
    tuple à cinq pays de conformite(), absente du tuple à quatre de
    leviers()) : les deux doivent maintenant la traiter pareil."""
    assert ("IE" in dc.CADRE_UE["cndcp"]["pays_climat_froid"]) == False
    etude = dc.etude({"puissance_it_kw": 1000, "pays": "IE",
                      "refroidissement": "eau_glacee", "taux_charge": 0.65})
    conf = dc.conformite({"puissance_it_kw": 1000, "pays": "IE"}, etude)
    pue_pt = next(p for p in conf if p["sujet"] == "PUE — repère de marché")
    assert "climat tempéré ou chaud" in pue_pt["detail"]


# ── leviers() : seize coefficients nommés, et deux fondements corrigés ─────
#
# LE DÉFAUT CORRIGÉ. Les coefficients qui chiffrent les leviers vivaient en
# littéraux nus, sans nom ni nature déclarée. Deux d'entre eux citaient en
# plus une norme réelle (ASHRAE TC 9.9 ; ISO/IEC 30134-6) comme fondement
# d'un NOMBRE que cette norme ne publie pas — le texte existe et porte sur le
# bon sujet, mais pas sur le chiffre attaché.

def test_les_seize_coefficients_sont_nommes_avec_leur_nature():
    assert len(dc.LEVIERS_HYPOTHESES) == 16, sorted(dc.LEVIERS_HYPOTHESES)
    for cle, h in dc.LEVIERS_HYPOTHESES.items():
        assert h["nature"] == "hypothèse du moteur", cle
        assert isinstance(h["valeur"], (int, float)), cle
        assert len(h["note"]) >= 20, cle


def test_les_valeurs_chiffrees_des_leviers_n_ont_pas_bouge():
    """Le seul changement voulu est la PROVENANCE affichée, jamais le
    résultat : les mêmes profils doivent rendre les mêmes chiffres qu'avant
    le correctif."""
    profil = {"puissance_it_kw": 1000, "pays": "FR",
              "refroidissement": "tour_evaporative", "taux_charge": 0.50,
              "classe_ashrae": "A2"}
    etude = dc.etude(profil)
    lv = {l["titre"]: l for l in dc.leviers(profil, etude)}
    attendu = {
        "Raccordement à un réseau de chaleur (30 % de l'énergie valorisée)": 320.6,
        "Allonger la durée de vie des serveurs de 5 à 7 ans": 134.4,
        "Refroidissement liquide direct (plaques froides)": 29.4,
        "Consolider les charges pour remonter le taux d'utilisation": 29.4,
        "Passer de la classe ASHRAE A2 à A3": 14.7,
        "Basculer vers un rejet sec (dry cooler) sur la majorité de l'année": -19.6,
    }
    assert set(lv) == set(attendu), set(lv) ^ set(attendu)
    for titre, gain in attendu.items():
        assert lv[titre]["gain_co2_t"] == gain, (titre, lv[titre]["gain_co2_t"])


def test_le_fondement_ashrae_ne_pretend_plus_publier_le_gain_de_pue():
    profil = {"puissance_it_kw": 1000, "pays": "FR",
              "refroidissement": "eau_glacee", "taux_charge": 0.65,
              "classe_ashrae": "A2"}
    etude = dc.etude(profil)
    lv = dc.leviers(profil, etude)
    ashrae = next(l for l in lv if l["titre"] == "Passer de la classe ASHRAE A2 à A3")
    assert "Hypothèse du moteur" in ashrae["fondement"]
    assert "ne publie pas" in ashrae["fondement"] or "pas le gain" in ashrae["fondement"]


def test_le_fondement_reseau_de_chaleur_ne_pretend_plus_publier_la_part_valorisable():
    profil = {"puissance_it_kw": 1000, "pays": "FR",
              "refroidissement": "immersion", "taux_charge": 0.65}
    etude = dc.etude(profil)
    lv = dc.leviers(profil, etude)
    chaleur = [l for l in lv if l["titre"].startswith("Raccordement à un réseau")]
    if chaleur:  # ne se déclenche que si res["chaleur"]["erf"] < 5
        assert "Hypothèse du moteur" in chaleur[0]["fondement"]
        assert "ne publie" in chaleur[0]["fondement"]
