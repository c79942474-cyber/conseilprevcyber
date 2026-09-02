"""Conformité mesurée : les contrôles MESURENT — et refusent d'inventer.

CE QUE CES TESTS PROTÈGENT. Le dossier de conformité de ce site était
entièrement déclaratif : huit « en place » écrits à la main dans rgpd.ART50,
et une politique de confidentialité qui promet un tableau « qui ne peut pas
diverger » du référentiel — alors qu'il diverge (6 lignes publiées, 10
traitements). Le module conformite_mesures relit l'état réel à chaque appel.

Ces tests prouvent trois choses, dans cet ordre :
  1. l'INVARIANT — un verdict « conforme » sans mesure est rétrogradé par le
     code, pas par la discipline du relecteur ;
  2. chaque mesure DISCRIMINE — la même mesure, servie d'un état dégradé,
     tombe ;
  3. les divergences réelles du dépôt sont VUES — tant qu'elles existent, les
     contrôles les nomment ; ces tests documentent l'état constaté et
     tomberont le jour où l'arbitrage sera rendu, pour être mis à jour avec
     lui.
"""
import io
import os
import sys
import zipfile

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import conformite_mesures as cm  # noqa: E402
import rgpd  # noqa: E402


# ── 1. L'invariant ─────────────────────────────────────────────────────────

def test_un_conforme_sans_mesure_est_retrograde():
    """LE POINT QUI DÉCIDE : l'invariant vit dans le code. Quiconque écrira un
    contrôle « conforme » en mode attestation obtiendra un non-mesure — pas
    un vert."""
    c = cm._ctl('essai', 'RGPD', 'essai', 'attestation', 'conforme', 'declare')
    assert c['statut'] == 'non-mesure'
    assert 'INVARIANT' in c['constat']


def test_un_conforme_mesure_passe():
    c = cm._ctl('essai', 'RGPD', 'essai', 'mesure', 'conforme', 'lu sur l etat')
    assert c['statut'] == 'conforme'


# ── 2. Les mesures discriminent ────────────────────────────────────────────

def test_la_mention_de_l_assistant_est_mesuree():
    c = cm._m_mention_assistant()
    assert c['mode'] == 'mesure'
    assert c['statut'] == 'conforme', c['constat']


def test_la_mention_amputee_tombe(tmp_path, monkeypatch):
    """La même mesure, servie d'un fichier sans la mention, doit tomber :
    une mesure qui dit conforme aux deux ne mesure rien."""
    page = open(os.path.join(ICI, 'assistant.html'), encoding='utf-8').read()
    ampute = page.replace('intelligence artificielle', 'assistant documentaire')
    (tmp_path / 'assistant.html').write_text(ampute, encoding='utf-8')
    monkeypatch.setattr(cm, 'ICI', str(tmp_path))
    c = cm._m_mention_assistant()
    assert c['statut'] == 'non-conforme', c['constat']


def test_le_marquage_des_exports_est_genere_puis_lu():
    c = cm._m_marquage_exports()
    assert c['mode'] == 'mesure'
    assert c['statut'] == 'conforme', c['constat']
    assert 'docProps/core.xml' in c['constat']


def test_un_fichier_absent_est_non_mesure_pas_vert(monkeypatch, tmp_path):
    monkeypatch.setattr(cm, 'ICI', str(tmp_path))     # répertoire vide
    c = cm._m_mention_assistant()
    assert c['statut'] == 'non-mesure'
    c2 = cm._m_derive_registre(rgpd)
    assert c2['statut'] == 'non-mesure'


def test_les_traceurs_tiers_discriminent(tmp_path, monkeypatch):
    (tmp_path / 'propre.html').write_text('<html>rien</html>', encoding='utf-8')
    monkeypatch.setattr(cm, 'ICI', str(tmp_path))
    assert cm._m_traceurs_tiers()['statut'] == 'conforme'
    (tmp_path / 'sale.html').write_text('<script>gtag("init")</script>', encoding='utf-8')
    c = cm._m_traceurs_tiers()
    assert c['statut'] == 'non-conforme'
    assert 'sale.html' in c['constat']


