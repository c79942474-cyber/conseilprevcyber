"""Le taux de charge — deux seuils, une zone plate, et ce qu'il faut en dire.

LE SIGNALEMENT : « blocage, bug avec ce coefficient ». Il n'y avait pas de
plantage. Il y avait pire, parce que c'est invisible : un réglage qui a l'air
d'agir et n'agit pas.

TROIS DÉFAUTS, MESURÉS :

  1. DEUX SEUILS DIFFÉRENTS DANS LE MÊME ÉCRAN. Le calcul appliquait sa pénalité
     sous 0,60. Le texte d'aide du champ, l'étiquette de la suggestion et la
     recommandation d'amélioration annonçaient tous 0,55. Quelqu'un qui saisit
     0,57 lisait donc qu'il était au-dessus du seuil pendant que le moteur le
     pénalisait déjà.

  2. UNE ZONE PLATE NON DÉCLARÉE. Au-dessus du point de conception la pénalité
     vaut zéro : 0,65, 0,80, 0,90 et 1,00 donnent EXACTEMENT le même PUE. Le
     formulaire proposait pourtant « 0,80 — site mature, bien rempli » comme un
     choix qui compte. On cliquait, rien ne bougeait.

  3. LES SEUILS ÉTAIENT ÉCRITS À LA MAIN à quatre endroits. Deux nombres
     recopiés finissent toujours par diverger — c'est ce qui s'était produit.

CE QU'ON NE CORRIGE PAS, ET C'EST DÉLIBÉRÉ : le modèle reste plat au-dessus du
point de conception. Inventer une prime pour un site mieux rempli produirait un
chiffre invérifiable dans une note de calcul annexée à une offre. On déclare la
limite au lieu de la combler avec une valeur inventée.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import datacenter as dc  # noqa: E402

PROFIL = {"puissance_it_kw": 50000, "pays": "FR",
          "refroidissement": "tour_evaporative"}


def _pue(taux):
    return dc.etude(dict(PROFIL, taux_charge=taux))["energie"]["pue"]


# ── 1. Un seul seuil, et il est nommé ──────────────────────────────────────

def test_les_seuils_sont_des_constantes_nommees():
    assert dc.CHARGE_POINT_CONCEPTION == 0.60
    assert dc.CHARGE_CONSOLIDER == 0.55
    assert dc.CHARGE_PENTE == 0.45


def test_les_deux_seuils_restent_distincts():
    """Ils ne répondent pas à la même question : à partir de quand le PUE se
    dégrade, et à partir de quand consolider devient le premier levier. Les
    confondre serait une autre erreur."""
    assert dc.CHARGE_CONSOLIDER < dc.CHARGE_POINT_CONCEPTION


def test_le_texte_du_champ_cite_les_deux_seuils_du_calcul():
    """LE contrôle de non-divergence : le texte doit porter les valeurs
    RÉELLEMENT appliquées, pas des nombres recopiés."""
    aide = {c["id"]: c for c in dc.CHAMPS}["taux_charge"]["aide"]
    assert dc.fr(dc.CHARGE_POINT_CONCEPTION) in aide
    assert dc.fr(dc.CHARGE_CONSOLIDER) in aide
    assert dc.fr(dc.CHARGE_PENTE) in aide


def test_le_texte_annonce_la_zone_plate():
    """Sans cette phrase, le lecteur conclut au blocage — c'est ce qui est
    arrivé."""
    aide = {c["id"]: c for c in dc.CHAMPS}["taux_charge"]["aide"]
    assert "ne varie plus" in aide


# ── LA ZONE PLATE NE CONCERNE QUE LE PUE ───────────────────────────────────
#
# Ce contrôle remplace celui qui exigeait la phrase « changer cette valeur ne
# changera pas le résultat ». Cette phrase était FAUSSE, et le test la gelait :
# il comparait le texte à lui-même au lieu de le comparer au moteur. C'est la
# façon la plus sûre de rendre un défaut permanent — le test protégeait l'erreur
# qu'il aurait dû trouver.
#
# Les contrôles ci-dessous partent donc du CALCUL, et n'acceptent le texte que
# s'il lui correspond.

PROFIL = {"puissance_it_kw": 50000, "pays": "FR",
          "refroidissement": "tour_evaporative"}


def test_au_dessus_du_point_de_conception_seul_le_PUE_est_plat():
    """LE contrôle. Le PUE ne bouge pas — l'énergie, elle, bouge beaucoup."""
    bas = dc.etude(dict(PROFIL, taux_charge=dc.CHARGE_POINT_CONCEPTION))
    haut = dc.etude(dict(PROFIL, taux_charge=1.0))
    assert bas["energie"]["pue"]["valeur"] == haut["energie"]["pue"]["valeur"]
    e_bas = bas["energie"]["energie_totale_MWh"]["valeur"]
    e_haut = haut["energie"]["energie_totale_MWh"]["valeur"]
    assert e_haut > e_bas * 1.5, (e_bas, e_haut)


