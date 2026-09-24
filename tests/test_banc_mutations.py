# -*- coding: utf-8 -*-
"""Le banc de mutations est dans le dépôt, et ses tables restent JOUABLES.

CE QUI MANQUAIT ICI. Deux tables `tests/mutations_*.json` vivaient dans ce
dépôt (maturité OT, veille des chiffres), et `test_veille_chiffres.py` vérifie
lui-même les ancres de la sienne — mais le script qui les REJOUE n'y était
pas : personne d'autre que leur auteur ne pouvait vérifier qu'une règle tombe
bien sur SON défaut. Le banc est `outils/muter.py`, le même que celui de
conseilprev, et ces règles gardent ce qu'il a fallu y mesurer :
  · une ancre devenue ambiguë (présente deux fois) rendait une mutation
    inexécutable sans qu'aucune règle ne tombe ;
  · un banc interrompu laissait un fichier du dépôt MUTÉ sur le disque ;
  · une modification faite pendant la batterie aurait été écrasée par la
    restauration ;
  · les lignes « ERROR » du journal capturé étaient comptées comme des
    règles tombées.
"""
import glob
import importlib.util
import io
import json
import os

import pytest

_RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _charger_banc():
    spec = importlib.util.spec_from_file_location(
        "muter", os.path.join(_RACINE, "outils", "muter.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


banc = _charger_banc()
TABLES = sorted(os.path.relpath(p, _RACINE)
                for p in glob.glob(os.path.join(_RACINE, "tests", "mutations_*.json")))


# ══════════════════════════════════════════════════════════════════════════
#  1. CHAQUE TABLE DU DÉPÔT EST JOUABLE — À CHAQUE PASSAGE DE LA SUITE
# ══════════════════════════════════════════════════════════════════════════

def test_le_releve_des_tables_n_est_pas_vide():
    assert len(TABLES) >= 3, TABLES


@pytest.mark.parametrize("table", TABLES, ids=[os.path.basename(t)[10:-5] for t in TABLES])
def test_chaque_table_est_JOUABLE(table):
    """UNE ANCRE DOUBLE, UNE RÈGLE DISPARUE : la mutation ne tomberait plus
    sur rien, et la batterie ne le dirait qu'à qui la relance. La suite, elle,
    passe à chaque modification."""
    fautes = banc.verifier(os.path.join(_RACINE, table))
    assert not fautes, "%s :\n  %s" % (table, "\n  ".join(fautes))


# ══════════════════════════════════════════════════════════════════════════
#  2. CE QUE LA VÉRIFICATION REFUSE
# ══════════════════════════════════════════════════════════════════════════

def _depot(tmp_path, source="VALEUR = 1\nAUTRE = 2\n"):
    (tmp_path / "tests").mkdir()
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    (tmp_path / "tests" / "test_mod.py").write_text(
        "def test_valeur():\n    pass\n\ndef test_autre():\n    pass\n",
        encoding="utf-8")
    return str(tmp_path)


def _table(*mutations):
    return {"cibles": ["tests/test_mod.py"], "mutations": [
        dict(nom="m%d" % i, fichier="mod.py", **m) for i, m in enumerate(mutations)]}


def test_une_ANCRE_double_est_une_faute(tmp_path):
    racine = _depot(tmp_path, "X = 1\nX = 1\n")
    fautes = banc.verifier(_table({"avant": "X = 1", "apres": "X = 2",
                                   "regle": "test_valeur"}), racine)
    assert any("présente 2 fois" in f for f in fautes), fautes


def test_une_ANCRE_absente_est_une_faute(tmp_path):
    racine = _depot(tmp_path)
    fautes = banc.verifier(_table({"avant": "INTROUVABLE", "apres": "X",
                                   "regle": "test_valeur"}), racine)
    assert any("présente 0 fois" in f for f in fautes), fautes


def test_une_REGLE_inconnue_est_une_faute(tmp_path):
    racine = _depot(tmp_path)
    fautes = banc.verifier(_table({"avant": "VALEUR = 1", "apres": "VALEUR = 3",
                                   "regle": "test_disparu[cas]"}), racine)
    assert any("test_disparu" in f and "aucune cible" in f for f in fautes), fautes


def test_une_table_SAINE_passe(tmp_path):
    racine = _depot(tmp_path)
    assert banc.verifier(_table({"avant": "VALEUR = 1", "apres": "VALEUR = 3",
                                 "regle": "test_valeur[x]"}), racine) == []


# ══════════════════════════════════════════════════════════════════════════
#  3. LE BANC DISTINGUE, ET REMET TOUJOURS LE FICHIER EN ÉTAT
# ══════════════════════════════════════════════════════════════════════════

def _lanceur_selon(racine, reponses):
    """Un faux pytest : il lit mod.py et répond selon ce qu'il y trouve."""
    def lanceur(_cibles):
        src = io.open(os.path.join(racine, "mod.py"), encoding="utf-8").read()
        for motif, sortie in reponses:
            if motif in src:
                return sortie
        return "2 passed in 0.01s"
    return lanceur


def test_le_banc_distingue_TOMBE_SURVIT_et_MAL_VISEE(tmp_path):
    racine = _depot(tmp_path)
    table = _table(
        {"avant": "VALEUR = 1", "apres": "VALEUR = 9", "regle": "test_valeur"},
        {"avant": "AUTRE = 2", "apres": "AUTRE = 8", "regle": "test_autre"},
        {"avant": "VALEUR = 1", "apres": "VALEUR = 7", "regle": "test_valeur"})
    lanceur = _lanceur_selon(racine, [
        ("VALEUR = 9", "FAILED tests/test_mod.py::test_valeur - x\n1 failed"),
        ("VALEUR = 7", "FAILED tests/test_mod.py::test_autre - x\n1 failed")])
    lignes = []
    survit, mal, fautes = banc.jouer(table, racine, lanceur, lignes.append)
    assert (survit, mal, fautes) == (1, 1, []), lignes
    assert any("tombe" in l and "m0" in l for l in lignes), lignes
    assert io.open(os.path.join(racine, "mod.py"), encoding="utf-8").read() \
        == "VALEUR = 1\nAUTRE = 2\n", "le fichier n'est pas remis en état"


def test_un_banc_INTERROMPU_remet_le_fichier_en_etat(tmp_path):
    """Un arrêt pendant une mutation laisserait un fichier du dépôt muté. La
    restauration se fait dans `finally`, et sur SIGINT/SIGTERM."""
    racine = _depot(tmp_path)

    def lanceur(_c):
        src = io.open(os.path.join(racine, "mod.py"), encoding="utf-8").read()
        if "VALEUR = 9" in src:
            raise KeyboardInterrupt
        return "2 passed in 0.01s"
    with pytest.raises(KeyboardInterrupt):
        banc.jouer(_table({"avant": "VALEUR = 1", "apres": "VALEUR = 9",
                           "regle": "test_valeur"}), racine, lanceur, lambda l: None)
    assert io.open(os.path.join(racine, "mod.py"), encoding="utf-8").read() \
        == "VALEUR = 1\nAUTRE = 2\n"


def test_une_modification_PENDANT_la_batterie_n_est_pas_ecrasee(tmp_path):
    """LE RISQUE : on corrige un fichier pendant que la batterie tourne.
    Restaurer la copie prise avant la mutation effacerait la correction. Seule
    la mutation est défaite."""
    racine = _depot(tmp_path)
    chemin = os.path.join(racine, "mod.py")

    def lanceur(_c):
        src = io.open(chemin, encoding="utf-8").read()
        if "VALEUR = 9" in src:
            io.open(chemin, "w", encoding="utf-8").write(src + "AJOUT = 3\n")
            return "FAILED tests/test_mod.py::test_valeur - x\n1 failed"
        return "2 passed in 0.01s"
    banc.jouer(_table({"avant": "VALEUR = 1", "apres": "VALEUR = 9",
                       "regle": "test_valeur"}), racine, lanceur, lambda l: None)
    assert io.open(chemin, encoding="utf-8").read() == \
        "VALEUR = 1\nAUTRE = 2\nAJOUT = 3\n"


def test_une_erreur_de_COLLECTE_est_une_chute_pas_une_survie():
    """UN MODULE QUI NE SE CHARGE PLUS : lire l'erreur de collecte comme une
    survie obligerait à viser la garde d'import au lieu du défaut."""
    sortie = ("ERROR tests/test_mod.py - RuntimeError: garde\n"
              "FAILED tests/test_x.py::test_y[z] - assert\n")
    assert banc.tombees(sortie) == ["test_y[z]", "tests/test_mod.py"]


def test_une_ligne_de_JOURNAL_n_est_pas_une_chute():
    """Les lignes « ERROR » du journal capturé — l'alignement du niveau, puis
    le nom du journal — ne sont pas des règles tombées ; le résumé, lui, met
    UNE espace après le mot, puis le fichier de règles."""
    sortie = ("----------------------------- Captured log call ---------\n"
              "ERROR    auth:auth.py:648 BREVO_API_KEY absente — email non envoyé\n"
              "ERROR    app:app.py:76 FLASK_SECRET_KEY absente - repli\n"
              "=================== short test summary info ============\n"
              "FAILED tests/test_x.py::test_y[z] - assert\n")
    assert banc.tombees(sortie) == ["test_y[z]"]


def test_une_BASE_rouge_ne_joue_rien(tmp_path):
    racine = _depot(tmp_path)
    lignes = []
    s, m, fautes = banc.jouer(
        _table({"avant": "VALEUR = 1", "apres": "VALEUR = 9", "regle": "test_valeur"}),
        racine, lambda _c: "FAILED tests/test_mod.py::test_valeur\n1 failed",
        lignes.append)
    assert fautes == ["base non verte"], lignes
    assert io.open(os.path.join(racine, "mod.py"), encoding="utf-8").read() \
        == "VALEUR = 1\nAUTRE = 2\n"