# ── 3. Les divergences réelles du dépôt sont vues ──────────────────────────

def test_la_derive_du_registre_publie_est_vue():
    """CONSTAT DU JOUR : la politique de confidentialité publie 6 lignes pour
    10 traitements au référentiel, en promettant qu'elle « ne peut pas
    diverger ». Tant que la page n'est pas rendue dynamique, ce contrôle doit
    le dire. Le jour où elle le sera, ce test tombera — c'est voulu : il
    devra alors affirmer « conforme », et le contrôle continuera de garder
    la page contre une nouvelle dérive."""
    c = cm._m_derive_registre(rgpd)
    assert c['statut'] == 'non-conforme', c['constat']
    assert 'diverger' in c['constat']
    assert c['correction']


def test_l_assistant_sans_compte_ne_se_contredit_plus():
    """LA CONTRADICTION A ÉTÉ TRANCHÉE, ET DANS LE SENS DU REGISTRE.

    Le registre publié affirmait « Aucun compte requis » pendant que
    /assistant et /api/chat exigeaient une connexion : la base légale publiée —
    consentement par l'usage volontaire, sans compte — reposait sur un fait
    inexact. Le contrôle le disait et refusait de trancher, parce qu'ouvrir
    l'assistant ou corriger le registre est une décision humaine. Elle a été
    prise le 2 septembre 2026, en ouvrant le site : le registre dit vrai.

    LA RÈGLE NE FIGE AUCUN DES DEUX ÉTATS. Elle exigeait « non-conforme » —
    elle serait donc tombée le jour de la correction, en désignant un défaut à
    l'instant où il disparaissait. Elle vérifie la PROPRIÉTÉ : déclaration et
    code concordent, et le contrôle a bien REGARDÉ les deux — sans quoi il
    serait vert par omission."""
    import app as application
    c = cm._m_assistant_sans_compte(application.app)
    assert c['statut'] == 'conforme', c['constat']
    import rgpd
    fiche = next(r for r in rgpd.REGISTRE if r.get("id") == "assistant")
    assert "Aucun compte requis" in str(fiche), (
        "le registre ne déclare plus rien : le contrôle serait vert pour rien")
    import acces as _acces
    assert _acces.ouvert("/assistant")
    assert _acces.api_statut("/api/chat") == "direct"


def test_les_routes_admin_sont_inspectees_sur_la_carte():
    import app as application
    c = cm._m_routes_admin_gardees(application.app)
    assert c['mode'] in ('mesure', 'arbitrage')
    # Le verdict depend de l'etat reel ; ce qui est garanti, c'est que le
    # controle a VU la carte des routes et non une liste recopiee.
    assert c['statut'] in ('conforme', 'non-conforme'), c['constat']


def test_art50_reste_une_attestation():
    c = cm._m_art50_attestations(rgpd)
    assert c['mode'] == 'attestation'
    assert c['statut'] == 'atteste'
    assert 'DÉCLARATIONS' in c['constat']


# ── 4. L'état complet ──────────────────────────────────────────────────────

def test_l_etat_sert_les_quatre_comptes_et_jamais_un_score_seul():
    import app as application
    e = cm.etat(application.clients_db, application.app)
    assert 'controles' in e and len(e['controles']) >= 8
    c = e['comptes']
    assert set(c) >= {'mesures', 'mesures_conformes', 'non_conformes',
                      'arbitrages', 'attestations', 'non_mesures'}
    # Aucun champ « score » : le pourcentage seul est exactement ce que la
    # doctrine interdit de servir.
    assert 'score' not in e
    for ctl in e['controles']:
        if ctl['statut'] == 'conforme':
            assert ctl['mode'] == 'mesure', (
                'un conforme non mesuré a traversé : %r' % ctl)
