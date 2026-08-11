"""Les modules numérotés — encadrement, et signalement de ce qui n'a pas servi.

CE QUI ÉTAIT DEMANDÉ. Séparer les blocs numérotés par un encadrement bleu
distinctif, et les faire clignoter tant qu'ils n'ont pas été sollicités.

LES DEUX PIÈGES DE CETTE DEMANDE, ET CE QUE LA MISE EN ŒUVRE EN FAIT :

  1. DIX BLOCS QUI CLIGNOTENT ENSEMBLE NE SIGNALENT PLUS RIEN. Sur la page des
     centres de données, onze modules sont non parcourus à l'arrivée. Les faire
     battre tous ferait un sapin de Noël, et le lecteur apprendrait en trois
     secondes à ne plus le voir. Le battement se déclenche donc quand le module
     ENTRE À L'ÉCRAN — le lecteur reçoit l'indication là où il regarde.

  2. UN CLIGNOTEMENT PERPÉTUEL EST NOCIF, ET IL N'INFORME PAS DURABLEMENT. Les
     règles d'accessibilité le déconseillent, et un signal passé ne laisse
     aucune trace pour qui a détourné les yeux. Le battement est donc BORNÉ à
     trois pulsations, et c'est la PASTILLE « à parcourir » qui porte
     l'information — elle reste jusqu'à ce que le module serve, et elle se lit
     sans percevoir le mouvement.

Ces tests éprouvent le MATÉRIAU ; le comportement — qui bat, quand, combien de
fois — est éprouvé par recette_modules.js dans le vrai document. La leçon est
acquise : un test qui lit le source ne voit pas ce qui est devenu inatteignable.
"""
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

# Le compte RÉEL des modules par page, relevé sur les fichiers. La page des
# centres de données en porte dix numérotés plus un marqué « ◆ » (le cadre
# Green Management) — soit onze blocs, et non sept comme on pourrait le croire
# en lisant le sommaire, qui n'en liste pas la totalité.
PAGES = {
    "datacenter.html": 11,
    "ingenierie-datacenter.html": 7,
    "strategie-durable-datacenter.html": 5,
}


def lire(nom):
    with open(os.path.join(ICI, nom), encoding="utf-8") as f:
        return f.read()


def modules(nom):
    return re.findall(r'<div class="rc-etape">\s*<span class="n">([^<]*)</span>',
                      lire(nom), re.S)


# ── 1. Le matériau est là, sur les trois pages ─────────────────────────────

@pytest.mark.parametrize("page", sorted(PAGES))
def test_chaque_page_charge_le_module_partage(page):
    """Un seul module pour trois pages : recopié, la règle du battement aurait
    divergé — et c'est celle qu'on ne remarque pas qui reste en clignotant."""
    assert "/modules.js" in lire(page), page


@pytest.mark.parametrize("page,n", sorted(PAGES.items()))
def test_le_compte_des_modules_est_celui_qu_on_croit(page, n):
    """Relevé plutôt que supposé : la page des centres de données en porte
    ONZE, et non sept."""
    assert len(modules(page)) == n, [x.strip() for x in modules(page)]


@pytest.mark.parametrize("page", sorted(PAGES))
def test_chaque_page_porte_le_cadre_bleu(page):
    h = lire(page)
    assert ".mod-bloc{" in h, page
    assert "var(--cyan" in h[h.index(".mod-bloc{"):h.index(".mod-bloc{") + 400], page


@pytest.mark.parametrize("page", sorted(PAGES))
def test_le_bloc_non_parcouru_se_distingue_SANS_animation(page):
    """Le cadre renforcé reste après le battement : c'est ce qui permet, en fin
    de lecture, de repérer d'un coup d'œil ce qui n'a pas été traité."""
    h = lire(page)
    assert ".mod-bloc.mod-neuf{" in h, page


# ── 2. Le battement est borné — le point qui compte ────────────────────────

