"""Le pilotage de programme — ce qui s'additionne, ce qui se pondère, ce qui non.

CE QUI EST ÉPROUVÉ. Les propriétés qui séparent une consolidation honnête d'une
console qui rassure :

  · un PUE de programme se PONDÈRE — la moyenne arithmétique des sites est
    fausse, et c'est celle qu'on calcule spontanément ;
  · un total dit sur combien de sites il porte, et NOMME ceux qui manquent ;
  · un ratio dont les deux termes ne couvrent pas le même périmètre n'est pas
    rendu — il ne décrirait aucun ensemble réel ;
  · le chemin critique est le site le plus TARDIF, jamais une moyenne ;
  · le régime administratif ne se consolide pas, et la vue le dit plutôt que
    de l'omettre ;
  · « zéro défaut » n'est pas « zéro réserve », et le taux de levée seul cache
    la réserve bloquante qui interdit l'exploitation.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import programme_dc as P  # noqa: E402


TROIS = [
    {"nom": "Paris", "pays": "FR", "nature": "greenfield", "phase": "PRO",
     "puissance_it_kw": 10000, "taux_charge": 0.7, "pue": 1.22,
     "capex_eur": 180e6, "opex_eur_an": 9e6, "mise_en_service": "2028-06",
     "regime_icpe": "E"},
    {"nom": "Francfort", "pays": "DE", "nature": "brownfield",
     "phase": "EXE-VISA", "puissance_it_kw": 4000, "taux_charge": 0.6,
     "pue": 1.35, "capex_eur": 60e6, "opex_eur_an": 4e6,
     "mise_en_service": "2027-11"},
    {"nom": "Madrid", "pays": "ES", "nature": "brownfield", "phase": "AOR",
     "puissance_it_kw": 1500, "taux_charge": 0.8, "pue": 1.40,
     "capex_eur": 22e6, "opex_eur_an": 1.6e6, "mise_en_service": "2026-12",
     "receptionne": True, "reserves_ouvertes": 12, "reserves_levees": 180,
     "reserves_bloquantes": 1},
]


# ── Ce qui se pondère, et pourquoi la moyenne simple est fausse ────────────

def test_le_pue_de_programme_est_pondere_et_non_moyenne():
    """LE DÉFAUT QUE CETTE RÈGLE EMPÊCHE, et qui est le plus tentant de tous.
    La moyenne arithmétique des PUE de site est ce qu'on calcule
    spontanément — et elle ne correspond à aucune réalité physique. Un site de
    dix mégawatts et un site de cent kilowatts ne pèsent pas pareil dans
    l'énergie totale du programme."""
    v = P.consolider(TROIS)
    pondere = v["pue_programme"]["valeur"]
    simple = sum(s["pue"] for s in TROIS) / len(TROIS)
    assert abs(pondere - simple) > 0.02, (
        "le PUE de programme coïncide avec la moyenne simple : la pondération "
        "n'a probablement pas lieu (pondéré %.4f, simple %.4f)"
        % (pondere, simple))
    # Recalculé à la main sur l'énergie informatique de chaque site.
    num = sum(s["pue"] * s["puissance_it_kw"] * s["taux_charge"] for s in TROIS)
    den = sum(s["puissance_it_kw"] * s["taux_charge"] for s in TROIS)
    assert abs(pondere - num / den) < 1e-9


def test_le_pue_se_pondere_sur_la_puissance_faute_de_taux_de_charge():
    """Imparfait, et c'est mieux que rien — à condition que ce soit dit. Le
    poids employé est rendu avec la valeur."""
    sites = [dict(s) for s in TROIS]
    for s in sites:
        s.pop("taux_charge")
    v = P.consolider(sites)
    num = sum(s["pue"] * s["puissance_it_kw"] for s in sites)
    den = sum(s["puissance_it_kw"] for s in sites)
    assert abs(v["pue_programme"]["valeur"] - num / den) < 1e-9


