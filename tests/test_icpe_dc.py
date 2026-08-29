"""Le criblage ICPE — ce qu'il dit, et surtout ce qu'il refuse de dire.

CE QUI EST ÉPROUVÉ. Pas la nomenclature elle-même — un test ne connaît pas le
texte consolidé du jour, et le module ne prétend pas le remplacer. Ce qui
s'éprouve, ce sont les propriétés qui font qu'un criblage est honnête :

  · une donnée ABSENTE ne se lit jamais comme un seuil non atteint ;
  · une valeur posée EXACTEMENT sur le seuil relève du régime supérieur — c'est
    la convention de la nomenclature, et c'est le cas qui se plaide ;
  · le régime du site est le PLUS LOURD des rubriques atteintes ;
  · une valeur estimée le dit, et une conversion impossible ne se remplace
    jamais par un nombre de mémoire ;
  · les seuils ne se recouvrent pas — sans quoi une même valeur relèverait de
    deux régimes et le premier de la liste l'emporterait en silence.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import icpe_dc as I  # noqa: E402


# ── Le point qui fait la valeur du module : l'absence de donnée ────────────

def test_un_profil_vide_ne_dit_pas_que_le_site_n_est_pas_classe():
    """LE DÉFAUT QUE CE MODULE EXISTE POUR EMPÊCHER. « Aucune rubrique
    atteinte » sur un formulaire vide se lit comme « votre site n'est pas
    classé » — et c'est faux : c'est « on ne sait pas encore ». La différence
    vaut des mois d'instruction découverts trop tard."""
    c = I.cribler({})
    assert c["regime_site"] == "hors"
    assert len(c["a_verifier"]) == len(I.RUBRIQUES)
    assert not c["declenchees"]
    note = c["regime_site_note"].lower()
    assert "sans donnée" in note
    assert "on ne sait pas encore" in note


def test_une_rubrique_sans_donnee_nomme_ce_qui_manque():
    """« Donnée manquante » sans dire laquelle n'aide personne : le lecteur ne
    sait pas quel champ remplir."""
    for l in I.cribler({})["a_verifier"]:
        assert len(l["manque"]) > 20, l["numero"]


def test_un_criblage_partiel_annonce_un_plancher_et_non_un_regime():
    """Trois rubriques criblées et deux inconnues ne donnent pas LE régime du
    site : elles donnent un minimum, qui ne peut que monter."""
    c = I.cribler({"charge_frigorigene_kg": 400})
    assert c["declenchees"]
    assert c["a_verifier"]
    assert "ne peut que monter" in c["regime_site_note"]


# ── La convention des seuils ───────────────────────────────────────────────

def test_une_valeur_posee_sur_le_seuil_releve_du_regime_superieur():
    """Bornes inclusives en bas, exclusives en haut — la convention de la
    nomenclature. C'est le cas qui se plaide le plus souvent, et le trancher
    dans le mauvais sens fait annoncer une déclaration là où l'instruction
    prendra des mois."""
    seuils = [(20.0, None, "A"), (1.0, 20.0, "DC")]
    assert I._regime_pour(20.0, seuils) == "A"
    assert I._regime_pour(19.999, seuils) == "DC"
    assert I._regime_pour(1.0, seuils) == "DC"
    assert I._regime_pour(0.999, seuils) == "hors"


def test_les_seuils_de_chaque_rubrique_sont_decroissants_et_disjoints():
    """DEUX SEUILS QUI SE RECOUVRENT feraient relever une même valeur de deux
    régimes, et le premier de la liste l'emporterait sans que rien ne le dise.
    Le contrôle de chargement le refuse ; celui-ci le vérifie sur les tables
    réellement livrées."""
    for code, r in I.RUBRIQUES.items():
        for nom in ("seuils", "seuils_sans_hydrogene"):
            seuils = r.get(nom) or []
            bas = [b for b, _h, _rg in seuils]
            assert bas == sorted(bas, reverse=True), (code, nom, bas)
            for b, h, _rg in seuils:
                assert h is None or h > b, (code, nom, b, h)


def test_la_marge_dit_la_distance_au_seuil_suivant():
    """« Vous êtes en déclaration » et « vous êtes à 12 % du seuil suivant » ne
    se lisent pas pareil. La seconde dit si une décision encore ouverte peut
    faire basculer le régime."""
    m = I._marge(10.0, [(20.0, None, "A"), (1.0, 20.0, "DC")])
    assert m["prochain_seuil"] == 20.0
    assert m["regime_au_dela"] == "A"
    assert m["marge"] == 10.0
    assert abs(m["part_du_seuil"] - 0.5) < 1e-9


