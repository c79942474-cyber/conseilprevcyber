"""Le raccordement effaçable — ce que coûte le délai qu'il fait gagner.

CE QUI EST ÉPROUVÉ. Les propriétés qui séparent un chiffrage opposable d'une
opinion sur le non ferme :

  · le calcul non servi croît avec la fréquence et la profondeur de
    l'effacement, et tombe à zéro quand la puissance ferme sur site couvre le
    déficit ;
  · LE REPORT EST PLAFONNÉ PAR LE CREUX — à taux de charge élevé, ajouter de
    la flexibilité cesse de réduire quoi que ce soit. C'est la propriété que
    ce module existe pour montrer, et la seule qu'aucune synthèse ne donne ;
  · l'élasticité marge se DÉDUIT de la marge et n'est jamais une constante ;
  · rien ne se calcule sur une valeur par défaut : une grandeur absente rend
    un résultat « incomplet » qui la nomme, une saisie hors bornes est
    refusée au lieu d'être ramenée dans les bornes ;
  · une source intermittente ne compte pas comme ferme ;
  · la production sur site fait apparaître le régime d'autorisation dans le
    criblage réglementaire, et un volume au-delà du criblage ressort comme une
    sortie de périmètre déclarée, pas comme un régime ;
  · un groupe de classe secours n'apporte aucun kilowatt qualifiant, quel que
    soit le rôle qu'on lui donne côté effacement ;
  · aucun repère de marché n'entre dans un calcul.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import reseau_dc as R  # noqa: E402


def profil(**kw):
    """Un profil complet, que chaque essai déforme sur un seul axe."""
    base = {"puissance_it_kw": 100000.0, "taux_charge": 0.65,
            "part_non_ferme": 0.5, "frequence_effacement": 0.30,
            "part_reportable": 0.0, "btm_ferme_kw": 0.0}
    base.update(kw)
    return base


# ── 1. Le calcul, et le sens de ses variations ─────────────────────────────

def test_le_non_servi_croit_avec_la_frequence():
    """Une fréquence d'effacement plus élevée ne peut pas réduire la perte."""
    parts = [R.calcul_non_servi(profil(frequence_effacement=f))["part_non_servie"]
             for f in (0.05, 0.15, 0.30, 0.50)]
    assert parts == sorted(parts)
    assert parts[0] < parts[-1]


def test_le_non_servi_croit_avec_la_profondeur():
    parts = [R.calcul_non_servi(
                 profil(profondeur_effacement=d))["part_non_servie"]
             for d in (0.2, 0.5, 0.8, 1.0)]
    assert parts == sorted(parts)


def test_la_puissance_ferme_sur_site_ramene_le_non_servi_a_zero():
    """Le déficit horaire est de 15 % de la plaque : 15 MW le couvrent."""
    r = R.calcul_non_servi(profil(btm_ferme_kw=15000.0))
    assert r["termes"]["deficit_horaire_kw"] == 0
    assert r["part_non_servie"] == 0
    partiel = R.calcul_non_servi(profil(btm_ferme_kw=10000.0))
    assert 0 < partiel["part_non_servie"] < R.calcul_non_servi(
        profil())["part_non_servie"]


def test_les_sources_que_la_meteo_commande_ne_sont_jamais_fermes():
    """LA FAUTE DE DIMENSIONNEMENT LA PLUS COÛTEUSE DU SUJET. L'effacement est
    appelé quand le réseau est tendu — c'est-à-dire souvent sans vent ni
    soleil. Le soleil et le vent ne répondent pas à un appel de gestionnaire
    de réseau : leur non-fermeté est un fait physique, pas une convention de
    table, et elle doit donc être éprouvée SOURCE PAR SOURCE.

    Une règle qui se contenterait de vérifier qu'il reste « au moins une »
    source intermittente survivrait à ce que le photovoltaïque soit déclaré
    ferme — ce qui est exactement la faute à empêcher."""
    meteo = ("photovoltaique", "eolien")
    for cle in meteo:
        assert R.BTM[cle]["ferme"] is False, cle
        assert "effacement" in R.BTM[cle]["attention"].lower(), cle
    # Et réciproquement : tout ce qui est déclaré non ferme est bien une
    # source que la météo commande. Déclarer un moteur « non ferme » le
    # sortirait à tort du dimensionnement.
    assert {k for k, v in R.BTM.items() if v["ferme"] is False} == set(meteo)


