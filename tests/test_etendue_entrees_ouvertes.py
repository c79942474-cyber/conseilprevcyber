"""_PLAGES_PLAUSIBLES : une clé morte rendait la part évaporative invisible.

LE DÉFAUT CORRIGÉ. La table qui balaie l'étendue due aux entrées non
renseignées portait la clé "part_evaporation" ; le champ réel du moteur
s'appelle "part_evaporative" (datacenter.py, profil_dc.py). Les deux ne se
recoupant jamais, la part évaporative — qui pèse 44 % du WUE de site quand
elle est laissée ouverte — ne pouvait JAMAIS apparaître dans l'étendue
affichée au lecteur, quel que soit le profil saisi.

CE QUE CES TESTS PROTÈGENT :

  1. Un contrôle de santé refuse désormais qu'une clé de _PLAGES_PLAUSIBLES
     ne corresponde à aucun champ réel du moteur — la faute qui s'est
     produite ici, et qui se serait tue un an de plus sans lui.
  2. Le cas concret du constat se rejoue : 1 000 kW, France, tour évaporative,
     part évaporative non renseignée — elle doit ressortir, et dominante.
"""
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ingenierie_dc as I  # noqa: E402


def test_la_sante_ne_signale_aucune_clé_de_plage_inconnue():
    assert I.sante()["plages_plausibles_champs_inconnus"] == []


def test_la_sante_TOMBE_sur_une_clé_de_plage_qui_ne_correspond_a_rien():
    """Prouvé plutôt qu'affirmé : on réintroduit la faute de frappe exacte du
    défaut passé, on vérifie que le contrôle la voit, on restaure — dans un
    try/finally pour ne pas laisser le module mutilé si l'assertion échoue."""
    sauve = dict(I._PLAGES_PLAUSIBLES)
    try:
        del I._PLAGES_PLAUSIBLES["part_evaporative"]
        I._PLAGES_PLAUSIBLES["part_evaporation"] = (0.55, 0.95)
        fautes = I.sante()["plages_plausibles_champs_inconnus"]
        assert fautes == ["part_evaporation"], fautes
    finally:
        I._PLAGES_PLAUSIBLES.clear()
        I._PLAGES_PLAUSIBLES.update(sauve)
    assert I.sante()["plages_plausibles_champs_inconnus"] == []


def test_le_cas_du_constat_la_part_evaporative_ressort_et_domine():
    """1 000 kW, France, tour évaporative, part évaporative non renseignée :
    le WUE de site doit porter une étendue MESURÉE dont le champ dominant est
    la part évaporative, à ~44 % — pas une étendue vide."""
    profil = {"puissance_it_kw": 1000, "pays": "FR",
              "refroidissement": "tour_evaporative", "taux_charge": 0.6}
    a = I.aptitude(profil, "APD")
    manquants = {m["id"] for m in (a.get("entrees_manquantes") or [])}
    assert "part_evaporative" in manquants, (
        "le profil de contrôle doit laisser CE champ non renseigné, sinon le "
        "test ne prouve rien")

    d = I.dossier(profil, "APD")
    wue = next(g for g in d["grandeurs"] if g["nom"] == "WUE de site")
    ouvert = wue["entrees_ouvertes"]
    assert ouvert["mesuree"] is True, (
        "la clé morte fait retomber l'étendue à \"non mesurée\" — c'est "
        "exactement ce que ce test doit détecter")
    ids = {c["id"] for c in ouvert["champs"]}
    assert "part_evaporative" in ids, ouvert
    assert ouvert["dominant"] == "Part de chaleur rejetée par évaporation", ouvert
    assert 40.0 < ouvert["dominant_pct"] < 50.0, ouvert["dominant_pct"]
