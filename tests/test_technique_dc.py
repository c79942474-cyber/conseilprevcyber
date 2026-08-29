"""Le vocabulaire du métier servi aux infobulles — et ce qui le tient au moteur.

CE QUI EST ÉPROUVÉ ICI. Pas la justesse des descriptions — un test ne sait pas
si un free cooling direct fonctionne comme il est écrit. Ce qui s'éprouve, ce
sont les PROPRIÉTÉS qui font qu'une infobulle existe et dit la bonne chose :

  · toute famille du moteur de calcul a son explication, et réciproquement ;
  · un mode qui n'est pas une famille de calcul DIT par quelle famille il est
    porté, sans quoi le lecteur cherche dans la liste une option absente ;
  · les deux axes d'une architecture électrique sont peuplés ;
  · le glossaire servi à la page couvre ce que la page pose.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import datacenter  # noqa: E402
import technique_dc as T  # noqa: E402


# ── Ce qui lie ce module au moteur ─────────────────────────────────────────

def test_toute_famille_du_moteur_a_son_explication():
    """LE DÉFAUT QUE CETTE RÈGLE EMPÊCHE, et qui est invisible. Une famille
    ajoutée au moteur apparaît aussitôt dans la liste déroulante du
    formulaire ; sans entrée ici, elle s'y affiche SANS infobulle. Une
    infobulle manquante ne lève rien, ne s'affiche pas en rouge et ne se
    remarque qu'en survolant — c'est-à-dire jamais, par celui qui l'a
    ajoutée."""
    declarees = {v["famille"] for v in T.MODES_REFROIDISSEMENT.values()
                 if v.get("famille")}
    assert set(datacenter.REFROIDISSEMENT) <= declarees, (
        set(datacenter.REFROIDISSEMENT) - declarees)


def test_aucune_explication_ne_parle_d_une_famille_inconnue_du_moteur():
    """L'inverse compte autant : une explication orpheline propose une
    conception que le calcul ne sait pas traiter."""
    declarees = {v["famille"] for v in T.MODES_REFROIDISSEMENT.values()
                 if v.get("famille")}
    assert declarees <= set(datacenter.REFROIDISSEMENT), (
        declarees - set(datacenter.REFROIDISSEMENT))


def test_un_mode_sans_famille_dit_par_quelle_famille_il_est_porte():
    """LE CAS DU FREE-CHILLING. Ce n'est pas une famille de calcul : c'est un
    mode de conduite d'une production d'eau glacée. Le déclarer comme une
    famille ferait chercher une septième option dans une liste qui en compte
    sept ; ne rien dire ferait croire qu'il n'existe pas. Il porte donc sa
    famille porteuse, et cette règle vérifie que TOUT mode sans famille en
    porte une — la prochaine addition comprise."""
    for cle, m in T.MODES_REFROIDISSEMENT.items():
        if not m.get("famille"):
            assert m.get("porte_par"), cle
            assert m["porte_par"] in datacenter.REFROIDISSEMENT, (cle, m["porte_par"])


def test_le_free_chilling_est_explique_et_n_est_pas_une_famille():
    """Il était absent, et c'est la première chose qu'un client demande après
    « free cooling ». Il est là, et il n'est PAS proposé au calcul."""
    m = T.MODES_REFROIDISSEMENT["free_chilling"]
    assert m["famille"] is None
    assert m["porte_par"] == "eau_glacee"
    assert "free_chilling" not in datacenter.REFROIDISSEMENT


def test_l_aide_d_un_mode_porte_dit_ou_le_choisir():
    """Dire « ce n'est pas une famille » sans dire laquelle retenir laisse le
    lecteur devant sa liste. La mention doit nommer la famille porteuse."""
    aide = T.glossaire()["mode_froid"]["free_chilling"]["aide"]
    porteuse = datacenter.REFROIDISSEMENT["eau_glacee"]["nom"]
    assert porteuse in aide, aide[:200]


def test_mode_de_famille_retrouve_le_mode_et_rend_none_sur_l_inconnu():
    assert T.mode_de_famille("adiabatique")["cle"] == "adiabatique"
    # Une famille inconnue vaut « pas d'explication », ce qui se rend par une
    # absence d'infobulle — pas par une page en erreur.
    assert T.mode_de_famille("famille_qui_n_existe_pas") is None


