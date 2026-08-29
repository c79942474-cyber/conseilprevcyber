"""La qualification Tier — le plus bas, jamais la moyenne.

CE QUI EST ÉPROUVÉ. Les propriétés qui séparent une qualification honnête d'une
étiquette qu'on s'attribue :

  · le niveau d'un site est le MINIMUM de ses sous-systèmes — pas leur moyenne,
    et il n'existe aucun niveau fractionnaire ;
  · un sous-système non noté n'est pas conforme : il est INCONNU, et le
    résultat devient un plafond qui ne peut que descendre ;
  · le sous-système limitant est NOMMÉ — « votre site est de niveau I » n'aide
    personne, « parce que la distribution mécanique l'est » se traite ;
  · les exigences ne régressent jamais d'un niveau au suivant ;
  · la classe de service d'un groupe décide de ce qui compte, et une
    certification constructeur l'emporte sur le déclassement par défaut ;
  · rien ici ne décerne un niveau, et la réserve voyage avec chaque résultat.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import tier_dc as T  # noqa: E402


TOUT_IV = {c: "IV" for c in T.SOUS_SYSTEMES if c != "eau_appoint"}


# ── La règle qui fait tout le module ──────────────────────────────────────

def test_le_niveau_du_site_est_le_plus_bas_de_ses_sous_systemes():
    """LE DÉFAUT QUE CE MODULE EXISTE POUR EMPÊCHER. On juge un site sur son
    lot le plus soigné — en général l'électricité, parce que c'est là que le
    budget est passé. Une chaîne électrique tolérante à la panne desservie par
    une distribution mécanique à chemin unique fait un site de niveau I."""
    ss = dict(TOUT_IV, distribution_meca="I")
    q = T.qualifier(ss)
    assert q["niveau"] == "I", q["niveau"]
    assert [l["cle"] for l in q["limitants"]] == ["distribution_meca"]


def test_le_niveau_n_est_jamais_la_moyenne():
    """La moyenne est ce qu'on calcule spontanément, et elle est fausse. Sept
    sous-systèmes au niveau IV et un au niveau I ne font pas « presque IV »."""
    q = T.qualifier(dict(TOUT_IV, distribution_meca="I"))
    assert q["niveau"] != "III"
    assert q["niveau"] == "I"


def test_il_n_existe_aucun_niveau_fractionnaire():
    """Le rendu ne peut porter qu'un des quatre codes — jamais un intermédiaire
    calculé."""
    for ss in ({"prod_elec": "I", "prod_froid": "IV"},
               {"prod_elec": "II", "prod_froid": "III"},
               dict(TOUT_IV, telecom="II")):
        q = T.qualifier(ss)
        assert q["niveau"] in T.ORDRE, q["niveau"]


def test_plusieurs_sous_systemes_au_meme_plancher_sont_tous_nommes():
    """Un seul limitant affiché ferait corriger un maillon et découvrir le
    second au tour suivant."""
    ss = dict(TOUT_IV, distribution_meca="II", telecom="II")
    q = T.qualifier(ss)
    assert q["niveau"] == "II"
    assert {l["cle"] for l in q["limitants"]} == {"distribution_meca", "telecom"}


def test_le_sous_systeme_limitant_est_nomme_dans_la_lecture():
    """« Votre site est de niveau I » n'aide personne."""
    q = T.qualifier(dict(TOUT_IV, distribution_meca="I"))
    assert T.SOUS_SYSTEMES["distribution_meca"]["nom"] in q["lecture"]


def test_la_lecture_dit_que_l_avance_des_autres_ne_remonte_rien():
    """C'est l'argument de chiffrage : porter les huit autres plus haut est
    payé sans être obtenu."""
    q = T.qualifier(dict(TOUT_IV, distribution_meca="I"))
    assert "ne remonte pas" in q["lecture"]


# ── Ce qui n'est pas noté n'est pas conforme ──────────────────────────────

