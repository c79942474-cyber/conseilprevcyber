# -*- coding: utf-8 -*-
"""Les équipements informatiques : quantités, part d'investissement, scope 3
et durée de vie.

Ce que ces tests protègent en priorité : le module ne doit JAMAIS confirmer
le message commercial (« prolongez, vous gagnez ») sans l'avoir calculé, et
il ne doit jamais présenter l'informatique comme une part des lots travaux —
elle n'y est pas.
"""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import equipements_it as eq  # noqa: E402


# ── La nomenclature ────────────────────────────────────────────────────────

def test_le_module_se_declare_sain_a_l_import():
    s = eq.sante()
    assert s["problemes"] == []
    assert s["postes"] >= 8


def test_les_baies_posees_peuvent_accueillir_la_puissance_demandee():
    for p_kw in (200.0, 1000.0, 5000.0):
        for d in eq.DENSITES:
            n = eq.nomenclature(p_kw, d)
            assert n["ok"], n.get("motif")
            assert n["baies"] * n["kw_par_baie"] >= p_kw, (p_kw, d)


def test_une_densite_plus_forte_demande_moins_de_baies():
    faible = eq.nomenclature(1000.0, "classique")
    forte = eq.nomenclature(1000.0, "ia_liquide")
    assert forte["baies"] < faible["baies"]


def test_la_nomenclature_refuse_une_puissance_absurde():
    for mauvais in (0, -50, None):
        assert eq.nomenclature(mauvais).get("ok") is not True


def test_une_densite_inconnue_est_refusee_et_non_devinee():
    r = eq.nomenclature(1000.0, "supersonique")
    assert r.get("ok") is not True
    assert "supersonique" in (r.get("motif") or "")


def test_chaque_ligne_porte_sa_regle_de_quantite_et_son_geste_durable():
    n = eq.nomenclature(1000.0)
    for l in n["lignes"]:
        assert l["regle"].strip(), l["cle"]
        assert l["achat_durable"].strip(), l["cle"]
        assert l["pourquoi"].strip(), l["cle"]


def test_le_total_est_la_somme_des_lignes():
    n = eq.nomenclature(1000.0)
    somme = sum(l["prix_total_eur"] for l in n["lignes"])
    assert abs(somme - n["total_eur"]) <= 1
    assert (n["total_indispensable_eur"] + n["total_utile_eur"]
            == pytest.approx(n["total_eur"], abs=1))


def test_le_carbone_du_serveur_vient_du_moteur_et_n_est_pas_recopie():
    """Une seconde table de facteurs divergerait au premier ajustement.

    Ce fichier est partagé entre les deux sites, qui n'embarquent pas le même
    moteur : conseilprevcyber a `datacenter` et publie un facteur par
    serveur, Sentinel a `empreinte_sites` et exprime l'empreinte par MWh. Le
    test éprouve donc la RÈGLE, pas un moteur : quand le moteur local publie
    le facteur, c'est LUI qui sort ; sinon, le repli est NOMMÉ comme tel.
    """
    n = eq.nomenclature(1000.0)
    serveurs = [l for l in n["lignes"] if l["cle"] == "serveurs"][0]
    publie = (getattr(eq._D, "INCORPORE", {}) or {}).get("serveur_kgCO2e") \
        if eq._D is not None else None

    if publie and publie.get("valeur"):
        assert serveurs["carbone_unitaire_kg"] == pytest.approx(publie["valeur"])
        assert serveurs["duree_vie_ans"] == pytest.approx(publie["duree_vie_ans"])
        assert eq._MOTEUR in n["serveur_source"]
    else:
        assert serveurs["carbone_unitaire_kg"] == eq.SERVEUR_REPLI_KG
        assert "epli" in n["serveur_source"], n["serveur_source"]


def test_l_intensite_carbone_est_lue_au_moteur_local_et_jamais_recopiee():
    """Les deux sites ne publient pas la même table — 56 g/kWh d'un côté,
    45 de l'autre pour la France. L'écart est documenté par chacun ; le
    module ne le moyenne pas, il lit celle qui est là."""
    assert eq._D is not None, "aucun moteur lié : le module ne saurait rien du mix"
    pays = eq.pays_connus()
    assert "FR" in pays and len(pays) >= 8, pays
    table = getattr(eq._D, "INTENSITE_RESEAU", None) or getattr(eq._D, "INTENSITE")
    for code in ("FR", "DE", "PL"):
        if code in table:
            assert eq._intensite_pays(code) == pytest.approx(float(table[code]))
    p = eq.prolongation(1000.0, 5, 8, "FR")
    assert p["intensite_g"] == pytest.approx(float(table["FR"]))