def test_un_site_sans_pue_ne_fausse_pas_la_pondération():
    """Il est écarté du calcul ET nommé dans les absents : compté à zéro, il
    tirerait le PUE du programme vers le bas et ferait croire à une
    performance."""
    v = P.consolider(TROIS + [{"nom": "Site 4", "puissance_it_kw": 50000}])
    assert "Site 4" in v["pue_programme"]["sites_absents"]
    assert abs(v["pue_programme"]["valeur"]
               - P.consolider(TROIS)["pue_programme"]["valeur"]) < 1e-9


# ── Le périmètre voyage avec le total ─────────────────────────────────────

def test_chaque_total_dit_sur_combien_de_sites_il_porte():
    """Un CAPEX calculé sur quatre sites sur sept n'est pas le CAPEX du
    programme : c'est un sous-total, et le présenter autrement est la façon la
    plus rapide de perdre la confiance d'un comité — parce qu'il s'en
    apercevra."""
    v = P.consolider(TROIS + [{"nom": "Intention"}])
    for cle in ("capacite_engagee_kw", "capex_eur", "opex_eur_an"):
        agr = v[cle]
        assert agr["sites_comptes"] == 3, cle
        assert agr["complet"] is False, cle
        assert "Intention" in agr["sites_absents"], cle


def test_un_total_complet_se_declare_complet():
    v = P.consolider(TROIS)
    assert v["capacite_engagee_kw"]["complet"] is True
    assert v["capacite_engagee_kw"]["sites_absents"] == []


def test_un_site_connu_par_son_seul_nom_compte_dans_l_effectif():
    """C'est exactement l'information utile au début d'un programme, quand la
    moitié des sites n'est qu'une intention. L'écarter ferait croire à un
    programme plus petit qu'il n'est."""
    v = P.consolider(TROIS + [{"nom": "Intention"}])
    assert v["sites"] == 4


def test_la_lecture_ouvre_sur_le_perimetre_et_non_sur_les_totaux():
    """Un tableau de bord qui ouvre sur ses totaux fait croire à un état
    complet."""
    v = P.consolider(TROIS + [{"nom": "Intention"}])
    assert "SOUS-TOTAUX" in v["lecture"]
    assert v["lecture"].index("SOUS-TOTAUX") < v["lecture"].index("kW engagés")


# ── Les ratios, et leur refus ─────────────────────────────────────────────

def test_le_capex_par_kw_est_le_ratio_de_reference():
    """Sur un centre de données, le coût au mètre carré ne veut rien dire : le
    lot technique pèse l'essentiel de l'enveloppe."""
    v = P.consolider(TROIS)
    attendu = sum(s["capex_eur"] for s in TROIS) / sum(
        s["puissance_it_kw"] for s in TROIS)
    assert abs(v["capex_par_kw"]["valeur"] - attendu) < 1e-6
    assert v["capex_par_kw"]["unite"] == "€/kW"


def test_un_ratio_sur_deux_perimetres_differents_n_est_pas_rendu():
    """LE DÉFAUT QUE CETTE RÈGLE EMPÊCHE. Si le CAPEX est connu sur deux sites
    et la puissance sur trois, leur quotient ne décrit aucun ensemble réel — et
    il aurait l'air d'un ratio."""
    sites = [dict(s) for s in TROIS]
    sites[2].pop("capex_eur")
    v = P.consolider(sites)
    assert v["capex_par_kw"]["valeur"] is None
    assert "même périmètre" in v["capex_par_kw"]["pourquoi"]


def test_un_ratio_sans_donnee_du_tout_dit_laquelle_manque():
    v = P.consolider([{"nom": "A", "puissance_it_kw": 100}])
    assert v["capex_par_kw"]["valeur"] is None
    assert v["capex_par_kw"]["pourquoi"]


# ── Le chemin critique ────────────────────────────────────────────────────