def test_un_sous_systeme_non_note_rend_le_resultat_plafond():
    """Il peut être plus bas que tous les autres : le niveau rendu ne peut que
    descendre. L'annoncer comme un verdict ferait promettre au client un
    niveau qui n'est pas établi."""
    q = T.qualifier({"prod_elec": "IV", "backbone_elec": "IV"})
    assert q["plafond"] is True
    assert "PLAFOND" in q["lecture"]
    assert len(q["non_evalues"]) >= 5


def test_un_relevé_complet_n_est_pas_un_plafond():
    q = T.qualifier(TOUT_IV)
    assert q["plafond"] is False
    assert q["non_evalues"] == []


def test_un_sous_systeme_non_note_le_dit_au_lieu_de_paraitre_conforme():
    q = T.qualifier({"prod_elec": "IV"})
    par_cle = {s["cle"]: s for s in q["sous_systemes"]}
    assert par_cle["prod_froid"]["etat"] == "non_evalue"
    assert "conforme" in par_cle["prod_froid"]["pourquoi"]


def test_aucune_note_ne_conclut_rien():
    """Sans aucune note, il n'y a rien à minorer — et le dire vaut mieux qu'un
    niveau I par défaut, qui se lirait comme un constat."""
    q = T.qualifier({})
    assert q["niveau"] is None
    assert q["evalue"] is False
    assert "rien à minorer" in q["pourquoi"]


def test_une_note_inconnue_est_signalee_et_traitee_comme_absente():
    """« Tier 3 » au lieu de « III » ne doit ni compter, ni disparaître."""
    q = T.qualifier({"prod_elec": "3", "prod_froid": "IV"})
    assert q["inconnus"], q
    assert q["inconnus"][0]["sous_systeme"] == "prod_elec"
    assert "prod_elec" in q["non_evalues"]


# ── L'eau d'appoint, hors périmètre sur un site sec ───────────────────────

def test_l_eau_d_appoint_n_est_notee_que_sur_un_site_evaporatif():
    """Sur un site sec, l'exiger ferait apparaître un sous-système
    perpétuellement non évalué, donc un plafond perpétuel."""
    sec = T.qualifier(TOUT_IV, evaporatif=False)
    assert sec["plafond"] is False
    par_cle = {s["cle"]: s for s in sec["sous_systemes"]}
    assert par_cle["eau_appoint"]["etat"] == "hors_perimetre"


def test_sur_un_site_evaporatif_l_eau_d_appoint_compte():
    hum = T.qualifier(TOUT_IV, evaporatif=True)
    assert hum["plafond"] is True
    assert "eau_appoint" in hum["non_evalues"]


def test_un_sous_systeme_hors_perimetre_dit_pourquoi():
    """Une absence silencieuse se lirait comme un oubli."""
    par_cle = {s["cle"]: s for s in T.qualifier(TOUT_IV)["sous_systemes"]}
    assert par_cle["eau_appoint"]["pourquoi"]


# ── L'écart au niveau visé ────────────────────────────────────────────────

def test_l_ecart_nomme_les_sous_systemes_qui_manquent():
    """Savoir qu'on est au niveau I ne dit pas quoi faire. Savoir lesquels des
    neuf manquent se traduit en plan d'action et en chiffrage."""
    ss = dict(TOUT_IV, distribution_meca="I", telecom="II")
    e = T.ecart_au_vise(ss, "III")
    manquants = {m["cle"] for m in e["manquants"]}
    assert manquants == {"distribution_meca", "telecom"}
    assert e["conforme"] is False


def test_un_ecart_nul_reste_a_demontrer():
    """Le niveau se constate par des essais dont l'issue est observable. Tenir
    les exigences ne suffit pas : il faut le prouver."""
    e = T.ecart_au_vise(TOUT_IV, "III")
    assert e["manquants"] == []
    assert e["conforme"] is True
    assert "DÉMONTRER" in e["lecture"]
    assert e["essais_a_demontrer"]


def test_un_ecart_avec_un_sous_systeme_non_note_n_est_pas_conforme():
    """Conforme sur ce qu'on a regardé n'est pas conforme."""
    e = T.ecart_au_vise({"prod_elec": "IV"}, "III")
    assert e["conforme"] is False