def test_un_pays_absent_de_la_table_locale_n_est_pas_devine():
    assert eq._intensite_pays("ZZ") is None
    assert eq._intensite_pays(None) is None


def test_les_postes_indispensables_pesent_l_essentiel():
    n = eq.nomenclature(1000.0)
    assert n["total_indispensable_eur"] > n["total_utile_eur"]


def test_l_incertitude_est_annoncee_et_non_tue():
    n = eq.nomenclature(1000.0)
    assert n["incertitude_prix_pct"] > 0
    assert n["incertitude_carbone_pct"] > 0
    assert "devis" in n["prix_source"].lower()


# ── La part dans l'investissement ──────────────────────────────────────────

def test_la_part_dans_les_lots_travaux_est_nulle_dans_tous_les_perimetres():
    """Le constat de périmètre : les lots ne portent pas d'informatique."""
    n = eq.nomenclature(1000.0)
    for per in eq.PERIMETRES:
        p = eq.part_investissement(n, 25_000_000, per)
        assert p["ok"], per
        assert p["part_lots_pct"] == 0.0, per
        assert "aménagement des salles" in p["lots_dit"]


def test_le_pourcentage_du_total_n_est_calcule_que_si_un_seul_maitre_ouvrage():
    n = eq.nomenclature(1000.0)
    propre = eq.part_investissement(n, 25_000_000, "propre")
    coloc = eq.part_investissement(n, 25_000_000, "colocation")
    assert propre["part_total_pct"] is not None
    assert coloc["part_total_pct"] is None
    assert "deux bilans" in coloc["lecture"]


def test_l_investissement_total_additionne_bien_les_deux_budgets():
    n = eq.nomenclature(1000.0)
    p = eq.part_investissement(n, 25_000_000, "propre")
    assert p["total_projet_eur"] == pytest.approx(25_000_000 + p["it_eur"], abs=2)
    attendu = p["it_eur"] / p["total_projet_eur"] * 100.0
    assert p["part_total_pct"] == pytest.approx(attendu, abs=0.1)


def test_en_heberge_une_enveloppe_travaux_n_est_pas_additionnee():
    """Elle appartient à l'hébergeur : l'additionner fabriquerait un
    investissement qui n'existe pas."""
    n = eq.nomenclature(1000.0)
    p = eq.part_investissement(n, 25_000_000, "heberge")
    assert p["ok"]
    assert p["enveloppe_travaux_eur"] is None
    assert p["total_projet_eur"] == p["it_eur"]
    assert "hébergeur" in p["lecture"]


def test_sans_enveloppe_le_module_renvoie_vers_l_etude_et_n_invente_rien():
    n = eq.nomenclature(1000.0)
    p = eq.part_investissement(n, None, "propre")
    assert p["part_total_pct"] is None
    assert "Sentinel" in p["lecture"]


def test_un_perimetre_inconnu_est_refuse():
    n = eq.nomenclature(1000.0)
    p = eq.part_investissement(n, 25_000_000, "sous-marin")
    assert p.get("ok") is not True
    assert "sous-marin" in p["motif"]


# ── La durée de vie : le point de bascule ──────────────────────────────────

def test_l_intensite_de_bascule_ne_depend_pas_de_la_taille_du_centre():
    """La puissance informatique se simplifie entre le gain et le coût.
    Si cette propriété tombe, une des deux formules a bougé."""
    seuils = [eq.prolongation(p, 5, 8, "FR")["intensite_bascule_g"]
              for p in (200.0, 1000.0, 5000.0, 20000.0)]
    assert max(seuils) - min(seuils) < 0.05, seuils


def test_prolonger_est_favorable_sur_un_mix_decarbone_et_pas_sur_un_mix_carbone():
    fr = eq.prolongation(1000.0, 5, 8, "FR")
    pl = eq.prolongation(1000.0, 5, 8, "PL")
    assert fr["verdict"] == "favorable"
    assert pl["verdict"] == "defavorable"
    assert fr["intensite_g"] < fr["intensite_bascule_g"] < pl["intensite_g"]


def test_le_verdict_defavorable_dit_le_levier_qui_reste():
    pl = eq.prolongation(1000.0, 5, 8, "PL")
    assert "décarboner" in pl["lecture"]