def test_le_chemin_critique_est_le_site_le_plus_tardif():
    """Pas une moyenne : un programme livre quand son DERNIER site livre, et
    une dérive moyenne masque précisément celui qui commande la date."""
    cc = P.consolider(TROIS)["chemin_critique"]
    assert cc["connu"] is True
    assert cc["site"] == "Paris"
    assert cc["date"] == "2028-06"


def test_les_sites_sans_date_peuvent_deplacer_le_chemin_critique():
    """Le dire est la seule réponse honnête : le site le plus tardif connu
    n'est pas forcément le plus tardif."""
    cc = P.consolider(TROIS + [{"nom": "Intention"}])["chemin_critique"]
    assert cc["sites_sans_date"] == 1
    assert "peuvent le déplacer" in cc["note"]


def test_sans_aucune_date_il_n_y_a_pas_de_chemin_critique():
    """« Inconnu » avec sa raison, plutôt qu'une date inventée ou un silence."""
    cc = P.consolider([{"nom": "A"}, {"nom": "B"}])["chemin_critique"]
    assert cc["connu"] is False
    assert "liste de sites" in cc["pourquoi"]


# ── Ce qui ne se consolide pas ────────────────────────────────────────────

def test_le_regime_administratif_est_declare_non_consolidable():
    """Une absence silencieuse se lirait comme un oubli. C'est la grandeur
    qu'un comité demande le plus souvent d'agréger, et précisément celle qui
    ne s'agrège pas : la nomenclature est nationale."""
    nc = P.consolider(TROIS)["non_consolidables"]
    assert nc
    assert "nationale" in nc[0]["pourquoi"] or "française" in nc[0]["pourquoi"]
    assert nc[0]["a_la_place"]
    assert len(nc[0]["sites"]) == 3


def test_un_site_non_crible_est_dit_non_crible_et_non_conforme():
    ligne = P.consolider(TROIS)["non_consolidables"][0]["sites"]
    par_nom = {s["nom"]: s for s in ligne}
    assert par_nom["Francfort"]["regime"] == "non criblé"


def test_un_programme_multi_pays_rappelle_ce_qui_ne_se_replique_pas():
    v = P.consolider(TROIS)
    assert v["par_pays"]["multi_pays"] is True
    sujets = {x["cle"] for x in v["par_pays"]["ce_qui_ne_se_replique_pas"]}
    assert {"reglementaire", "carbone", "eau", "devise"} <= sujets, sujets


def test_un_programme_national_ne_sert_pas_la_mise_en_garde():
    """Une mise en garde servie hors de propos apprend à ne plus les lire."""
    v = P.consolider([dict(s, pays="FR") for s in TROIS])
    assert v["par_pays"]["multi_pays"] is False
    assert v["par_pays"]["ce_qui_ne_se_replique_pas"] == []


# ── La promesse « zéro défaut » ───────────────────────────────────────────

def test_zero_defaut_n_est_pas_zero_reserve():
    """Sur un ouvrage de cette taille, zéro réserve au procès-verbal signale
    une visite trop rapide, pas un ouvrage parfait — et les défauts non
    constatés se paient en exploitation, sans recours."""
    assert "sans réserve" in P.ZERO_DEFAUT["n_est_pas"]
    z = P.consolider([{"nom": "A", "puissance_it_kw": 100}])["zero_defaut"]
    assert z["taux_de_levee"] is None
    assert "pas encore constaté" in z["lecture"]


def test_une_reserve_bloquante_l_emporte_sur_le_taux_de_levee():
    """Un taux de 95 % dont les 5 % restants portent sur une bascule de chaîne
    électrique interdit l'exploitation. Le taux seul le cache."""
    z = P.consolider(TROIS)["zero_defaut"]
    assert z["taux_de_levee"] > 0.9
    assert "bloquante" in z["lecture"]
    assert "interdit l'exploitation" in z["lecture"]