# ── 2. Le report, et son plafond — la propriété centrale ───────────────────

def test_le_report_reduit_le_non_servi_quand_le_creux_le_permet():
    parts = [R.calcul_non_servi(profil(part_reportable=x))["part_non_servie"]
             for x in (0.0, 0.25, 0.5, 0.75)]
    assert parts == sorted(parts, reverse=True)
    assert parts[-1] < parts[0]


def test_le_report_est_plafonne_par_le_creux_a_charge_elevee():
    """LA PROPRIÉTÉ QUE CE MODULE EXISTE POUR MONTRER. Le travail reporté doit
    s'exécuter plus tard, sur des heures qui ne sont pas déjà prises. À taux
    de charge élevé ce creux se referme : au-delà d'un certain point, ajouter
    de la flexibilité ne change plus RIEN — et la seule chose qui agisse
    encore est de la puissance ferme.

    C'est ce plafond qui explique la borne haute que la littérature de marché
    constate sans l'expliquer. L'éprouver sur l'ÉGALITÉ de deux résultats, et
    non sur une phrase du résultat, est ce qui distingue cette règle d'un
    contrôle de rédaction."""
    haute = dict(taux_charge=0.90)
    a = R.calcul_non_servi(profil(part_reportable=0.75, **haute))
    b = R.calcul_non_servi(profil(part_reportable=1.00, **haute))
    assert a["plafonne_par_le_creux"] and b["plafonne_par_le_creux"]
    assert a["part_non_servie"] == b["part_non_servie"] > 0
    # Et à charge basse, le même écart de flexibilité agit encore.
    basse = dict(taux_charge=0.55)
    c = R.calcul_non_servi(profil(part_reportable=0.75, **basse))
    d = R.calcul_non_servi(profil(part_reportable=1.00, **basse))
    assert not c["plafonne_par_le_creux"]
    assert d["part_non_servie"] < c["part_non_servie"]


def test_le_creux_se_referme_quand_la_charge_monte():
    creux = [R.calcul_non_servi(profil(taux_charge=u))["termes"]
             ["creux_de_rattrapage_kwh_an"] for u in (0.5, 0.7, 0.9)]
    assert creux == sorted(creux, reverse=True)


def test_la_ponderation_par_les_classes_de_charge():
    """Un parc d'entraînement est reportable, un parc interactif ne l'est pas.
    La moyenne pondérée doit les séparer."""
    lourd = R.part_reportable_du_profil({"entrainement": 1.0})
    leger = R.part_reportable_du_profil({"interactif": 1.0})
    mixte = R.part_reportable_du_profil({"entrainement": 0.5, "interactif": 0.5})
    assert leger["part_reportable"] == 0.0
    assert lourd["part_reportable"] > mixte["part_reportable"] > 0


def test_une_repartition_qui_ne_somme_pas_a_un_le_dit():
    """Ce n'est pas une erreur bénigne : la part manquante n'est pas « non
    reportable », elle est NON CLASSÉE, et la moyenne la suppose semblable au
    classé. Le résultat doit porter l'alerte, sinon 60 % du parc décide pour
    100 %."""
    r = R.part_reportable_du_profil({"entrainement": 0.6})
    assert r["nature"] == "calcule"
    assert r["somme_declaree"] == pytest.approx(0.6)
    assert r.get("alerte")


def test_une_classe_de_charge_inconnue_est_refusee():
    r = R.part_reportable_du_profil({"minage": 1.0})
    assert r["nature"] == "refus" and r["erreur"] == "classe_inconnue"


# ── 3. L'effet marge : une déduction, jamais une constante ─────────────────