def test_le_carbone_et_l_eau_suivent_aussi_la_charge():
    """Si seule l'énergie bougeait, le texte pourrait se contenter de la
    nommer. Elle entraîne les deux autres."""
    bas = dc.etude(dict(PROFIL, taux_charge=0.65))
    haut = dc.etude(dict(PROFIL, taux_charge=0.85))
    assert (haut["carbone"]["empreinte_totale_t"]["valeur"]
            > bas["carbone"]["empreinte_totale_t"]["valeur"])
    assert (haut["eau"]["evaporation_m3"]["valeur"]
            > bas["eau"]["evaporation_m3"]["valeur"])
    # …tandis que les RATIOS, eux, restent bien constants : c'est ce qui rend
    # la confusion possible, et c'est pourquoi le texte doit la lever.
    assert (haut["eau"]["wue_site"]["valeur"]
            == bas["eau"]["wue_site"]["valeur"])


def test_le_texte_ne_dit_jamais_que_la_valeur_est_sans_effet():
    """La phrase exacte qui a induit en erreur, et toutes ses cousines. Un
    lecteur qui la croit laisse le taux par défaut pour un site à 0,85 et
    repart avec une énergie sous-estimée d'un tiers."""
    aide = {c["id"]: c for c in dc.CHAMPS}["taux_charge"]["aide"]
    textes = [aide, dc.PLATEAU_PUE]
    textes += [s["nom"] for s in dc.SUGGESTIONS["taux_charge"]]
    for t in textes:
        for interdite in ("ne changera pas le résultat",
                          "sans effet sur le résultat",
                          "n'a aucun effet"):
            assert interdite not in t, (interdite, t)


def test_le_texte_dit_ce_qui_reste_proportionnel_a_la_charge():
    """Dire que le PUE est plat sans dire ce qui ne l'est pas laisse le lecteur
    conclure de lui-même — et il conclut mal, c'est ce qui est arrivé."""
    aide = {c["id"]: c for c in dc.CHAMPS}["taux_charge"]["aide"]
    assert "proportionnels" in aide
    for grandeur in ("énergie", "eau", "carbone"):
        assert grandeur in aide, grandeur


def test_l_explication_de_la_zone_plate_a_UNE_seule_source():
    """Elle était écrite à la main en quatre endroits ; trois disaient vrai et
    le quatrième disait le contraire. Les textes servis la LISENT désormais."""
    aide = {c["id"]: c for c in dc.CHAMPS}["taux_charge"]["aide"]
    assert dc.PLATEAU_PUE in aide
    pue = dc.etude(dict(PROFIL, taux_charge=0.80))["energie"]["pue"]
    assert dc.PLATEAU_PUE in pue["entrees"]["origine"]


# ── 2. La pénalité fait ce que le texte annonce ────────────────────────────

@pytest.mark.parametrize("taux", [0.30, 0.45, 0.55, 0.59])
def test_sous_le_point_de_conception_la_penalite_existe(taux):
    assert dc.penalite_charge(taux) > 0


@pytest.mark.parametrize("taux", [0.60, 0.65, 0.80, 0.90, 1.00])
def test_au_dessus_la_penalite_est_nulle(taux):
    assert dc.penalite_charge(taux) == 0.0


