"""L'actualisation ne doit jamais inventer un taux, ni cacher qu'elle en manque.

Ce module existe parce qu'un barème de 2018 était appliqué en 2026 sans que
rien ne le date. Le risque, en le corrigeant, était d'aller trop loin dans
l'autre sens : livrer des courbes d'escalade par pays jusqu'en 2050 que
personne ne peut vérifier. Ces contrôles gardent la ligne entre les deux.
"""
import escalade_dc as e


def test_les_parts_par_defaut_font_un_tout():
    # Sinon l'actualisation porte sur plus ou moins que l'enveloppe, sans
    # que rien ne le signale.
    assert abs(sum(p["part_defaut"] for p in e.POSTES) - 1.0) < 1e-9


def test_sante_ne_releve_aucune_faute():
    assert e.sante()["fautes"] == []


def test_sans_taux_le_module_REFUSE_et_dit_quoi():
    r = e.actualiser([100.0, 100.0], 2018, 2026)
    assert r["ok"] is True
    assert r["instruit"] == 0
    assert r["couverture_pct"] == 0.0
    assert len(r["refus"]) == len(e.POSTES)
    for x in r["refus"]:
        assert x["motif"] and x["nom"]


def test_un_poste_NON_INSTRUIT_n_est_pas_escale_a_zero():
    """LE CONTRÔLE QUI COMPTE. Escalader un poste inconnu à 0 % le ferait
    apparaître stable — une stabilité que personne n'a constatée. Il doit
    être reporté à sa valeur de départ, et compté comme non instruit."""
    r = e.actualiser([100.0, 100.0], 2018, 2026)
    # Rien n'étant instruit, l'arrivée vaut exactement le départ.
    assert r["arrivee"]["meur"] == r["depart"]["meur"]
    for l in r["lignes"]:
        assert l["nature"] == "non_instruit"
        assert l["coef"] is None and l["arrivee_meur"] is None


def test_un_taux_pose_compose_bien_sur_les_annees():
    r = e.actualiser([100.0, 100.0], 2020, 2026, {"batiment": 5.0})
    ligne = [l for l in r["lignes"] if l["poste"] == "batiment"][0]
    assert abs(ligne["coef"] - 1.05 ** 6) < 1e-3
    assert ligne["nature"] == "hypothese"          # jamais « publie »


def test_la_couverture_dit_s_il_faut_croire_le_total():
    r = e.actualiser([100.0, 100.0], 2018, 2026,
                     {"batiment": 4.0, "cvc": 4.0, "electricite": 4.0})
    assert r["instruit"] == 3
    assert r["couverture_pct"] == 50.0


def test_l_annee_d_arrivee_ne_peut_preceder_le_depart():
    r = e.actualiser([100.0, 100.0], 2030, 2026, {"batiment": 4.0})
    assert r["ok"] is False


def test_une_seule_operation_est_RELEVEE_les_autres_sont_des_hypotheses():
    """Si une deuxième opération se déclarait relevée sans relevé, la
    distinction entre mesure et hypothèse — tout l'apport du module —
    disparaîtrait sans bruit."""
    releves = [o["cle"] for o in e.OPERATIONS if o["nature"] == "releve"]
    assert releves == ["neuf"]
    for o in e.OPERATIONS:
        if o["cle"] != "neuf":
            assert o["nature"] == "hypothese"
            assert o["attention"]


def test_la_reprise_alourdit_les_ETUDES_plus_que_les_honoraires_totaux():
    """C'est l'erreur que le barème de neuf fait commettre : sur une reprise,
    ce qui gonfle est la conception, pas le chantier."""
    r = e.effet_operation([100.0, 100.0], "reprise")
    assert r["coef_etudes"] > r["coef_moe"] > 1.0


def test_le_site_en_exploitation_est_le_plus_lourd_en_maitrise_d_oeuvre():
    ex = e.effet_operation([100.0, 100.0], "existant")
    nf = e.effet_operation([100.0, 100.0], "neuf")
    assert ex["coef_moe"] > nf["coef_moe"]
    assert ex["part_technique_conseillee"] > nf["part_technique_conseillee"]


def test_le_projet_2030_ne_gonfle_PAS_le_taux_mais_l_assiette():
    """Le taux d'honoraires ne change pas avec l'année de mise en service :
    c'est l'assiette qui bouge, et c'est l'escalade qui la traite. Gonfler le
    taux ferait payer deux fois la même inflation."""
    r = e.effet_operation([100.0, 100.0], "projete_2030")
    assert r["coef_moe"] == 1.0


def test_chaque_ancrage_porte_son_emetteur_et_sa_limite():
    assert e.ANCRAGES
    for a in e.ANCRAGES:
        assert a["emetteur"] and a["porte"] and a["limite"]
        assert a["nature"] == "publie"


def test_le_millesime_du_bareme_est_declare_et_motive():
    assert e.MILLESIME_BAREME == 2018
    assert "2018" in e.MOTIF_MILLESIME


def test_aucun_taux_d_escalade_par_defaut_n_est_livre():
    """Un taux par défaut serait repris tel quel, deviendrait une référence,
    et plus personne ne saurait qu'il a été posé par le module."""
    for p in e.POSTES:
        assert "taux_defaut" not in p
        assert p["nature_part"] == "hypothese"