def test_l_elasticite_est_l_inverse_de_la_marge():
    """AUCUNE CONSTANTE D'ÉLASTICITÉ N'EXISTE DANS CE MODULE. Une constante
    recopiée d'une étude serait celle de la structure de coûts de cette
    étude, appliquée en silence à un projet qui n'a pas la même."""
    for m in (0.30, 0.50, 0.55, 0.67, 0.80):
        r = R.effet_sur_la_marge(0.05, m)
        assert r["elasticite"] == pytest.approx(1.0 / m)
    # Deux marges différentes ne peuvent pas rendre la même élasticité.
    a = R.effet_sur_la_marge(0.05, 0.40)["elasticite"]
    b = R.effet_sur_la_marge(0.05, 0.60)["elasticite"]
    assert a != b


def test_la_perte_de_resultat_suit_la_part_non_servie():
    r = R.effet_sur_la_marge(0.05, 0.50)
    assert r["perte_de_resultat_relative"] == pytest.approx(0.10)


def test_une_marge_absente_ou_impossible_est_refusee():
    """PAS DE VALEUR PAR DÉFAUT. L'élasticité dépend entièrement de la marge ;
    en supposer une ferait passer la structure de coûts d'un autre projet
    pour celle-ci, sous couvert d'un chiffre calculé."""
    for m in (None, "", 0, 1, 1.5, -0.2, "beaucoup"):
        r = R.effet_sur_la_marge(0.05, m)
        assert r["nature"] == "refus", m
        assert r["erreur"] == "marge_illisible"


# ── 4. Rien ne se devine ───────────────────────────────────────────────────

@pytest.mark.parametrize("absent", [
    "puissance_it_kw", "taux_charge", "part_non_ferme", "frequence_effacement"])
def test_une_grandeur_absente_rend_un_resultat_incomplet_qui_la_nomme(absent):
    p = profil()
    p.pop(absent)
    r = R.calcul_non_servi(p)
    assert r["nature"] == "incomplet"
    assert r["manques"], absent
    assert "part_non_servie" not in r


def test_une_part_hors_bornes_est_refusee_et_non_ramenee():
    """Une part saisie « 30 » pour trente pour cent est une faute fréquente.
    La ramener à 1 rendrait un résultat plausible et faux."""
    r = R.calcul_non_servi(profil(profondeur_effacement=30))
    assert r["nature"] == "refus" and r["erreur"] == "profondeur_illisible"
    # Et une part non ferme hors bornes fait ressortir la grandeur comme
    # ABSENTE, jamais comme bornée à un.
    r2 = R.calcul_non_servi(profil(part_non_ferme=50))
    assert r2["nature"] == "incomplet"


def test_la_profondeur_supposee_est_declaree():
    """Une profondeur totale est le cas défavorable. La supposer sans le dire
    ferait passer une hypothèse pour une donnée."""
    r = R.calcul_non_servi(profil())
    assert r["hypotheses"]["profondeur_effacement"] == 1.0
    assert r["hypotheses"]["profondeur_supposee"] is True
    assert r.get("alerte_profondeur")
    explicite = R.calcul_non_servi(profil(profondeur_effacement=1.0))
    assert explicite["hypotheses"]["profondeur_supposee"] is False
    assert not explicite.get("alerte_profondeur")


def test_aucun_champ_ne_porte_de_valeur_par_defaut():
    for c in R.CHAMPS:
        assert "defaut" not in c, c["id"]


def test_les_termes_du_calcul_sont_tous_rendus():
    """Un chiffre dont on ne voit pas la décomposition ne se discute ni avec
    un gestionnaire de réseau ni avec un client : il se croit ou il se
    rejette."""
    r = R.calcul_non_servi(profil(part_reportable=0.4))
    for t in ("puissance_tenue_en_effacement_kw", "puissance_appelee_kw",
              "deficit_horaire_kw", "non_servi_brut_kwh_an",
              "creux_de_rattrapage_kwh_an", "reporte_kwh_an",
              "non_servi_net_kwh_an", "demande_annuelle_kwh"):
        assert t in r["termes"], t
    assert r["formules"]
    # Les termes s'enchaînent réellement : le net est le brut moins le reporté.
    assert (r["termes"]["non_servi_net_kwh_an"]
            == pytest.approx(r["termes"]["non_servi_brut_kwh_an"]
                             - r["termes"]["reporte_kwh_an"]))