def test_la_marge_est_absente_au_dernier_palier():
    """Au-delà du dernier seuil, il n'y a plus de « prochain » — annoncer une
    marge nulle laisserait croire qu'on est à la limite."""
    assert I._marge(50.0, [(20.0, None, "A"), (1.0, 20.0, "DC")]) is None


# ── Le régime du site ──────────────────────────────────────────────────────

def test_le_regime_du_site_est_le_plus_lourd_des_atteints():
    """C'est lui qui commande la procédure et le délai. Prendre le plus léger,
    ou le premier trouvé, ferait annoncer une formalité là où une enquête
    publique est due."""
    p = {"groupes_puissance_thermique_mw": 2.0,      # DC
         "refroidissement": "tour_evaporative",
         "puissance_evacuee_kw": 5000.0}             # E
    c = I.cribler(p)
    assert c["regime_site"] == "E"
    assert [l["regime"] for l in c["declenchees"]][0] == "E"


def test_les_rubriques_atteintes_sont_rendues_du_plus_lourd_au_plus_leger():
    p = {"groupes_puissance_thermique_mw": 25.0,     # A
         "charge_frigorigene_kg": 500.0,             # DC
         "batteries_charge_kw": 100.0,               # D
         "batteries_hydrogene": True}
    rangs = [I._rang(l["regime"]) for l in I.cribler(p)["declenchees"]]
    assert rangs == sorted(rangs, reverse=True), rangs


# ── Les conversions, et leur honnêteté ─────────────────────────────────────

def test_la_puissance_electrique_donne_une_thermique_declaree_comme_estimee():
    """Un criblage sur une valeur convertie doit DIRE qu'elle est convertie :
    le rendement retenu est un ordre de grandeur, la puissance déclarée par le
    constructeur ne l'est pas."""
    c = I.cribler({"groupes_puissance_elec_kw": 2000.0})
    l = [x for x in c["declenchees"] if x["numero"] == "2910"][0]
    assert l["estimee"] is True
    assert "rendement retenu" in l["detail"]
    assert abs(l["valeur"] - (2.0 / I.RENDEMENT_GROUPE)) < 1e-9


def test_la_puissance_thermique_declaree_l_emporte_sur_la_conversion():
    """Dès que la vraie valeur est saisie, le repli disparaît — et le résultat
    cesse d'être annoncé comme estimé."""
    c = I.cribler({"groupes_puissance_thermique_mw": 3.0,
                   "groupes_puissance_elec_kw": 9999.0})
    l = [x for x in c["declenchees"] if x["numero"] == "2910"][0]
    assert l["valeur"] == 3.0
    assert l["estimee"] is False


def test_la_masse_volumique_vient_de_la_base_et_n_a_aucun_repli(monkeypatch):
    """JAMAIS DE REPLI CHIFFRÉ sur une grandeur qui décide d'un régime.

    LA PREMIÈRE VERSION DE CETTE RÈGLE NE VÉRIFIAIT RIEN. Elle remplaçait
    `_densite_gazole` par une fonction qui rend None, puis constatait que la
    rubrique ressortait « donnée manquante ». Elle éprouvait donc le
    comportement de `cribler` FACE À un None — pas la discipline de
    `_densite_gazole` elle-même. Un `or 845.0` glissé dans son `return`
    survivait intact : la fonction mutée ne rendait plus jamais None, et la
    règle ne s'en apercevait pas puisqu'elle ne l'appelait pas.

    Elle coupe donc la source UN CRAN PLUS BAS — au lecteur de la Base Carbone
    — et vérifie que la fonction réelle rend None. C'est là que le littéral
    devrait apparaître pour faire du mal, et c'est là qu'on regarde.
    """
    import datacenter as _dc
    monkeypatch.setattr(_dc, "_facteur_gazole", lambda: None)
    assert I._densite_gazole() is None, (
        "une masse volumique apparaît alors que la Base Carbone est muette : "
        "un littéral de repli s'est glissé dans la fonction")


def test_sans_masse_volumique_le_tonnage_n_est_pas_invente(monkeypatch):
    """Et ce que le criblage en fait : la rubrique ressort « donnée
    manquante », en nommant ce qui manque, au lieu de porter un nombre de
    mémoire — la même discipline que le calcul du scope 1."""
    import datacenter as _dc
    monkeypatch.setattr(_dc, "_facteur_gazole", lambda: None)
    c = I.cribler({"fioul_stocke_m3": 200.0})
    manque = [l for l in c["a_verifier"] if l["numero"] == "4734"]
    assert manque, c["declenchees"]
    assert "masse volumique" in manque[0]["manque"]