def test_un_niveau_vise_inconnu_est_refuse_avec_les_niveaux_admis():
    e = T.ecart_au_vise(TOUT_IV, "V")
    assert e["vise"] is None
    assert "III" in e["pourquoi"]


# ── Les exigences, et leur progression ────────────────────────────────────

def test_le_niveau_iii_distingue_le_backbone_de_la_distribution_critique():
    """LA NUANCE QUE LES DOSSIERS MANQUENT LE PLUS SOUVENT. Un chemin actif et
    un alterné suffisent sur le backbone ; la distribution critique — de la
    sortie des onduleurs aux baies — exige DEUX chemins simultanément actifs.
    C'est ce que la table de cette plateforme disait faux."""
    iii = T.EXIGENCES["III"]
    assert iii["backbone"] == 2 and iii["backbone_actifs"] == 1
    assert iii["distribution_critique"] == 2
    assert iii["distribution_critique_actifs"] == 2


def test_le_niveau_iv_exige_un_resultat_et_non_un_schema():
    """« N après toute panne » est un RÉSULTAT. Écrire « 2N » comme l'exigence
    transforme un référentiel fondé sur les résultats en liste de matériel."""
    assert "après toute panne" in T.EXIGENCES["IV"]["capacite_min"]
    assert "2N" not in T.EXIGENCES["IV"]["capacite_min"]
    assert "moyen" in T.EXIGENCES["IV"]["capacite_aide"]


def test_le_compartimentage_et_le_froid_continu_sont_propres_au_niveau_iv():
    """Deux exigences que la table d'origine ne portait pas du tout."""
    for code in ("I", "II", "III"):
        assert T.EXIGENCES[code]["compartimente"] is False, code
        assert T.EXIGENCES[code]["froid_continu"] is False, code
    assert T.EXIGENCES["IV"]["compartimente"] is True
    assert T.EXIGENCES["IV"]["froid_continu"] is True


def test_la_maintenabilite_commence_au_niveau_iii():
    assert not T.EXIGENCES["II"]["maintenable_sans_interruption"]
    assert T.EXIGENCES["III"]["maintenable_sans_interruption"]
    assert not T.EXIGENCES["III"]["tolerant_panne"]
    assert T.EXIGENCES["IV"]["tolerant_panne"]


def test_aucune_exigence_ne_regresse_d_un_niveau_au_suivant():
    """Un niveau supérieur qui perdrait une exigence du précédent ferait
    remonter un site en abaissant sa topologie."""
    for champ in ("maintenable_sans_interruption", "tolerant_panne",
                  "compartimente", "froid_continu"):
        vus = [bool(T.EXIGENCES[c][champ]) for c in T.ORDRE]
        assert vus == sorted(vus), (champ, vus)
    for champ in ("backbone", "distribution_critique"):
        vus = [T.EXIGENCES[c][champ] for c in T.ORDRE]
        assert vus == sorted(vus), (champ, vus)


def test_l_autonomie_est_la_meme_a_tous_les_niveaux():
    """Douze heures à la capacité N, du niveau I au niveau IV. C'est le genre
    d'exigence qu'on croit croissante et qui ne l'est pas."""
    for code in T.ORDRE:
        assert T.EXIGENCES[code]["autonomie_h"] == T.AUTONOMIE_H, code


def test_les_niveaux_i_et_ii_sont_tactiques_et_les_deux_autres_strategiques():
    assert T.EXIGENCES["I"]["posture"] == "tactique"
    assert T.EXIGENCES["II"]["posture"] == "tactique"
    assert T.EXIGENCES["III"]["posture"] == "strategique"
    assert T.EXIGENCES["IV"]["posture"] == "strategique"


# ── Les essais de confirmation ────────────────────────────────────────────