# ── 5. Le pont vers le criblage réglementaire et la disponibilité ──────────

def test_la_production_sur_site_fait_basculer_le_regime():
    """LE RÉSULTAT LE PLUS UTILE DU MODULE : éviter une file d'attente de
    raccordement en installant de la production, c'est remplacer une attente
    par une procédure d'autorisation. Éprouvé sur le RÉGIME RENDU par le
    criblage, jamais sur une phrase du résultat."""
    petit = {"groupes_puissance_elec_kw": 2000.0}
    grand = dict(petit, btm_puissance_elec_kw=60000.0,
                 btm_combustible="gaz", btm_heures_an=876.0)
    c = R.consequences_btm(grand)
    assert c["icpe"]["regime_sans_production"] == "DC"
    assert c["icpe"]["regime_avec_production"] == "A"
    assert c["icpe"]["bascule"] is True
    assert c["alertes"]
    # Une production marginale ne fait pas basculer : la règle ne crie pas
    # toujours, sinon elle ne dirait rien.
    calme = R.consequences_btm(dict(petit, btm_puissance_elec_kw=500.0,
                                    btm_combustible="gaz", btm_heures_an=10.0))
    assert calme["icpe"]["bascule"] is False


def test_les_heures_de_fonctionnement_sont_exigees():
    """L'ALLÈGEMENT D'ÉMISSION TOMBE AVEC LES HEURES. La nomenclature
    reconnaît des exigences réduites aux moteurs de SECOURS parce qu'ils
    tournent très peu ; une machine appelée pour tenir un effacement
    fonctionne, elle ne secourt pas. Les heures ne sont donc pas un détail de
    second ordre : elles décident du régime d'émission applicable ET du volume
    de combustible. Le module doit les RÉCLAMER quand elles manquent, et le
    résultat doit porter le point là où il se lit."""
    sans = R.consequences_btm({"groupes_puissance_elec_kw": 2000.0,
                               "btm_puissance_elec_kw": 20000.0,
                               "btm_combustible": "gaz"})
    assert any("heures" in m for m in sans["manques"])
    assert sans["allegement_heures"]
    avec = R.consequences_btm({"groupes_puissance_elec_kw": 2000.0,
                               "btm_puissance_elec_kw": 20000.0,
                               "btm_combustible": "gaz",
                               "btm_heures_an": 876.0})
    assert not any("heures" in m for m in avec["manques"])


def test_le_cumul_compte_et_non_la_seule_production():
    """C'est la puissance TOTALE qui classe le site. Cribler la production
    seule rendrait un régime plus favorable que la réalité.

    ÉPROUVÉ SUR LE RÉGIME CRIBLÉ, PAS SUR LE NOMBRE AFFICHÉ. Le cumul est
    aussi reporté dans le résultat pour la lecture ; si la règle ne regardait
    que ce nombre-là, un criblage conduit sur la seule production tandis que
    l'affichage montre le cumul passerait inaperçu — et c'est précisément la
    forme que prend ce genre de défaut. Ici les deux dosages sont choisis de
    part et d'autre d'un seuil : la production seule reste en déclaration, le
    cumul bascule en autorisation."""
    entree = {"groupes_puissance_elec_kw": 4000.0,
              "btm_puissance_elec_kw": 6000.0,
              "btm_combustible": "gaz", "btm_heures_an": 500.0}
    c = R.consequences_btm(entree)
    assert c["icpe"]["puissance_elec_cumulee_kw"] == 10000.0
    assert c["icpe"]["regime_avec_production"] == "A"
    # La production seule, criblée à part, ne donnerait PAS ce régime.
    seule = R.consequences_btm({"btm_puissance_elec_kw": 6000.0,
                                "btm_combustible": "gaz",
                                "btm_heures_an": 500.0})
    assert seule["icpe"]["regime_avec_production"] == "DC"