def test_le_tonnage_declare_court_circuite_la_conversion():
    c = I.cribler({"fioul_stocke_t": 120.0, "fioul_stocke_m3": 1.0})
    l = [x for x in c["declenchees"] if x["numero"] == "4734"][0]
    assert l["valeur"] == 120.0
    assert l["regime"] == "E"


def test_une_valeur_negative_ou_non_finie_est_ecartee_comme_absente():
    """Une puissance négative n'est pas une donnée basse : c'est une saisie
    fausse. La traiter comme une donnée produirait un régime « hors »
    rassurant et faux."""
    for mauvaise in (-5.0, float("nan"), float("inf"), "abc"):
        c = I.cribler({"groupes_puissance_thermique_mw": mauvaise})
        assert any(l["numero"] == "2910" for l in c["a_verifier"]), mauvaise


# ── Les rubriques qui dépendent d'autre chose qu'un nombre ─────────────────

def test_un_mode_sec_ecarte_la_rubrique_du_refroidissement_evaporatif():
    """Écartée AVEC SA RAISON : une rubrique écartée en silence se lit comme
    une rubrique oubliée."""
    c = I.cribler({"refroidissement": "air_dx", "puissance_it_kw": 5000})
    e = [l for l in c["ecartees"] if l["numero"] == "2921"]
    assert e, c
    assert "disperse" in e[0]["pourquoi"].lower()


def test_la_tour_evaporative_classe_le_site_quelle_que_soit_sa_taille():
    """Cette rubrique n'a pas de seuil bas : le seuil ne départage que la
    déclaration et l'enregistrement."""
    c = I.cribler({"refroidissement": "tour_evaporative",
                   "puissance_evacuee_kw": 10.0})
    l = [x for x in c["declenchees"] if x["numero"] == "2921"][0]
    assert l["regime"] == "DC"


def test_l_adiabatique_releve_du_regime_du_circuit_ferme():
    """Un dispositif adiabatique sur circuit primaire fermé reste concerné —
    le régime est plus léger, la rubrique demeure."""
    c = I.cribler({"refroidissement": "adiabatique",
                   "puissance_evacuee_kw": 9000.0})
    l = [x for x in c["declenchees"] if x["numero"] == "2921"][0]
    assert l["regime"] == "D", l


def test_le_seuil_des_batteries_depend_de_la_technologie():
    """Plomb ouvert et lithium ne sont pas pris au même seuil. Choisir le
    mauvais jeu donnerait un régime faux avec la même assurance qu'un vrai."""
    avec = I.cribler({"batteries_charge_kw": 100.0, "batteries_hydrogene": True})
    sans = I.cribler({"batteries_charge_kw": 100.0, "batteries_hydrogene": False})
    assert any(l["numero"] == "2925" for l in avec["declenchees"])
    assert not any(l["numero"] == "2925" for l in sans["declenchees"])


def test_sans_reponse_sur_l_hydrogene_le_cas_le_plus_contraignant_s_applique():
    """Une question non posée ne vaut pas « non ». Retenir le seuil permissif
    par défaut ferait manquer la rubrique la plus souvent oubliée d'un centre
    de données."""
    c = I.cribler({"batteries_charge_kw": 100.0})
    assert any(l["numero"] == "2925" for l in c["declenchees"])


# ── Ce que le criblage rend à la page ──────────────────────────────────────

def test_la_liste_deroulante_range_l_action_avant_la_nomenclature():
    """Ce qui bloque d'abord, ce qui manque ensuite, ce qui est écarté en
    dernier. L'ordre de la nomenclature n'aide personne."""
    p = {"groupes_puissance_thermique_mw": 25.0, "refroidissement": "air_dx",
         "puissance_it_kw": 100}
    r = I.rubriques_du_projet(p)["rubriques"]
    etats = [x["etat"] for x in r]
    ordre = {"declenchee": 0, "a_verifier": 1, "ecartee": 2}
    assert [ordre[e] for e in etats] == sorted(ordre[e] for e in etats), etats


def test_chaque_entree_de_la_liste_porte_de_quoi_s_afficher():
    """Une page qui recompose un libellé recompose bientôt autre chose que ce
    qui a été criblé."""
    for x in I.rubriques_du_projet({"charge_frigorigene_kg": 500})["rubriques"]:
        assert x["libelle"] and x["badge"] and x["resume"], x


