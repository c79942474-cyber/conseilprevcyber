# -*- coding: utf-8 -*-
"""UNE DÉCISION INVENTÉE A EXACTEMENT LA FORME D'UNE VRAIE.

Le module `librejustice` sait dire qu'une décision citée ne figurait pas dans
celles qu'on a montrées au modèle. Cela ne sert à rien si la page ne le dit pas
au lecteur — et une référence de texte inventée n'a pas la même gravité qu'une
décision inventée : la première se vérifie sur EUR-Lex en trente secondes, la
seconde porte une chambre, une date et un numéro de pourvoi de la bonne forme,
et rien ne la distingue d'une vraie sans aller la chercher.

CES RÈGLES EXÉCUTENT LE CODE SERVI, elles ne le lisent pas. Chercher
« rel="noopener" » dans le fichier est satisfait par un commentaire, et ce dépôt
s'est déjà fait prendre à ce jeu.
"""
import io
import json
import os
import re
import shutil
import subprocess

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = io.open(os.path.join(ICI, 'juridique.html'), encoding='utf-8').read()
NODE = shutil.which('node')

PRELUDE = ('esc', 'PUBLICATION', 'SOLUTION', 'codeLisible',
           'ord', 'creneau', 'chambre', 'rendreJurisprudence',
           'rendreCorpusMuet', 'rendreDecisions')


def _extraire(nom):
    """Une déclaration de la page, fonction ou objet, telle qu'elle est écrite.

    On borne à l'ACCOLADE DE MÊME INDENTATION plutôt que de compter les
    accolades : « /^[A-ZÉÈÀÇ]{4,}$/ » en contient deux dans une quantification
    d'expression rationnelle, et un compteur naïf s'y perd."""
    if nom.isupper():
        d = PAGE.index('var %s={' % nom)
        return PAGE[d:PAGE.index('\n    };', d) + 6]
    for ouverture in ('function %s(' % nom, 'var %s = function(' % nom,
                      'var %s=function(' % nom):
        d = PAGE.find(ouverture)
        if d >= 0:
            return PAGE[d:PAGE.index('\n    }', d) + 6]
    raise AssertionError('déclaration « %s » introuvable dans juridique.html' % nom)