# ── Les modes de refroidissement demandés ──────────────────────────────────

@pytest.mark.parametrize("cle", ["free_cooling_air", "free_chilling",
                                 "adiabatique", "liquide_dlc"])
def test_les_quatre_modes_demandes_sont_expliques(cle):
    """Free-cooling, free-chilling, adiabatique et DLC : les quatre que le
    métier confond, et sur lesquels se joue la première réunion."""
    m = T.MODES_REFROIDISSEMENT[cle]
    for champ in ("principe", "quand", "cout", "contrainte", "erreur"):
        assert len(m[champ]) > 40, (cle, champ)


def test_le_dlc_dit_que_l_air_reste_necessaire():
    """LA FAUTE DE CONCEPTION LA PLUS CHÈRE sur un projet DLC : dimensionner
    le froid air comme s'il n'y en avait plus. La plaque froide capte 70 à
    80 % de la chaleur, pas la totalité — et le reste est à évacuer."""
    m = T.MODES_REFROIDISSEMENT["liquide_dlc"]
    texte = (m["principe"] + " " + m["contrainte"] + " " + m["erreur"]).lower()
    assert "air" in texte
    assert "reste" in texte or "part non captée" in texte


def test_l_adiabatique_dit_que_la_pointe_compte_plus_que_la_moyenne():
    """C'est l'argument qui se plaide devant une autorité de l'eau, et celui
    qu'un WUE annuel efface."""
    m = T.MODES_REFROIDISSEMENT["adiabatique"]
    assert "pointe" in (m["contrainte"] + m["erreur"]).lower()


# ── Les architectures électriques ──────────────────────────────────────────

def test_les_deux_axes_sont_peuples():
    """Production ET distribution. La faute classique est de croire que la
    première suffit : deux chaînes complètes qui se rejoignent sur un tableau
    terminal unique ne font qu'un seul chemin."""
    for axe in ("production", "distribution"):
        assert T.architectures(axe), axe


def test_architectures_sans_axe_rend_tout():
    assert len(T.architectures()) == len(T.ARCHITECTURES_ELEC)


def test_la_double_voie_signale_le_materiel_a_alimentation_simple():
    """C'est ce qui ramène le point unique dans une architecture qu'on croit
    doublée — et le commutateur de source devient à son tour l'organe seul."""
    a = T.ARCHITECTURES_ELEC["double_voie"]
    assert "simple" in a["point_faible"].lower()


def test_le_2n_dit_qu_il_degrade_le_rendement():
    """Deux chaînes à demi-charge tournent hors de leur meilleur point. Ne pas
    le dire fait passer une conséquence normale pour un défaut de conception
    au moment où le PUE mesuré déçoit."""
    a = T.ARCHITECTURES_ELEC["deux_n"]
    assert "pue" in a["point_faible"].lower() or "rendement" in a["point_faible"].lower()


# ── Les enjeux d'une première réunion ──────────────────────────────────────

@pytest.mark.parametrize("cle", ["tier", "pue", "wue", "icpe"])
def test_chaque_enjeu_dit_ce_qu_il_n_atteste_pas(cle):
    """C'est la colonne qui évite les malentendus coûteux : un Tier IV peut
    être hors la loi, un excellent PUE peut cacher des serveurs inutiles."""
    e = T.ENJEUX_DC[cle]
    assert len(e["n_atteste_pas"]) > 40, cle
    assert len(e["a_repondre"]) > 40, cle


def test_le_tier_ne_s_attribue_pas():
    """« Certifié Tier III » pour un site conçu selon les principes du niveau
    est un risque contractuel, pas une approximation commerciale."""
    piege = T.ENJEUX_DC["tier"]["piege"].lower()
    assert "certification" in piege or "certifié" in piege
    assert "conception" in piege