def test_le_volume_de_gazole_sort_du_perimetre_crible():
    """Quelques centaines d'heures de production demandent un stockage sans
    commune mesure avec les douze heures de secours. Au-delà du plus haut
    seuil crible, le module doit DÉCLARER la sortie de périmètre — un régime
    rendu là serait faussement rassurant."""
    c = R.consequences_btm({"btm_puissance_elec_kw": 60000.0,
                            "btm_combustible": "gazole",
                            "btm_heures_an": 876.0})
    comb = c["combustible"]
    assert comb["voie"] == "gazole"
    assert comb["volume_m3"] > comb["reserve_tier_m3"] * 50
    assert comb["tonnes"] > comb["plafond_criblage_t"]
    assert comb.get("hors_perimetre")
    # Un stockage modeste reste dans le périmètre et n'alerte pas.
    petit = R.consequences_btm({"btm_puissance_elec_kw": 1000.0,
                                "btm_combustible": "gazole",
                                "btm_heures_an": 12.0})
    assert not petit["combustible"].get("hors_perimetre")


def test_la_voie_gaz_deplace_la_contrainte_sur_un_second_reseau():
    c = R.consequences_btm({"btm_puissance_elec_kw": 60000.0,
                            "btm_combustible": "gaz", "btm_heures_an": 876.0})
    assert c["combustible"]["voie"] == "gaz"
    assert c["combustible"]["a_obtenir"]
    assert "gaz" in R.BTM["raccordement_gaz"]["nom"].lower()


def test_un_groupe_de_secours_n_apporte_aucun_kilowatt_qualifiant():
    """Tenir un effacement n'est pas secourir. La classe de service décide, et
    le rôle qu'on donne par ailleurs à la machine n'y change rien."""
    c = R.consequences_btm({"btm_puissance_elec_kw": 40000.0,
                            "btm_combustible": "gaz", "btm_heures_an": 876.0,
                            "btm_classe_iso": "secours"})
    q = c["duty"]["qualifiante"]
    assert q["qualifiante_kw"] == 0
    assert q["eligible_iii_iv"] is False
    # Une classe intermédiaire est déclassée, pas écartée.
    c2 = R.consequences_btm({"btm_puissance_elec_kw": 40000.0,
                             "btm_combustible": "gaz", "btm_heures_an": 876.0,
                             "btm_classe_iso": "prime"})
    q2 = c2["duty"]["qualifiante"]
    assert 0 < q2["qualifiante_kw"] < 40000.0


def test_la_classe_absente_est_nommee_et_non_supposee():
    c = R.consequences_btm({"btm_puissance_elec_kw": 5000.0,
                            "btm_combustible": "gaz", "btm_heures_an": 100.0})
    assert c["duty"]["manque"]
    assert c["duty"]["classes"]
    assert "qualifiante" not in c["duty"]


def test_sans_production_declaree_le_resultat_est_incomplet():
    c = R.consequences_btm({})
    assert c["nature"] == "incomplet" and c["manques"]


# ── 6. Les repères publiés restent dehors ──────────────────────────────────

def test_aucun_repere_de_marche_n_entre_dans_un_calcul():
    """LA RÈGLE DE L'ÉTAT DE L'ART S'APPLIQUE ICI. Un chiffre publié par un
    tiers qui entrerait dans une formule y entrerait sans que personne ne le
    voie. Le repère s'AFFICHE à côté du résultat, avec son auteur ; il ne le
    produit pas.

    Éprouvé sur la propriété : le résultat du calcul ne change pas quand
    l'état de l'art est vidé de ses faits."""
    import etat_art
    attendu = R.calcul_non_servi(profil())["part_non_servie"]
    faits = etat_art.FAITS[:]
    try:
        etat_art.FAITS[:] = []
        assert R.calcul_non_servi(profil())["part_non_servie"] == attendu
    finally:
        etat_art.FAITS[:] = faits