@pytest.mark.parametrize("page", sorted(PAGES))
def test_l_animation_est_finie_et_non_perpetuelle(page):
    """LE CONTRÔLE QUI COMPTE ICI. « infinite » transformerait un signal en
    nuisance : les règles d'accessibilité déconseillent une animation qu'on ne
    peut pas arrêter, et un clignotement qui dure cesse d'informer."""
    h = lire(page)
    i = h.index(".mod-bloc.mod-bat{")
    regle = h[i:i + 160]
    assert "infinite" not in regle, regle
    m = re.search(r"animation:\s*mod-bat[^;}]*?\s(\d+)\s*(?:}|;)", regle)
    assert m, regle
    assert 1 <= int(m.group(1)) <= 5, m.group(1)


@pytest.mark.parametrize("page", sorted(PAGES))
def test_le_mouvement_reduit_supprime_toute_animation(page):
    """Non négociable : la pastille et le cadre portent alors l'information, et
    ils la portent aussi bien."""
    h = lire(page)
    i = h.index("prefers-reduced-motion")
    bloc = h[i:i + 220]
    assert "mod-bat" in bloc and "animation:none" in bloc, bloc[:160]


# ── 3. La pastille porte l'information, pas le battement ───────────────────

@pytest.mark.parametrize("page", sorted(PAGES))
def test_la_pastille_existe_et_se_lit_en_toutes_lettres(page):
    """Un clignotement passé ne laisse aucune trace. La pastille, elle, reste —
    et elle se lit sans percevoir le mouvement."""
    assert ".mod-chip{" in lire(page), page


def test_la_pastille_dit_ce_qu_elle_signifie():
    js = lire("modules.js")
    assert 'textContent = "à parcourir"' in js
    assert "n’a pas encore été sollicité" in js, "et son infobulle l'explique"


# ── 4. Ce que « sollicité » veut dire ──────────────────────────────────────

def test_un_module_est_sollicite_par_l_usage_de_ses_commandes():
    js = lire("modules.js")
    assert '["input", "change", "click"]' in js


def test_un_module_sans_commande_est_sollicite_par_la_lecture():
    """Exiger un clic sur un bloc qui n'en propose aucun serait une exigence
    qu'on ne peut pas satisfaire : la pastille ne partirait jamais."""
    js = lire("modules.js")
    assert "LECTURE_MS" in js
    m = re.search(r"LECTURE_MS\s*=\s*(\d+)", js)
    assert m and int(m.group(1)) >= 1000, (
        "un seuil trop court ferait éteindre dix pastilles au premier "
        "défilement rapide")


def test_le_battement_se_declenche_a_l_approche_et_non_au_chargement():
    """C'est ce qui empêche le sapin de Noël. Vérifié aussi dans le vrai
    document par recette_modules.js — ici, on ne garde que le matériau."""
    js = lire("modules.js")
    assert "IntersectionObserver" in js
    i = js.index("new IntersectionObserver")
    assert 'classList.add("mod-bat")' in js[i:i + 1400]


def test_sans_observateur_on_renonce_au_signal_plutot_qu_a_l_eteindre_jamais():
    """Un signal qu'on ne peut pas éteindre est pire que pas de signal."""
    js = lire("modules.js")
    assert 'if (!("IntersectionObserver" in window))' in js


def test_l_etat_survit_a_une_visite_suivante():
    js = lire("modules.js")
    assert "localStorage" in js
    assert "location.pathname" in js, "l'état est propre à chaque page"


def test_l_identite_d_un_module_ne_glisse_pas_quand_on_en_ajoute_un():
    """Un rang « module 4 » désignerait le module suivant après un ajout, et
    effacerait par erreur la pastille du nouveau."""
    js = lire("modules.js")
    i = js.index("function idDe(")
    assert "sec.id" in js[i:i + 400]


def test_le_stockage_indisponible_ne_casse_rien():
    """Navigation privée, cookies refusés : la page doit rester utilisable."""
    js = lire("modules.js")
    for fn in ("function lire()", "function ecrire(v)"):
        i = js.index(fn)
        assert "catch" in js[i:i + 260], fn