def test_le_vieillissement_compte_est_la_MOITIE_de_l_allongement():
    """Deux cycles de renouvellement se comparent par leur âge MOYEN, qui
    vaut la moitié du cycle. Compter (C−B) au lieu de (C−B)/2 doublerait le
    coût et renverserait des verdicts."""
    p = eq.prolongation(1000.0, 5, 9, "FR")
    assert p["vieillissement_moyen_ans"] == pytest.approx(2.0)


def test_le_gain_de_fabrication_suit_bien_la_difference_des_inverses():
    p = eq.prolongation(1000.0, 5, 8, "FR")
    attendu = p["carbone_fabrication_kg"] * (1 / 5.0 - 1 / 8.0)
    assert p["gain_fabrication_kg_an"] == pytest.approx(attendu, rel=1e-3)


def test_le_cout_d_exploitation_se_refait_a_la_main():
    p = eq.prolongation(1000.0, 5, 8, "FR", pue=1.0)
    kwh = 1000.0 * 8760 * eq.DERIVE_EFFICACITE_AN * 1.5
    assert p["kwh_supplementaires_an"] == pytest.approx(kwh, rel=1e-6)
    assert p["cout_exploitation_kg_an"] == pytest.approx(
        kwh * p["intensite_g"] / 1000.0, rel=1e-3)


def test_le_net_est_bien_la_difference_des_deux_termes():
    for pays in ("FR", "DE", "PL", "SE"):
        p = eq.prolongation(1000.0, 5, 8, pays)
        assert p["net_kg_an"] == pytest.approx(
            p["gain_fabrication_kg_an"] - p["cout_exploitation_kg_an"], abs=2)


def test_un_pue_plus_eleve_abaisse_le_seuil_de_bascule():
    """Chaque watt informatique supplémentaire traîne son refroidissement."""
    a = eq.prolongation(1000.0, 5, 8, "FR", pue=1.0)["intensite_bascule_g"]
    b = eq.prolongation(1000.0, 5, 8, "FR", pue=1.5)["intensite_bascule_g"]
    assert b < a
    assert b == pytest.approx(a / 1.5, rel=1e-3)


def test_a_derive_nulle_prolonger_paie_toujours():
    """Cas limite : si le matériel ne perd rien en efficacité, il n'y a plus
    de contrepartie. Le module doit le dire, pas buter."""
    p = eq.prolongation(1000.0, 5, 8, "PL", derive_an=0.0)
    assert p["ok"]
    assert p["verdict"] == "favorable"
    assert p["cout_exploitation_kg_an"] == 0


def test_la_duree_maximale_payante_annule_bien_le_net():
    """L'intensité est choisie pour que la bascule tombe DANS le domaine du
    calcul : un test qui se contente de sauter ne démontre rien."""
    p = eq.prolongation(1000.0, 5, 8, intensite_g=91.3)
    cible = p["duree_max_payante_ans"]
    assert 5 < cible < 15, cible
    q = eq.prolongation(1000.0, 5, cible, intensite_g=91.3)
    assert abs(q["net_kg_an"]) < 0.02 * q["gain_fabrication_kg_an"]
    assert q["verdict"] in ("favorable", "defavorable")


def test_sur_un_reseau_carbone_la_duree_maximale_tombe_sous_la_duree_actuelle():
    p = eq.prolongation(1000.0, 5, 8, "PL")
    assert p["duree_max_payante_ans"] < 5
    assert "AUCUN allongement" in p["lecture"]


def test_le_module_refuse_de_prolonger_au_dela_de_son_domaine():
    r = eq.prolongation(1000.0, 5, 18, "FR")
    assert r.get("ok") is not True
    assert "quinze ans" in r["motif"]


def test_le_module_refuse_un_raccourcissement_deguise_en_allongement():
    r = eq.prolongation(1000.0, 8, 5, "FR")
    assert r.get("ok") is not True
    assert "ALLONGEMENT" in r["motif"]


def test_le_module_refuse_un_pays_dont_il_ignore_le_mix():
    r = eq.prolongation(1000.0, 5, 8, "XX")
    assert r.get("ok") is not True
    assert "n'a" not in r["motif"] or "suppose" in r["motif"]


def test_le_module_refuse_un_pue_physiquement_impossible():
    r = eq.prolongation(1000.0, 5, 8, "FR", pue=0.8)
    assert r.get("ok") is not True
    assert "impossible" in r["motif"]