def test_l_enjeu_tier_porte_la_regle_du_plus_bas_sous_systeme():
    """C'EST LA RÈGLE QUI DÉCIDE, et elle vaut d'être dans l'enjeu autant que
    dans le module de calcul : elle se dit en première réunion, avant tout
    calcul. Un site vaut son sous-système le plus faible — jamais la moyenne,
    et il n'existe aucun niveau fractionnaire."""
    piege = T.ENJEUX_DC["tier"]["piege"]
    assert "PLUS BAS" in piege, piege
    assert "moyenne" in piege.lower(), piege
    # Et l'exemple qui la rend concrète : c'est lui qu'on retient.
    assert "froid" in piege.lower()


def test_l_enjeu_tier_renvoie_aux_essais_et_non_a_une_liste_de_materiel():
    """Le référentiel se démontre par des épreuves dont l'issue est
    observable. Demander « quel Tier ? » sans demander les essais laisse
    croire qu'une liste de matériel suffit."""
    rep = T.ENJEUX_DC["tier"]["a_repondre"].lower()
    assert "essais" in rep
    assert "liste de contrôle" in rep or "liste de matériel" in rep


def test_le_raccordement_dit_que_le_reseau_public_ne_qualifie_pas():
    """L'hypothèse française la plus répandue : « nous avons deux arrivées,
    donc nous sommes redondants ». Aucune arrivée publique ne compte.

    LA RÈGLE PORTE SUR LA NÉGATION, pas sur le vocabulaire. Sa première
    version cherchait « limite de propriété » n'importe où dans la phrase :
    une réécriture qui aurait ouvert par « deux arrivées suffisent » tout en
    gardant la locution plus loin passait — c'est-à-dire qu'elle acceptait
    l'exact contraire de ce qu'elle prétend vérifier."""
    pf = T.ARCHITECTURES_ELEC["raccordement"]["point_faible"]
    bas = pf.lower()
    assert "aucune arrivée publique ne compte" in bas, pf
    i_aucune = bas.index("aucune arrivée publique")
    assert "limite de propriété" in bas[i_aucune:], (
        "la négation n'est pas motivée par la limite de propriété", pf)
    # QUI est primaire, pas seulement que le mot figure. Chercher « primaire »
    # laissait passer « le réseau public est la source primaire » — soit
    # exactement l'inverse, avec le bon vocabulaire.
    assert "production sur site est la source primaire" in bas[i_aucune:], (
        "la production sur site n'est pas désignée comme source primaire", pf)


def test_les_groupes_disent_que_la_classe_decide_de_l_eligibilite():
    """Un groupe limité en heures consécutives à la puissance demandée ne
    répond pas à l'exigence des niveaux III et IV — et une classe « secours »
    l'est par définition.

    ICI AUSSI, LA RÈGLE PORTE SUR LE LIEN DE CAUSE, pas sur les mots. « classe »
    apparaît deux fois dans la phrase : chercher le mot laissait passer une
    réécriture qui supprimait précisément l'affirmation selon laquelle la
    classe DÉCIDE."""
    pf = T.ARCHITECTURES_ELEC["groupes"]["point_faible"]
    bas = pf.lower()
    assert "classe de service décide" in bas, pf
    i = bas.index("classe de service décide")
    suite = bas[i:]
    assert "secours" in suite, ("le cas qui disqualifie n'est pas nommé", pf)
    assert "consécutives" in suite, ("la limite qui disqualifie n'est pas "
                                     "nommée", pf)


def test_le_pue_exige_son_perimetre_sa_periode_et_sa_charge():
    """Le même site affiche 1,2 et 1,6 sans qu'aucune valeur ne soit fausse.
    Un PUE sans ces trois-là ne veut rien dire."""
    e = T.ENJEUX_DC["pue"]
    t = (e["piege"] + " " + e["a_repondre"]).lower()
    for mot in ("périmètre", "période", "charge"):
        assert mot in t, mot


# ── Les natures de travaux ─────────────────────────────────────────────────

@pytest.mark.parametrize("cle", ["neuf", "fit_out", "retrofit"])
def test_les_trois_natures_de_travaux_existent(cle):
    """Le fit-out et le rétrofit étaient absents du dépôt — un mot chacun —
    alors que la majorité des opérations françaises en relèvent."""
    n = T.NATURES_TRAVAUX[cle]
    for champ in ("ce_que_c_est", "phases", "risque", "moe"):
        assert len(n[champ]) > 40, (cle, champ)