def test_sans_reserve_bloquante_la_lecture_rappelle_le_delai_de_levee():
    """Une réserve sans délai ne se lève pas, elle se discute."""
    sites = [dict(s) for s in TROIS]
    sites[2]["reserves_bloquantes"] = 0
    z = P.consolider(sites)["zero_defaut"]
    assert "délai de levée" in z["lecture"]


def test_la_promesse_dit_ce_qu_elle_coute():
    """L'annoncer sans le chiffrer revient à ne pas la faire."""
    assert P.ZERO_DEFAUT["cout"]
    assert "commissioning" in P.ZERO_DEFAUT["cout"]
    assert len(P.ZERO_DEFAUT["conditions"]) >= 5


# ── Les natures de site ───────────────────────────────────────────────────

def test_greenfield_et_brownfield_renvoient_aux_natures_de_travaux():
    """« Brownfield » recouvre DEUX métiers — l'aménagement d'une coquille et
    la reprise d'une salle en exploitation — qui n'ont ni le même risque ni le
    même prix. Le programme doit redescendre au niveau des travaux."""
    assert [n["cle"] for n in P.natures_travaux_de("greenfield")] == ["neuf"]
    assert {n["cle"] for n in P.natures_travaux_de("brownfield")} == {
        "fit_out", "retrofit"}


def test_une_nature_inconnue_ne_leve_pas():
    assert P.natures_travaux_de("champ_de_mars") == []


def test_toute_nature_de_travaux_est_rattachee_a_une_nature_de_site():
    """Une nature orpheline serait invisible depuis le pilotage de programme :
    personne ne saurait qu'elle existe."""
    import technique_dc as T
    citees = {c for v in P.NATURES_SITE.values() for c in v["travaux"]}
    assert citees == set(T.NATURES_TRAVAUX), citees ^ set(T.NATURES_TRAVAUX)


def test_un_site_sans_nature_est_signale_et_non_range_par_defaut():
    """Sans nature, on ne sait pas si le site se chiffre comme un terrain nu
    ou comme une reprise d'existant — un écart qui se découvre en exécution."""
    v = P.consolider(TROIS + [{"nom": "Sans nature", "puissance_it_kw": 100}])
    assert "_sans_nature" in v["par_nature"]
    assert "Sans nature" in v["par_nature"]["_sans_nature"]["lesquels"]


# ── Les indicateurs ───────────────────────────────────────────────────────

@pytest.mark.parametrize("cle", sorted(P.KPI))
def test_chaque_indicateur_dit_ce_qu_il_n_indique_pas(cle):
    """Chacun sera cité hors de son contexte dans une diapositive. La phrase
    qui l'empêche de dire plus qu'il ne sait voyage avec lui."""
    k = P.KPI[cle]
    assert len(k["n_indique_pas"]) > 40, cle
    assert len(k["definition"]) > 40, cle
    assert k["consolidation"] in P.CONSOLIDATIONS, cle


def test_un_indicateur_pondere_dit_par_quoi():
    """Sans quoi la page calculerait une moyenne simple — le défaut que cette
    table existe pour empêcher."""
    for cle, k in P.KPI.items():
        if k["consolidation"] == "pondere":
            assert k.get("pondere_par"), cle


def test_le_pue_de_programme_porte_son_piege():
    assert "arithmétique" in P.KPI["pue_programme"]["piege"].lower()


def test_la_derive_de_planning_se_prend_au_pire_et_non_au_milieu():
    assert P.KPI["derive_planning"]["consolidation"] == "extremum"
    assert "dernier site" in P.KPI["derive_planning"]["n_indique_pas"]


def test_le_regime_icpe_est_declare_non_consolidable_dans_la_table():
    assert P.KPI["regime_icpe"]["consolidation"] == "aucune"


# ── Les parties prenantes ─────────────────────────────────────────────────