def test_chaque_mode_porte_son_repere_avec_son_auteur():
    for m in R.modes():
        rep = m.get("repere")
        assert rep, m["cle"]
        assert rep["editeur"], m["cle"]
        assert rep["nature"], m["cle"]
        assert rep["n_entre_pas_dans_le_calcul"] is True


def test_un_repere_inconnu_est_une_faute_de_chargement():
    """Un mode qui citerait un repère absent s'afficherait sans ordre de
    grandeur, en silence, et le lecteur conclurait qu'il n'y en a pas."""
    sauve = R.MODES_RACCORDEMENT["ferme"]["repere_delai"]
    try:
        R.MODES_RACCORDEMENT["ferme"]["repere_delai"] = "inexistant"
        assert any("repère de marché inconnu" in f for f in R._verifier())
    finally:
        R.MODES_RACCORDEMENT["ferme"]["repere_delai"] = sauve
    assert not R._verifier()


def test_une_rubrique_inconnue_citee_par_un_actif_est_une_faute():
    sauve = R.BTM["turbine_gaz"]["icpe"]
    try:
        R.BTM["turbine_gaz"]["icpe"] = "9999"
        assert any("rubrique inconnue" in f for f in R._verifier())
    finally:
        R.BTM["turbine_gaz"]["icpe"] = sauve
    assert not R._verifier()


# ── 7. L'étude complète, et ce qu'elle refuse ─────────────────────────────

def test_l_etude_presente_les_resultats_ensemble():
    e = R.etudier(profil(mode_raccordement="non_ferme",
                         marge_operationnelle=0.55,
                         btm_puissance_elec_kw=20000.0,
                         btm_combustible="gaz", btm_heures_an=876.0,
                         btm_classe_iso="continu"))
    assert e["mode"]["cle"] == "non_ferme"
    assert e["non_servi"]["nature"] == "calcule"
    assert e["marge"]["nature"] == "calcule"
    assert e["production_sur_site"]["icpe"]


def test_un_mode_inconnu_est_refuse():
    e = R.etudier(profil(mode_raccordement="gratuit"))
    assert e["nature"] == "refus" and e["erreur"] == "mode_inconnu"
    assert e["modes"]


def test_la_reserve_voyage_avec_chaque_resultat():
    """Un résultat détaché de sa réserve devient une offre de raccordement."""
    assert R.calcul_non_servi(profil())["reserve"] == R.RESERVE
    assert R.calcul_non_servi({})["reserve"] == R.RESERVE
    assert R.effet_sur_la_marge(0.05, 0.5)["reserve"] == R.RESERVE
    assert R.etudier(profil())["reserve"] == R.RESERVE
    assert R.consequences_btm({"btm_puissance_elec_kw": 100.0})["reserve"] \
        == R.RESERVE


# ── 8. Les tables tiennent ────────────────────────────────────────────────

def test_le_module_se_charge_sans_faute_de_structure():
    assert R._verifier() == []


def test_les_leviers_portent_tous_leur_contrepartie():
    """C'est la contrepartie qui fait la valeur, pas le levier : un levier
    sans elle est un argument commercial."""
    assert len(R.LEVIERS) >= 5
    for k, v in R.LEVIERS.items():
        assert v["contrepartie"].strip(), k


def test_la_taxonomie_ordonne_les_charges_du_plus_au_moins_reportable():
    ordre = ["entrainement", "lots", "agentique", "interactif"]
    parts = [R.CHARGES[c]["part_reportable"] for c in ordre]
    assert parts == sorted(parts, reverse=True)
    assert R.CHARGES["interactif"]["part_reportable"] == 0.0


def test_les_familles_d_infobulles_couvrent_les_tables():
    g = R.glossaire()
    assert set(g["mode_raccordement"]) == set(R.MODES_RACCORDEMENT)
    assert set(g["levier_reseau"]) == set(R.LEVIERS)
    assert set(g["charge_flex"]) == set(R.CHARGES)
    assert set(g["btm"]) == set(R.BTM)
