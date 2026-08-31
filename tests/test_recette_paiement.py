# -*- coding: utf-8 -*-
"""La recette de paiement doit échouer bruyamment, et ne rien abîmer.

POURQUOI CES RÈGLES EXISTENT. Deux mutations ont survécu à la première campagne
— retirer la sortie en erreur après un échec d'étape, et retirer le refus sur
une clé de production — parce qu'aucune ne se voyait tant que TOUTES les étapes
passaient. Un script de recette dont les gardes n'ont pas de règle est un script
dont on découvrira le jour venu qu'il rassurait.
"""
import io
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.join(ICI, "outils"))

import auth                                                        # noqa: E402
import paiement                                                    # noqa: E402
import recette_paiement as R                                       # noqa: E402


def test_une_etape_en_echec_termine_la_recette_en_erreur(capsys):
    """UNE RECETTE QUI CONTINUE APRÈS UN ÉCHEC FINIT PAR SE LIRE COMME UN
    SUCCÈS. L'étape fautive doit arrêter la course, et le code de sortie doit
    le dire à qui l'appelle depuis un enchaînement."""
    R._ETAT.update({"n": 3, "echecs": 0, "simule": False})
    with pytest.raises(SystemExit) as sortie:
        R.echec("quelque chose ne va pas", "et il faut s'arrêter")
    assert sortie.value.code == 1
    texte = capsys.readouterr().out
    assert "quelque chose ne va pas" in texte
    assert "ÉCHOUÉE à l'étape 3" in texte


def test_une_etape_reussie_ne_termine_rien(capsys):
    """La règle doit DISCRIMINER : s'arrêter à chaque étape la satisferait
    aussi."""
    R._ETAT.update({"n": 1, "echecs": 0})
    R.verifier(True, "tout va bien")
    assert "✓ tout va bien" in capsys.readouterr().out


def test_la_recette_refuse_de_s_executer_sur_une_cle_de_production(monkeypatch, capsys):
    """ON NE FAIT PAS DE RECETTE EN PRODUCTION. Ce script crée un compte, ouvre
    une caisse et ouvre un accès : sur une clé « sk_live_ », il doit s'arrêter
    avant tout, et n'avoir rien créé."""
    monkeypatch.setenv(paiement.CLE, "sk_live_factice")
    monkeypatch.setenv(paiement.CLE_WEBHOOK, "whsec_factice")
    monkeypatch.setenv(paiement.CLE_PRIX, "price_factice")
    assert R.main() == 2
    texte = capsys.readouterr().out
    assert "CLÉ DE PRODUCTION" in texte
    assert auth.store.get(R.ACHETEUR) is None, "un compte a été créé malgré le refus"


def test_le_mode_simule_se_declare_en_pied(capsys):
    """Un mode simulé présenté comme une recette complète serait le seul vrai
    échec de ce script : tout ce qui précède l'appel à Stripe est éprouvé,
    l'appel lui-même ne l'est pas."""
    R._ETAT.update({"n": 11, "echecs": 0, "simule": True})
    assert R._fin(0) == 0
    texte = capsys.readouterr().out
    assert "SEGMENT STRIPE N'A PAS ÉTÉ JOUÉ" in texte
    assert "sk_test" in texte

    R._ETAT["simule"] = False
    R._fin(0)
    assert "SEGMENT STRIPE" not in capsys.readouterr().out


def test_la_caisse_simulee_garde_ce_qu_on_lui_passe():
    """L'intérêt du faux SDK n'est pas de rendre une URL : c'est de pouvoir
    relire les arguments transmis. Une caisse ouverte en « subscription », ou
    sans compte lié, encaisserait sans rien ouvrir — et la valeur de retour ne
    le dirait pas."""
    faux = R._CaisseSimulee()
    faux.checkout.Session.create(mode="payment", client_reference_id="x@y.test")
    assert faux.appels[-1]["mode"] == "payment"
    assert faux.appels[-1]["client_reference_id"] == "x@y.test"


def test_le_signeur_de_la_recette_produit_une_signature_acceptee(monkeypatch):
    """Si le signeur du script ne signait pas juste, ses étapes 7 et 10
    éprouveraient le vide."""
    for nom in (paiement.CLE, paiement.CLE_WEBHOOK, paiement.CLE_PRIX):
        monkeypatch.setenv(nom, "recette")
    charge, entete = R._signer(R._evenement("x@y.test"), "recette")
    assert paiement.lire_evenement(charge, entete) is not None
    _, faux = R._signer(R._evenement("x@y.test"), "un.autre.secret")
    assert paiement.lire_evenement(charge, faux) is None