@pytest.mark.parametrize("cle", sorted(P.PARTIES_PRENANTES))
def test_chaque_partie_prenante_porte_sa_fenetre(cle):
    """Le moment après lequel sa décision coûte cher. C'est l'information qui
    manque le plus souvent, parce qu'elle ne figure dans aucun organigramme."""
    pp = P.PARTIES_PRENANTES[cle]
    assert len(pp["fenetre"]) > 30, cle
    assert len(pp["quand_ca_coince"]) > 30, cle


def test_les_trois_directions_citees_par_la_mission_sont_couvertes():
    """IT, énergie, immobilier — celles qu'une direction de programme
    coordonne en premier."""
    assert {"it", "energie", "immobilier"} <= set(P.PARTIES_PRENANTES)


def test_l_energie_rappelle_que_le_raccordement_est_le_plus_long_delai():
    f = P.PARTIES_PRENANTES["energie"]["fenetre"].lower()
    assert "plus long" in f


# ── Les entrées et les vides ──────────────────────────────────────────────

def test_une_liste_vide_ne_conclut_rien():
    v = P.consolider([])
    assert v["vide"] is True
    assert "rien à conclure" in v["note"]


def test_une_valeur_non_finie_est_ecartee_comme_absente():
    """Un NaN qui traverse une somme la rend NaN tout entière — et un total
    NaN s'affiche « NaN » en comité, ou casse la sérialisation avant."""
    v = P.consolider([{"nom": "A", "puissance_it_kw": float("nan")},
                      {"nom": "B", "puissance_it_kw": 100}])
    assert v["capacite_engagee_kw"]["valeur"] == 100
    assert "A" in v["capacite_engagee_kw"]["sites_absents"]


def test_une_saisie_illisible_est_ecartee_comme_absente():
    v = P.consolider([{"nom": "A", "puissance_it_kw": "beaucoup"},
                      {"nom": "B", "puissance_it_kw": 100}])
    assert v["capacite_engagee_kw"]["valeur"] == 100


def test_aucun_champ_de_site_n_est_obligatoire():
    """Un formulaire qui exigerait tout ferait inventer des chiffres pour
    pouvoir cliquer."""
    for c in P.CHAMPS_SITE:
        assert not c.get("requis"), c["id"]


# ── Le contrôle de chargement se vérifie lui-même ─────────────────────────

def test_le_controle_attrape_un_indicateur_pondere_sans_poids(monkeypatch):
    faux = {k: dict(v) for k, v in P.KPI.items()}
    faux["pue_programme"].pop("pondere_par")
    monkeypatch.setattr(P, "KPI", faux)
    assert any("pondéré sans dire par quoi" in f for f in P._verifier())


def test_le_controle_attrape_une_nature_de_travaux_orpheline(monkeypatch):
    faux = {k: dict(v) for k, v in P.NATURES_SITE.items()}
    faux["brownfield"]["travaux"] = ("fit_out",)
    monkeypatch.setattr(P, "NATURES_SITE", faux)
    assert any("retrofit" in f for f in P._verifier())


def test_le_controle_attrape_une_consolidation_inconnue(monkeypatch):
    faux = {k: dict(v) for k, v in P.KPI.items()}
    faux["capex_par_kw"]["consolidation"] = "moyenne"
    monkeypatch.setattr(P, "KPI", faux)
    assert any("consolidation inconnue" in f for f in P._verifier())


# ── Le glossaire ──────────────────────────────────────────────────────────

def test_le_glossaire_couvre_les_trois_tables():
    g = P.glossaire()
    assert set(g) == {"nature_site", "kpi", "partie_prenante"}
    assert set(g["kpi"]) == set(P.KPI)
    assert set(g["partie_prenante"]) == set(P.PARTIES_PRENANTES)


def test_l_infobulle_d_un_indicateur_dit_comment_il_se_consolide():
    """C'est ce qui empêche un lecteur de moyenner ce qui se pondère."""
    aide = P.glossaire()["kpi"]["pue_programme"]["aide"]
    assert "pondère" in aide
    assert "arithmétique" in aide.lower()