@pytest.mark.parametrize("code", ["I", "II", "III", "IV"])
def test_chaque_niveau_porte_ses_essais_et_ses_impacts(code):
    """Les essais sont ce qui se DÉMONTRE ; les impacts, ce que le client
    vivra. Un niveau écrit au marché sans ses essais est invérifiable."""
    assert T.ESSAIS_CONFIRMATION[code]
    assert T.IMPACTS_EXPLOITATION[code]
    for x in T.ESSAIS_CONFIRMATION[code] + T.IMPACTS_EXPLOITATION[code]:
        assert len(x) > 40, (code, x)


def test_le_niveau_iii_annonce_qu_un_defaut_peut_encore_couper():
    """Maintenable sans interruption ne veut pas dire tolérant à la panne —
    la promesse commerciale la plus fréquemment démentie par les faits."""
    txt = " ".join(T.IMPACTS_EXPLOITATION["III"]).lower()
    assert "non programmé" in txt
    assert "tolérant à la panne" in txt


def test_le_niveau_iv_annonce_l_exposition_pendant_l_entretien():
    """Elle ne fait pas perdre le niveau, mais elle se planifie — et le client
    doit le savoir avant, pas pendant."""
    txt = " ".join(T.IMPACTS_EXPLOITATION["IV"]).lower()
    assert "entretien" in txt
    assert "ne fait pas perdre le niveau" in txt


# ── Les groupes électrogènes ──────────────────────────────────────────────

def test_un_groupe_continu_compte_pour_sa_puissance_nominale():
    r = T.capacite_qualifiante_groupes(2000, "continu")
    assert r["qualifiante_kw"] == 2000
    assert r["eligible_iii_iv"] is True


def test_un_groupe_prime_est_declasse_faute_de_certification():
    """Pour un fonctionnement de durée illimitée, la capacité se déclasse."""
    r = T.capacite_qualifiante_groupes(2000, "prime")
    assert r["qualifiante_kw"] == 2000 * T.DECLASSEMENT_PRIME
    assert "déclassement" in r["origine"]


def test_un_groupe_de_secours_ne_compte_pour_rien_sans_certification():
    """Limité en heures annuelles par définition : il ne répond pas à
    l'exigence des niveaux III et IV."""
    r = T.capacite_qualifiante_groupes(2000, "secours")
    assert r["qualifiante_kw"] == 0
    assert r["eligible_iii_iv"] is False


def test_la_certification_du_constructeur_l_emporte_sur_le_declassement():
    """Un déclassement forfaitaire appliqué en silence sur un groupe dont le
    constructeur certifie mieux ferait acheter une machine de trop."""
    r = T.capacite_qualifiante_groupes(2000, "prime", 1600)
    assert r["qualifiante_kw"] == 1600
    assert "certification" in r["origine"]


def test_une_certification_rend_meme_un_groupe_de_secours_eligible():
    """Le référentiel admet qu'un constructeur atteste une capacité tenable
    sans limite de durée, quelle que soit la classe affichée."""
    r = T.capacite_qualifiante_groupes(2000, "secours", 1200)
    assert r["qualifiante_kw"] == 1200
    assert r["eligible_iii_iv"] is True


def test_une_certification_superieure_a_la_plaque_est_plafonnee():
    """Une capacité certifiée au-delà de la puissance nominale ne s'utilise
    pas : elle signale une saisie fausse, pas une machine plus puissante."""
    r = T.capacite_qualifiante_groupes(2000, "prime", 5000)
    assert r["qualifiante_kw"] == 2000
    assert "plafonnée" in r["note"]


def test_une_classe_inconnue_est_un_refus_nomme_et_non_un_silence():
    """C'est la faute que le compteur de redondance de ce dépôt a mis
    longtemps à corriger : un refus muet passe pour un champ vide."""
    r = T.capacite_qualifiante_groupes(2000, "turbo")
    assert r["nature"] == "refus"
    assert r["erreur"] == "classe_inconnue"
    assert "continu" in r["classes"]


def test_une_puissance_illisible_est_un_refus_nomme():
    for mauvaise in ("beaucoup", None, 0, -100, float("nan")):
        r = T.capacite_qualifiante_groupes(mauvaise, "continu")
        assert r["nature"] == "refus", mauvaise


