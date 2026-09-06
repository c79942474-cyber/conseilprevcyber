# -*- coding: utf-8 -*-
"""La veille collecte une fois par semaine — et le fait vraiment.

LA DÉCISION. Le catalogue était interrogé toutes les six heures. Trente-six
sources officielles relues quatre fois par jour, c'est beaucoup de sollicitation
pour des flux qui publient au rythme des avis de sécurité — et rien de ce que
la page montre n'exige cette fraîcheur. La cadence passe à SEPT JOURS.

POURQUOI CE N'EST PAS `every = 7 * 24 * 3600`, ET C'EST TOUT LE SUJET. Le
planificateur vit EN MÉMOIRE : `_register_jobs` pose `next = now + first`, avec
`first` à 180 secondes. Un redémarrage relance donc une collecte trois minutes
plus tard, quel que soit l'intervalle. Or ce service redéploie à chaque commit.
« Toutes les semaines » aurait signifié « toutes les semaines, ou à chaque
déploiement, le plus tôt des deux » — c'est-à-dire, certains jours, plusieurs
fois par jour. Un réglage qui annonce une chose et en produit une autre est
précisément ce que ce dépôt traque.

LA CADENCE SE LIT DONC DANS L'ÉTAT PERSISTANT, comme `job_rapport_hebdo` le
fait déjà avec sa clé de semaine. Et le RÉVEIL reste horaire, ce qui n'est pas
une contradiction mais la condition du rattrapage : un réveil aussi espacé que
la cadence reporterait la collecte d'autant à chaque arrêt.

CES RÈGLES SONT EN GRANDE PARTIE COMPORTEMENTALES. `_veille_due()` se laisse
appeler avec un état de substitution : on mesure ce qu'elle DÉCIDE, plutôt que
de relire le texte qui prétend le décider.
"""
import io
import os
import re
import sys
import time

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import automation                                                  # noqa: E402

SOURCE = io.open(os.path.join(ICI, "automation.py"), encoding="utf-8").read()

SEMAINE = 7 * 24 * 3600


class _EtatFactice:
    """Un état persistant en mémoire — ce que `_State` offre, sans la base."""

    def __init__(self, valeurs=None):
        self.valeurs = dict(valeurs or {})
        self.ecritures = []

    def get(self, cle, defaut=None):
        return self.valeurs.get(cle, defaut)

    def set(self, cle, valeur):
        self.valeurs[cle] = valeur
        self.ecritures.append((cle, valeur))


@pytest.fixture
def etat(monkeypatch):
    faux = _EtatFactice()
    monkeypatch.setattr(automation, "_state", faux)
    monkeypatch.delenv("VEILLE_INTERVAL_HOURS", raising=False)
    return faux


def _corps(nom):
    """Le corps d'une fonction, SANS sa docstring : une règle qui lirait la
    prose serait verte devant le code qui la contredit."""
    i = SOURCE.index("\ndef %s(" % nom)
    j = SOURCE.find("\ndef ", i + 1)
    corps = SOURCE[i:j if j > 0 else len(SOURCE)]
    if corps.count('"""') >= 2:
        return corps[corps.index('"""', corps.index('"""') + 3) + 3:]
    return corps


# ══════════════════════════════════════════════════════════════════════════
# 1. UNE SEMAINE, ET MESURÉE COMME TELLE
# ══════════════════════════════════════════════════════════════════════════

def test_six_jours_ne_suffisent_pas_et_huit_jours_declenchent(etat):
    """La cadence est éprouvée par ses DEUX bords. Vérifier seulement qu'une
    semaine déclenche laisserait passer un `>= 0` : tout déclencherait, et la
    règle resterait verte."""
    etat.valeurs["veille.dernier"] = str(time.time() - 6 * 24 * 3600)
    assert automation._veille_due() is False, "six jours ont suffi"
    etat.valeurs["veille.dernier"] = str(time.time() - 8 * 24 * 3600)
    assert automation._veille_due() is True, "huit jours n'ont pas suffi"


def test_l_intervalle_reste_reglable_sans_redeploiement(etat, monkeypatch):
    """Le défaut est hebdomadaire, mais la valeur reste une DÉCISION
    d'exploitation : la remettre à six heures ne doit pas demander de toucher
    au code."""
    monkeypatch.setenv("VEILLE_INTERVAL_HOURS", "6")
    etat.valeurs["veille.dernier"] = str(time.time() - 7 * 3600)
    assert automation._veille_due() is True, "l'intervalle réglé n'est pas lu"


# ══════════════════════════════════════════════════════════════════════════
# 2. LES TROIS FAÇONS DONT « UNE FOIS PAR SEMAINE » CESSE D'ÊTRE VRAI
# ══════════════════════════════════════════════════════════════════════════