def test_le_fit_out_nomme_les_capacites_du_batiment_recu():
    """Charge au plancher, hauteur libre, réservations, puissance déjà
    négociée : ce sont des données à RELEVER, et un plancher qui ne porte pas
    les batteries se découvre en exécution."""
    r = T.NATURES_TRAVAUX["fit_out"]["risque"].lower()
    assert "plancher" in r
    assert "relever" in r or "relevé" in r


def test_le_retrofit_impose_le_phasage_d_exploitation():
    """Le site fonctionne et doit continuer à fonctionner : c'est cette étude,
    pas les plans, qui décide de la faisabilité."""
    n = T.NATURES_TRAVAUX["retrofit"]
    assert "phasage" in n["phases"].lower()
    assert "exploitation" in n["moe"].lower()


# ── Le glossaire servi à la page ───────────────────────────────────────────

def test_le_glossaire_couvre_les_quatre_tables():
    g = T.glossaire()
    assert set(g) == {"mode_froid", "archi_elec", "enjeu", "nature_travaux"}
    assert set(g["mode_froid"]) == set(T.MODES_REFROIDISSEMENT)
    assert set(g["archi_elec"]) == set(T.ARCHITECTURES_ELEC)
    assert set(g["enjeu"]) == set(T.ENJEUX_DC)
    assert set(g["nature_travaux"]) == set(T.NATURES_TRAVAUX)


def test_aucune_entree_de_glossaire_n_est_vide():
    """Une infobulle vide est pire qu'aucune : elle s'ouvre et n'apprend rien,
    et le lecteur cesse de survoler les suivantes."""
    for famille, entrees in T.glossaire().items():
        for cle, e in entrees.items():
            assert e["nom"].strip(), (famille, cle)
            assert len(e["aide"]) > 60, (famille, cle, len(e["aide"]))


def test_le_referentiel_sert_la_source_avec_les_modes():
    """Ces descriptions cadrent un métier, elles ne fixent aucune performance.
    Servies sans leur réserve, elles se lisent comme des spécifications."""
    r = T.referentiel()
    assert r["modes_source"]
    assert "norme" in r["modes_source"].lower()


# ── Le contrôle de cohérence du module lui-même ────────────────────────────

def test_le_controle_de_chargement_attrape_une_famille_orpheline(monkeypatch):
    """LA RÈGLE SE VÉRIFIE ELLE-MÊME. On ajoute au moteur une famille sans
    explication et on rappelle le contrôle : s'il ne dit rien, c'est lui qui
    est cassé, et plus rien ne protège les infobulles."""
    faux = dict(datacenter.REFROIDISSEMENT)
    faux["cryogenie"] = {"nom": "Refroidissement cryogénique"}
    monkeypatch.setattr(datacenter, "REFROIDISSEMENT", faux)
    fautes = T._verifier()
    assert any("cryogenie" in f for f in fautes), fautes


def test_le_controle_de_chargement_attrape_un_mode_sans_rattachement(monkeypatch):
    """Un mode ni famille de calcul ni conduite d'une autre : le lecteur ne
    saurait pas quoi choisir dans la liste."""
    faux = dict(T.MODES_REFROIDISSEMENT)
    faux["flottant"] = {"nom": "Un mode sans rattachement", "famille": None,
                        "principe": "x" * 50, "quand": "x" * 50,
                        "cout": "x" * 50, "contrainte": "x" * 50,
                        "erreur": "x" * 50}
    monkeypatch.setattr(T, "MODES_REFROIDISSEMENT", faux)
    fautes = T._verifier()
    assert any("flottant" in f for f in fautes), fautes


def test_le_controle_de_chargement_attrape_un_axe_vide(monkeypatch):
    """Une table d'architectures sans distribution laisserait croire que la
    production suffit — l'erreur exacte que la table existe pour lever."""
    faux = {k: v for k, v in T.ARCHITECTURES_ELEC.items()
            if v["axe"] != "distribution"}
    monkeypatch.setattr(T, "ARCHITECTURES_ELEC", faux)
    fautes = T._verifier()
    assert any("distribution" in f for f in fautes), fautes