def test_la_virgule_francaise_est_lue():
    r = T.capacite_qualifiante_groupes("1500,5", "continu")
    assert r["nature"] == "calcule"
    assert abs(r["qualifiante_kw"] - 1500.5) < 1e-9


# ── L'autonomie sur site ──────────────────────────────────────────────────

def test_l_autonomie_exige_douze_heures_de_combustible():
    a = T.autonomie({"groupes_puissance_elec_kw": 2000})
    assert a["heures"] == 12
    attendu = 2000 * T.CONSO_SPECIFIQUE_L_KWH * 12 / 1000.0
    assert abs(a["combustible"]["volume_m3"] - attendu) < 1e-9
    assert a["combustible"]["estime"] is True


def test_le_volume_annonce_est_un_plancher_et_le_dit():
    """Hors volume mort et hors nourrices : ce n'est pas un dimensionnement de
    cuve, et le confondre ferait commander trop juste."""
    a = T.autonomie({"groupes_puissance_elec_kw": 2000})
    assert "PLANCHER" in a["combustible"]["note"]


def test_sans_puissance_le_volume_n_est_pas_invente():
    a = T.autonomie({})
    assert "combustible" not in a
    assert a["manques"]


def test_l_eau_d_appoint_n_est_exigee_qu_en_refroidissement_evaporatif():
    sec = T.autonomie({"refroidissement": "air_dx"})
    assert sec["evaporatif"] is False
    assert sec["eau_appoint"]["volume_m3"] is None
    assert "pas évaporatif" in sec["eau_appoint"]["pourquoi"]


def test_l_eau_d_appoint_se_calcule_sur_un_site_evaporatif():
    a = T.autonomie({"refroidissement": "tour_evaporative", "eau_m3_an": 8760})
    assert a["evaporatif"] is True
    assert abs(a["eau_appoint"]["volume_m3"] - 12.0) < 1e-9


def test_l_eau_d_appoint_avertit_que_la_moyenne_n_est_pas_la_pointe():
    """C'est en pointe qu'une réserve sert, et la pointe estivale est plus
    élevée que la moyenne annuelle."""
    a = T.autonomie({"refroidissement": "adiabatique", "eau_m3_an": 8760})
    assert "pointe" in a["eau_appoint"]["note"]


def test_l_autonomie_renvoie_au_regime_administratif():
    """Le volume exigé décide du volume stocké, qui décide de la rubrique, qui
    décide du délai. Les trois se décident ensemble."""
    a = T.autonomie({"groupes_puissance_elec_kw": 1000})
    assert "installation classée" in a["lien_icpe"]


# ── Les règles dures ──────────────────────────────────────────────────────

@pytest.mark.parametrize("cle", sorted(T.REGLES))
def test_chaque_regle_renverse_une_hypothese_et_dit_quoi_verifier(cle):
    r = T.REGLES[cle]
    assert len(r["interdit"]) > 40, cle
    assert len(r["hypothese_renversee"]) > 40, cle
    assert len(r["verifier"]) > 20, cle


def test_le_reseau_public_n_est_pas_une_source_qualifiante():
    """Deux arrivées publiques ne comptent pour aucun niveau, même issues de
    postes sources distincts. C'est l'hypothèse française la plus répandue."""
    r = T.REGLES["reseau_non_qualifiant"]
    assert "limite de propriété" in r["interdit"]
    assert "deux arrivées" in r["hypothese_renversee"].lower()


def test_un_niveau_ne_se_deduit_pas_d_un_calcul_de_fiabilite():
    r = T.REGLES["pas_de_mtbf"]
    assert "topologie" in r["hypothese_renversee"].lower()
    assert "protocole d'essai" in r["verifier"]


def test_la_limite_reglementaire_ne_leve_pas_l_exigence_de_duree():
    """Deux contraintes distinctes : les heures annuelles pour émissions et
    les heures consécutives à la puissance demandée."""
    assert "réglementaire" in T.REGLES["groupe_illimite"]["verifier"]
    assert "distinctes" in T.REGLES["groupe_illimite"]["verifier"]