def test_la_reserve_non_carbone_est_toujours_dite():
    """Un gain carbone ne justifie pas de garder un serveur sans correctifs."""
    p = eq.prolongation(1000.0, 5, 8, "FR")
    for mot in ("sécurité", "support constructeur", "correctifs"):
        assert mot in p["reserve"]


def test_les_formules_sont_publiees_pour_etre_refaites():
    p = eq.prolongation(1000.0, 5, 8, "FR")
    assert len(p["formules"]) >= 4
    assert any("bascule" in f.lower() for f in p["formules"])


# ── Le scope 3 ─────────────────────────────────────────────────────────────

def test_le_bilan_scope3_couvre_toutes_les_lignes_de_la_nomenclature():
    n = eq.nomenclature(1000.0)
    b = eq.bilan_scope3(n)
    total_lignes = sum(l["carbone_total_kg"] for l in n["lignes"])
    assert b["total_t"] == pytest.approx(total_lignes / 1000.0, abs=0.2)
    assert b["categorie_1_t"] + b["categorie_2_t"] == pytest.approx(
        b["total_t"], abs=0.2)


def test_le_bilan_dit_ce_qu_il_ne_couvre_pas():
    """Un bilan muet sur ses trous se lit comme un bilan complet."""
    b = eq.bilan_scope3(eq.nomenclature(1000.0))
    assert len(b["non_couvert"]) >= 3
    joint = " ".join(b["non_couvert"])
    assert "12" in joint and "4" in joint


def test_le_bilan_se_presente_en_complement_des_scopes_1_et_2():
    b = eq.bilan_scope3(eq.nomenclature(1000.0))
    assert "scope" in b["complement"].lower()


def test_l_effet_de_la_prolongation_avertit_du_transfert_entre_scopes():
    """Le gain se lit au scope 3 et le coût au scope 2 : ne montrer que le
    premier afficherait une amélioration là où le bilan se dégrade."""
    n = eq.nomenclature(1000.0)
    b = eq.bilan_scope3(n, eq.prolongation(1000.0, 5, 8, "PL"))
    eff = b["effet_prolongation"]
    assert eff["annualise_apres_t"] < b["annualise_t"]
    assert eff["verdict"] == "defavorable"
    assert "scope 2" in eff["avertissement"]


def test_sans_prolongation_aucun_effet_n_est_invente():
    b = eq.bilan_scope3(eq.nomenclature(1000.0))
    assert b["effet_prolongation"] is None


def test_le_bilan_refuse_une_nomenclature_en_echec():
    assert eq.bilan_scope3({"ok": False}).get("ok") is not True
    assert eq.bilan_scope3(None).get("ok") is not True


# ── Le référentiel servi ───────────────────────────────────────────────────

def test_le_referentiel_publie_ses_hypotheses_chiffrees():
    r = eq.referentiel()
    for cle in ("version", "postes", "densites", "perimetres",
                "derive_efficacite_an", "incertitude_prix_pct"):
        assert cle in r, cle
    assert r["derive_efficacite_an"] > 0


def test_toutes_les_valeurs_servies_sont_serialisables():
    import json
    n = eq.nomenclature(1000.0)
    charge = {"nomenclature": n,
              "part": eq.part_investissement(n, 25_000_000, "propre"),
              "prolongation": eq.prolongation(1000.0, 5, 8, "FR"),
              "scope3": eq.bilan_scope3(n),
              "referentiel": eq.referentiel()}
    txt = json.dumps(charge, ensure_ascii=False)
    assert len(txt) > 2000
    assert "NaN" not in txt and "Infinity" not in txt


def test_aucune_grandeur_servie_n_est_nan_ou_infinie():
    def parcourir(v, chemin=""):
        if isinstance(v, dict):
            for k, x in v.items():
                parcourir(x, chemin + "/" + str(k))
        elif isinstance(v, list):
            for i, x in enumerate(v):
                parcourir(x, "%s[%d]" % (chemin, i))
        elif isinstance(v, float):
            assert not math.isnan(v) and not math.isinf(v), chemin

    n = eq.nomenclature(1000.0)
    parcourir(n)
    parcourir(eq.prolongation(1000.0, 5, 8, "FR"))
    parcourir(eq.bilan_scope3(n, eq.prolongation(1000.0, 5, 8, "FR")))