def test_toute_rubrique_du_projet_est_rendue_une_fois_et_une_seule():
    """Une rubrique qui apparaîtrait deux fois — ou zéro — dans la liste
    déroulante ferait douter du criblage entier."""
    r = I.rubriques_du_projet({"charge_frigorigene_kg": 500})["rubriques"]
    codes = [x["code"] for x in r]
    assert sorted(codes) == sorted(I.RUBRIQUES), codes


# ── Ce que le régime change pour la mission ────────────────────────────────

@pytest.mark.parametrize("regime", sorted(I.REGIMES))
def test_chaque_regime_dit_ce_qu_il_ajoute_a_la_mission(regime):
    """Le criblage dit le régime ; il ne dit pas quoi faire. C'est pourtant la
    seule chose qui intéresse un maître d'ouvrage en première réunion."""
    c = I.consequences_mission(regime)
    assert c["actions"], regime
    assert c["reserve"]


def test_le_regime_hors_demande_quand_meme_de_conserver_la_note():
    """C'est elle qu'on demandera à la première extension — et l'absence de
    trace fait alors refaire le criblage sur un projet dont les hypothèses
    d'origine sont perdues."""
    actions = " ".join(I.consequences_mission("hors")["actions"]).lower()
    assert "conserver" in actions or "note" in actions


def test_l_autorisation_place_les_etudes_avant_la_conception_detaillee():
    """Les campagnes de mesure se déroulent sur un cycle biologique : les
    lancer après la conception détaillée décale tout le projet."""
    actions = " ".join(I.consequences_mission("A")["actions"]).lower()
    assert "avant" in actions
    assert "enquête publique" in actions


# ── Les réserves, qui font tenir tout le reste ─────────────────────────────

def test_le_criblage_dit_partout_qu_il_ne_classe_pas():
    c = I.cribler({"charge_frigorigene_kg": 500})
    assert "ne classe pas" in c["reserve"].lower() or "criblage" in c["reserve"].lower()
    assert "préfet" in c["reserve"]
    assert "décret" in c["reserve"]


def test_les_rubriques_connexes_sont_nommees_plutot_que_tues():
    """Une rubrique absente d'une liste passe pour inexistante. On préfère la
    nommer sans seuil que la taire."""
    c = I.cribler({})
    assert "ammoniac" in c["connexes"].lower()
    assert "même site" in c["connexes"]


def test_chaque_rubrique_renvoie_au_texte_qui_la_porte():
    for l in I.rubriques_du_projet({})["rubriques"]:
        assert "R. 511-9" in l["ligne"]["texte"]


# ── Le contrôle de chargement se vérifie lui-même ──────────────────────────

def test_le_controle_attrape_des_seuils_qui_se_recouvrent(monkeypatch):
    faux = {k: dict(v) for k, v in I.RUBRIQUES.items()}
    faux["1185"]["seuils"] = [(300.0, None, "DC"), (500.0, None, "A")]
    monkeypatch.setattr(I, "RUBRIQUES", faux)
    fautes = I._verifier()
    assert any("décroissants" in f for f in fautes), fautes


def test_le_controle_attrape_une_rubrique_sans_criblage(monkeypatch):
    """Une rubrique déclarée sans fonction pour la mesurer ne serait jamais
    criblée, et son absence des résultats passerait pour « non atteinte »."""
    faux = {k: dict(v) for k, v in I.RUBRIQUES.items()}
    faux["9999"] = dict(faux["1185"], numero="9999")
    monkeypatch.setattr(I, "RUBRIQUES", faux)
    fautes = I._verifier()
    assert any("9999" in f for f in fautes), fautes


def test_le_controle_attrape_un_regime_sans_consequence_de_mission(monkeypatch):
    faux = {k: v for k, v in I.MISSION_PAR_REGIME.items() if k != "E"}
    monkeypatch.setattr(I, "MISSION_PAR_REGIME", faux)
    fautes = I._verifier()
    assert any("E" in f and "mission" in f for f in fautes), fautes


# ── Le glossaire ───────────────────────────────────────────────────────────

def test_le_glossaire_couvre_les_rubriques_et_les_regimes():
    g = I.glossaire()
    assert set(g["rubrique_icpe"]) == set(I.RUBRIQUES)
    assert set(g["regime_icpe"]) == set(I.REGIMES)
    for famille in g.values():
        for cle, e in famille.items():
            assert len(e["aide"]) > 60, (cle, len(e["aide"]))