def test_la_penalite_est_continue_au_point_de_conception():
    """Une marche à la frontière ferait sauter le PUE pour un centième de
    charge — indéfendable dans une note de calcul."""
    juste_dessous = dc.penalite_charge(dc.CHARGE_POINT_CONCEPTION - 0.001)
    assert juste_dessous < 0.001


def test_la_penalite_croit_quand_la_charge_baisse():
    valeurs = [dc.penalite_charge(t) for t in (0.59, 0.50, 0.40, 0.30)]
    assert valeurs == sorted(valeurs), "la pénalité doit croître en descendant"


def test_la_pente_est_bien_celle_annoncee():
    ecart = dc.penalite_charge(0.50) - dc.penalite_charge(0.55)
    assert abs(ecart - 0.05 * dc.CHARGE_PENTE) < 1e-9


# ── 3. La zone plate est déclarée dans le RÉSULTAT, pas seulement dans l'aide ──

def test_le_resultat_dit_lui_meme_que_le_pue_ne_bouge_plus():
    """C'est le chiffre servi qui doit se défendre : le lecteur d'une note
    exportée n'a pas le formulaire sous les yeux."""
    o = _pue(0.80)["entrees"]["origine"]
    assert "aucune pénalité" in o
    assert "ne varie plus" in o
    assert dc.fr(dc.CHARGE_POINT_CONCEPTION) in o


def test_sous_le_seuil_le_resultat_dit_qu_il_est_penalise():
    o = _pue(0.45)["entrees"]["origine"]
    assert "pénalité de charge partielle" in o


def test_le_pue_est_bien_identique_de_0_60_a_1_00():
    """On VERROUILLE le fait, au lieu de le laisser surprendre : si un jour le
    modèle gagne un terme au-dessus du point de conception, ce test tombera et
    obligera à reprendre les textes en même temps."""
    valeurs = {_pue(t)["valeur"] for t in (0.60, 0.65, 0.80, 0.90, 1.00)}
    assert len(valeurs) == 1, valeurs


def test_le_pue_varie_bien_sous_le_seuil():
    """L'inverse compte autant : si le réglage n'agissait NULLE PART, ce serait
    un vrai blocage."""
    valeurs = [_pue(t)["valeur"] for t in (0.30, 0.40, 0.50, 0.59)]
    assert len(set(valeurs)) == 4
    assert valeurs == sorted(valeurs, reverse=True)


# ── 4. Les suggestions ne promettent plus un effet qu'elles n'ont pas ──────

def test_les_suggestions_couvrent_les_deux_seuils():
    v = [s["valeur"] for s in dc.SUGGESTIONS["taux_charge"]]
    assert dc.CHARGE_CONSOLIDER in v
    assert dc.CHARGE_POINT_CONCEPTION in v


def test_la_suggestion_0_80_previent_qu_elle_ne_change_rien():
    s = [x for x in dc.SUGGESTIONS["taux_charge"] if x["valeur"] == 0.80][0]
    assert "même PUE" in s["nom"], s["nom"]


def test_la_suggestion_par_defaut_previent_aussi():
    s = [x for x in dc.SUGGESTIONS["taux_charge"] if x["valeur"] == 0.65][0]
    assert "sans effet" in s["nom"], s["nom"]


# ── 5. La recommandation suit le même seuil nommé ──────────────────────────

def test_la_recommandation_de_consolidation_suit_son_seuil():
    def propose(taux):
        # La clé est « leviers ». L'étude n'expose pas d'« ameliorations » : un
        # nom deviné plutôt que mesuré rendait ce contrôle vide de sens, il
        # passait sur une liste toujours absente.
        e = dc.etude(dict(PROFIL, taux_charge=taux))
        return any("onsolider les charges" in (a.get("titre") or "")
                   for a in (e.get("leviers") or []))
    assert propose(dc.CHARGE_CONSOLIDER - 0.05)
    assert not propose(dc.CHARGE_CONSOLIDER)
    assert not propose(dc.CHARGE_CONSOLIDER + 0.05)