def _evaluer(expression):
    if not NODE:
        pytest.skip('node absent : le rendu ne peut pas être évalué')
    src = '\n'.join(_extraire(n) for n in PRELUDE)
    prog = src + '\nconsole.log(JSON.stringify(%s));' % expression
    r = subprocess.run([NODE, '-e', prog], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        pytest.fail('%s ne s\'évalue pas :\n%s' % (expression, (r.stderr or '')[-1500:]))
    return json.loads(r.stdout)


def _rendre(appel, *arguments):
    args = ', '.join(json.dumps(a, ensure_ascii=False) for a in arguments)
    return _evaluer('%s(%s)' % (appel, args))


DECISION = {
    "titre": "Cour de cassation, Chambre commerciale, 22 octobre 1996",
    "url": "https://librejustice.fr/decision/cc-1996-10-22",
    "juridiction": "Cour de cassation", "chambre": "COMMERCIALE",
    "date": "1996-10-22", "numero": "93-18.632",
    "publication": "PUBLIE_BULLETIN", "solution": "CASSATION",
    "sort": "CONFIRMATION — confirmée le 9 juillet 2002",
}


# ── L'ALERTE ─────────────────────────────────────────────────────────────

def test_une_decision_hors_liste_est_signalee_comme_inexistante():
    """« Non reconnue » invite à vérifier, et personne ne vérifie. Le lecteur
    doit savoir qu'il n'y a rien à vérifier : la décision n'existe pas."""
    h = _rendre('rendreJurisprudence',
                {"ok": False, "suspectes": [{"type": "pourvoi", "cle": "9999999"}],
                 "montrees": 2})
    assert '9999999' in h
    assert 'INEXISTANTES' in h


def test_l_approbation_ne_s_affiche_pas_sans_decision_rapportee():
    """UN FAUX TÉMOIGNAGE DE VÉRIFICATION. La plupart des analyses n'auront
    aucune jurisprudence — les textes en cause datent de 2024."""
    assert _rendre('rendreJurisprudence', {"ok": True, "suspectes": [], "montrees": 0}) == ''


def test_l_approbation_ne_promet_pas_ce_qu_elle_ne_verifie_pas():
    h = _rendre('rendreJurisprudence', {"ok": True, "suspectes": [], "montrees": 3})
    assert h and 'lisez-la' in h


# ── LES DÉCISIONS AFFICHÉES ──────────────────────────────────────────────

def test_chaque_decision_est_liee_a_sa_source():
    h = _rendre('rendreDecisions', [DECISION])
    assert 'href="https://librejustice.fr/decision/cc-1996-10-22"' in h
    assert '93-18.632' in h


def test_les_decisions_ne_sont_pas_rendues_dans_le_conteneur_a_pastilles():
    """LA CSS DÉCIDE DE LA MISE EN PAGE, PAS L'INTENTION. `.srcs` est un
    conteneur flex à pastilles ; un titre et des retours de ligne placés dedans
    deviennent des éléments flex distincts et la liste se disloque."""
    h = _rendre('rendreDecisions', [DECISION])
    assert 'class="srcs"' not in h
    for classe in re.findall(r'class="(jur[a-z-]*)"', h):
        assert '.%s{' % classe in PAGE or '.%s ' % classe in PAGE, (
            "la classe « %s » est employée mais n'est stylée nulle part" % classe)


def test_la_reserve_accompagne_les_decisions():
    assert 'décision cassée ne dit plus rien' in _rendre('rendreDecisions', [DECISION])


def test_le_sort_de_la_decision_est_affiche():
    """Une décision infirmée ne fonde rien. Ne pas l'afficher revient à
    présenter comme autorité ce qui n'en est plus une."""
    h = _rendre('rendreDecisions', [DECISION])
    assert 'Sort de cette décision' in h and 'confirmée' in h


def test_aucune_decision_aucune_liste_de_decisions():
    """Sans décision, aucune LISTE ne doit paraître — c'est ce que cette règle
    a toujours défendu, et elle le défend encore.

    CE QU'ELLE NE DÉFEND PLUS : le silence complet. Elle exigeait une chaîne
    vide, et cela masquait une distinction qui compte. Une liste vide a deux
    causes qui ne se soignent pas pareil — le corpus a répondu et ne connaît
    rien, ou le corpus n'a pas répondu du tout. Ne rien dire faisait passer une
    panne de raccordement pour un fait juridique : « il n'existe pas de
    jurisprudence sur cette question »."""
    for vide in ([], None):
        for etat in (None, {"ok": True}, {"ok": False, "motif": "corpus fermé"}):
            h = _rendre('rendreDecisions', vide, etat)
            assert '[J1]' not in h and '<ol>' not in h, (vide, etat)


def test_sans_etat_du_corpus_la_page_se_tait():
    """Ne rien savoir n'autorise pas à conclure. Tant que l'appelant ne dit pas
    ce qu'a fait le corpus, la page n'invente aucune explication."""
    assert _rendre('rendreDecisions', [], None) == ''


def test_un_corpus_injoignable_est_annonce_avec_son_motif():
    """LA DISTINCTION QUI COMPTE. Une analyse produite sans jurisprudence parce
    que le corpus est fermé n'est pas une analyse qui conclut à l'absence de
    jurisprudence — et le lecteur est le seul à pouvoir en tirer les
    conséquences."""
    h = _rendre('rendreDecisions', [],
                {"ok": False, "motif": "exige une autorisation OAuth 2.1"})
    assert 'SANS jurisprudence' in h
    assert 'exige une autorisation OAuth 2.1' in h
    assert "n'est pas affecté" in h, (
        "le lecteur doit savoir que la qualification réglementaire, elle, "
        "tient toujours")


def test_un_corpus_interroge_et_muet_le_dit_autrement():
    h = _rendre('rendreDecisions', [], {"ok": True})
    assert 'aucune décision' in h
    assert 'SANS jurisprudence' not in h, (
        "un corpus qui a répondu est présenté comme injoignable")


def test_le_motif_du_corpus_est_echappe():
    """Le motif vient d'un service tiers et transite par un message
    d'exploitation : il entre dans la page comme du texte, jamais comme du
    balisage."""
    h = _rendre('rendreDecisions', [],
                {"ok": False, "motif": "<img src=x onerror=alert(1)>"})
    assert '<img' not in h and '&lt;img' in h


# ── LE VOCABULAIRE DU LECTEUR, PAS CELUI DU RÉFÉRENTIEL ─────────────────

@pytest.mark.parametrize('code,attendu', [
    ('INEDIT_BULLETIN', 'ne fait pas jurisprudence'),
    ('INEDIT_LEBON', 'ne fait pas jurisprudence'),
    ('PUBLIE_BULLETIN', 'publiée au Bulletin'),
    ('PUBLIE_RAPPORT', 'portée maximale'),
])
def test_la_publication_est_dite_en_francais_avec_sa_portee(code, attendu):
    """« INEDIT_BULLETIN » n'est pas seulement du jargon : c'est l'information
    la plus utile de la ligne, et un sigle en majuscules l'escamote.

    CONTRÔLÉ SUR LA TRADUCTION ELLE-MÊME. Une mutation qui vidait « inédite —
    ne fait pas jurisprudence » de sa portée a survécu dans le dépôt jumeau : la
    réserve, trois lignes plus bas, porte déjà « une décision non publiée ne fait
    pas jurisprudence ». La règle lisait la réserve et croyait lire la
    traduction."""
    traduit = _evaluer('codeLisible(%s, PUBLICATION)' % json.dumps(code))
    assert attendu in traduit, "« %s » se traduit « %s »" % (code, traduit)
    h = _rendre('rendreDecisions', [dict(DECISION, publication=code)])
    assert code not in h and traduit in h


def test_la_solution_est_dite_en_francais():
    h = _rendre('rendreDecisions', [dict(DECISION, solution='CASSATION_PARTIELLE')])
    assert 'cassation partielle' in h and 'CASSATION_PARTIELLE' not in h


def test_un_code_inconnu_est_rendu_lisible_et_non_masque():
    h = _rendre('rendreDecisions', [dict(DECISION, solution='SURSIS_A_STATUER')])
    assert 'sursis a statuer' in h and 'SURSIS_A_STATUER' not in h


@pytest.mark.parametrize('cle,attendu', [
    ('COMMERCIALE', 'chambre commerciale'),
    ('SOCIALE', 'chambre sociale'),
    ('P5.C4', 'pôle 5, 4e chambre'),
    ('P5.C1', 'pôle 5, 1re chambre'),
    ('SC4.C6', '4e section, 6e chambre'),
    ('CD', 'chambre D'),
    ('C4-7', 'chambre 4-7'),
    ('S1', '1re section'),
    ('LB', 'section B'),
    ('Q1-4', 'sous-sections 1/4 réunies'),
    ('R3-8', 'chambres 3/8 réunies'),
])
def test_la_formation_est_dite_en_clair(cle, attendu):
    """« P5.C4 » n'est pas une formation, c'est une clé."""
    assert _rendre('chambre', cle) == attendu
    # ET LE RENDU S'EN SERT : traduire une valeur que personne n'affiche ne sert
    # à rien, et la mutation correspondante a survécu tant que cette seconde
    # assertion manquait.
    assert attendu in _rendre('rendreDecisions', [dict(DECISION, chambre=cle)])


@pytest.mark.parametrize('inconnu', ['XZ9', 'FORMATION-PLENIERE', 'W12-3'])
def test_un_creneau_non_documente_passe_tel_quel(inconnu):
    """INVENTER UNE LECTURE SERAIT PIRE QUE DE NE PAS LIRE. Une formation
    fabriquée sur une décision de justice est une erreur de fond ; une clé brute
    n'est qu'une gêne."""
    assert _rendre('chambre', inconnu) == inconnu


# ── L'ADRESSE NE DOIT PAS POUVOIR EXÉCUTER DE CODE ──────────────────────

@pytest.mark.parametrize('adresse', [
    'javascript:alert(1)', 'JaVaScRiPt:alert(1)',
    'data:text/html,<script>alert(1)</script>', 'vbscript:msgbox(1)',
])
def test_une_adresse_qui_n_est_pas_http_n_est_pas_rendue_cliquable(adresse):
    """ÉCHAPPER PROTÈGE DU BALISAGE, PAS DU SCHÉMA. Les adresses viennent d'un
    service tiers : on n'ouvre que http et https."""
    h = _rendre('rendreDecisions', [dict(DECISION, url=adresse)])
    assert '<a ' not in h, "une adresse « %s » a été rendue cliquable" % adresse
    assert 'Chambre commerciale' in h, "l'intitulé doit rester affiché, en texte"


def test_un_intitule_hostile_ne_produit_pas_de_balise():
    h = _rendre('rendreDecisions',
                [dict(DECISION, titre='<img src=x onerror=alert(1)>')])
    assert '<img' not in h
    assert '&lt;img src=x onerror=alert(1)&gt;' in h


def test_un_lien_externe_ne_donne_pas_la_main_a_la_page_ouverte():
    assert 'rel="noopener' in _rendre('rendreDecisions', [DECISION])


# ── LE BRANCHEMENT DANS LES DEUX RENDUS ─────────────────────────────────

@pytest.mark.parametrize('ancre,ce_que_c_est', [
    ('function rendreAnalyse(', "l'analyse juridique et la revue de contrat"),
    ("'/api/juridique/arbitrage'", "la note d'arbitrage"),
])
def test_les_deux_rendus_portent_le_controle_de_jurisprudence(ancre, ce_que_c_est):
    """Une note d'arbitrage se lit en comité de direction ; il n'y a aucune
    raison qu'elle affiche moins de garde-fous qu'une analyse."""
    d = PAGE.index(ancre)
    bloc = PAGE[d:d + 3000]
    assert 'rendreJurisprudence(' in bloc, (
        "%s n'affiche pas le contrôle des décisions citées" % ce_que_c_est)
    assert 'rendreDecisions(' in bloc, (
        "%s n'affiche pas les décisions consultées" % ce_que_c_est)


def test_le_controle_des_textes_est_toujours_affiche():
    """L'ajout ne doit pas avoir remplacé le contrôle qui existait."""
    assert PAGE.count('rendreCitations(j.citations)') >= 2