def test_les_conditions_extremes_chiffrent_le_cout_d_une_valeur_a_deux_pour_cent():
    """« 175 heures par an » se plaide ; « il faut être conservateur » non."""
    r = T.REGLES["conditions_extremes"]
    assert "175" in r["hypothese_renversee"]
    assert "vingt ans" in r["verifier"]


# ── Ce que le module refuse de faire ──────────────────────────────────────

def test_la_reserve_dit_qu_aucun_niveau_n_est_decerne():
    """C'est la phrase qui distingue une qualification d'une certification, et
    elle voyage avec chaque résultat."""
    for r in (T.qualifier(TOUT_IV), T.qualifier({}),
              T.ecart_au_vise(TOUT_IV, "III"), T.autonomie({})):
        assert "DÉCERNÉ" in r["reserve"] or "décerné" in r["reserve"]


def test_la_reserve_rappelle_la_separation_conception_ouvrage():
    assert "conception" in T.RESERVE
    assert "construit" in T.RESERVE


def test_la_source_dit_que_rien_n_est_reproduit():
    """La discipline du dépôt sur les textes normatifs, et la clause de droit
    d'auteur du document : les règles sont reformulées, jamais recopiées."""
    assert "reformul" in T.SOURCE
    assert "reproduit" in T.SOURCE


# ── Le contrôle de chargement se vérifie lui-même ─────────────────────────

def test_le_controle_attrape_une_exigence_qui_regresse(monkeypatch):
    faux = {k: dict(v) for k, v in T.EXIGENCES.items()}
    faux["IV"]["maintenable_sans_interruption"] = False
    monkeypatch.setattr(T, "EXIGENCES", faux)
    assert any("régresse" in f for f in T._verifier())


def test_le_controle_attrape_une_autonomie_divergente(monkeypatch):
    faux = {k: dict(v) for k, v in T.EXIGENCES.items()}
    faux["I"]["autonomie_h"] = 8
    monkeypatch.setattr(T, "EXIGENCES", faux)
    assert any("autonomie" in f for f in T._verifier())


def test_le_controle_attrape_un_declassement_ecrit_deux_fois(monkeypatch):
    """La part de la classe « prime » et la constante nommée doivent rester
    la même valeur : deux littéraux recopiés divergent."""
    faux = {k: dict(v) for k, v in T.CLASSES_GROUPE.items()}
    faux["prime"]["part"] = 0.8
    monkeypatch.setattr(T, "CLASSES_GROUPE", faux)
    assert any("deux fois" in f for f in T._verifier())


def test_le_controle_attrape_un_rang_en_double(monkeypatch):
    """Le « plus bas des sous-systèmes » repose sur les rangs : un doublon
    rendrait le minimum ambigu."""
    faux = {k: dict(v) for k, v in T.EXIGENCES.items()}
    faux["III"]["rang"] = 2
    monkeypatch.setattr(T, "EXIGENCES", faux)
    assert any("rangs" in f for f in T._verifier())


# ── Le glossaire ──────────────────────────────────────────────────────────

def test_le_glossaire_couvre_les_quatre_familles():
    g = T.glossaire()
    assert set(g) == {"tier_exigence", "tier_essai", "tier_regle",
                      "classe_groupe"}
    assert set(g["tier_exigence"]) == set(T.EXIGENCES)
    assert set(g["tier_regle"]) == set(T.REGLES)


def test_l_infobulle_d_un_niveau_porte_la_reserve():
    """Elle sera lue en survolant un sigle, hors de tout contexte. Sans la
    réserve, elle se lit comme une certification."""
    for code in T.ORDRE:
        assert "DÉCERNÉ" in T.glossaire()["tier_exigence"][code]["aide"]


def test_aucune_infobulle_n_est_vide():
    for famille, entrees in T.glossaire().items():
        for cle, e in entrees.items():
            assert len(e["aide"]) > 80, (famille, cle, len(e["aide"]))