def test_un_redemarrage_ne_relance_pas_la_collecte(etat):
    """LE DÉFAUT QUE TOUT CECI CORRIGE. Le planificateur vit en mémoire et
    repart à `now + 180 s` à chaque démarrage. Si la décision dépendait de lui,
    chaque déploiement collecterait — plusieurs fois par jour certains jours.
    Rejouer `_register_jobs()`, c'est exactement ce que fait un redémarrage."""
    etat.valeurs["veille.dernier"] = str(time.time() - 3600)
    automation._register_jobs()
    assert automation._veille_due() is False, (
        "un redémarrage relance la collecte : la cadence ne tient pas")


def test_le_reveil_est_bien_plus_frequent_que_la_cadence():
    """Un réveil aussi espacé que la cadence REPORTERAIT la collecte à chaque
    arrêt : trois jours d'indisponibilité, et le passage suivant tomberait trois
    jours plus tard — indéfiniment. Le rattrapage n'est possible que si le
    travail se réveille souvent et se garde lui-même."""
    automation._register_jobs()
    veille = [j for j in automation._JOBS if j["name"] == "veille"]
    assert len(veille) == 1, [j["name"] for j in automation._JOBS]
    assert veille[0]["every"] <= 3600, (
        "le réveil est espacé de %d s : un arrêt décalerait la collecte "
        "définitivement" % veille[0]["every"])
    code = _corps("_register_jobs")
    assert "VEILLE_INTERVAL_HOURS" not in code, (
        "le réveil est de nouveau dérivé de la cadence : les deux ne sont plus "
        "distincts\n%s" % code)


def test_un_passage_interrompu_est_retente_et_non_compte_comme_fait(etat, monkeypatch):
    """L'horodatage s'écrit APRÈS la collecte. L'écrire avant compterait comme
    faite une semaine qui a échoué — et il faudrait attendre la suivante pour
    s'en apercevoir."""
    etat.valeurs["veille.dernier"] = str(time.time() - SEMAINE - 60)

    def _echoue():
        raise RuntimeError("le réseau a lâché")

    monkeypatch.setattr(automation, "veille_refresh", _echoue)
    with pytest.raises(RuntimeError):
        automation.job_veille()
    assert etat.ecritures == [], (
        "un passage échoué a été horodaté : la collecte attendrait une semaine "
        "de plus")
    assert automation._veille_due() is True


# ══════════════════════════════════════════════════════════════════════════
# 3. CE QUI RESTE HORS CADENCE, ET DÉLIBÉRÉMENT
# ══════════════════════════════════════════════════════════════════════════

def test_une_collecte_reussie_est_horodatee(etat, monkeypatch):
    """Le témoin positif de la règle précédente : ne jamais horodater
    satisfait « pas d'horodatage sur échec » et casse la cadence entière."""
    etat.valeurs["veille.dernier"] = str(time.time() - SEMAINE - 60)
    monkeypatch.setattr(automation, "veille_refresh", lambda: 3)
    automation.job_veille()
    assert [c for c, _ in etat.ecritures] == ["veille.dernier"], etat.ecritures
    assert automation._veille_due() is False


def test_la_relance_manuelle_ignore_la_cadence(etat, monkeypatch):
    """DÉCISION DÉLIBÉRÉE, ÉCRITE POUR QU'ON NE LA « CORRIGE » PAS. Le bouton
    de `/admin` appelle `veille_refresh` DIRECTEMENT — jamais `job_veille` —
    parce qu'il sert à diagnostiquer : un bouton qui répondrait « revenez dans
    six jours » ne servirait à rien le jour où l'on cherche pourquoi la page
    est vide.

    La règle lit l'appel de l'application, pas un commentaire à son sujet.
    """
    app_py = io.open(os.path.join(ICI, "app.py"), encoding="utf-8").read()
    i = app_py.index("def api_veille_refresh(")
    j = app_py.find("\n@app.route", i)
    route = app_py[i:j if j > 0 else len(app_py)]
    assert "automation.veille_refresh()" in route, route
    assert "job_veille" not in route, (
        "la relance manuelle passe par la garde hebdomadaire : le bouton de "
        "diagnostic ne diagnostique plus rien\n%s" % route)


def test_un_etat_absent_declenche_une_collecte(etat):
    """Au tout premier démarrage, ou après une base remise à neuf, il n'y a
    rien à comparer. Attendre une semaine par prudence laisserait une page vide
    sept jours durant — pour se conformer à une cadence qu'on ne mesure pas."""
    assert etat.get("veille.dernier") is None
    assert automation._veille_due() is True
    for illisible in ("", "bientôt", "NaN"):
        etat.valeurs["veille.dernier"] = illisible
        assert automation._veille_due() is True, (
            "un horodatage illisible (%r) empêche toute collecte" % illisible)
