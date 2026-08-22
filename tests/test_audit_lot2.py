"""LOT 2 DE L'AUDIT — les constats vérifiés puis corrigés.

Chacun de ces contrôles garde une correction, et chacun est écrit pour tomber
si la faute revient. Ils portent sur quatre familles :

  1. UNE PANNE NE DOIT PAS SE LIRE COMME UNE MESURE. C'était le constat
     bloquant : la page d'audit affichait « indice de risque 0/100 » horodaté
     alors que rien n'avait été mesuré.
  2. UNE ADRESSE INCONNUE RESTE SUR LE SITE. Aucun gestionnaire 404
     n'existait.
  3. UN CHAMP DE FORMULAIRE PORTE SON NOM. Neuf libellés du parcours de
     compte n'étaient rattachés à aucun champ.
  4. LES RÉFÉRENCES NORMATIVES SONT EXACTES. La table des parties d'ISO/IEC
     30134 attribuait le CER à la partie 8, qui est le CUE.
"""
import os
import re

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _lire(nom):
    with open(os.path.join(ICI, nom), encoding="utf-8") as f:
        return f.read()


# ── 1. Une panne ne se lit pas comme une mesure ───────────────────────────

def test_l_indice_de_risque_ne_naît_plus_d_un_ou_logique():
    """CONSTAT BLOQUANT. `(st.risk||0)` transformait un champ absent en zéro,
    et la page affichait « indice de risque 0/100 » avec l'heure à côté. Sur
    une page d'audit, zéro est exactement la valeur qu'un exploitant a envie
    de lire : une panne de collecte se présentait en certificat de santé."""
    s = _lire("audit-conformite.html")
    assert "(st.risk||0)" not in s and "(st.assets||0)" not in s
    assert "typeof st.risk === 'number'" in s


def test_l_absence_de_mesure_est_dite_et_non_notée():
    s = _lire("audit-conformite.html")
    assert "l’absence de mesure n’est" in s or "absence de mesure n" in s
    assert "indice non calculable" in s


def test_l_horodatage_n_accompagne_que_ce_qui_est_mesuré():
    """Dater ce qui n'a pas été mesuré, c'est le certifier."""
    s = _lire("audit-conformite.html")
    i = s.index("toLocaleTimeString")
    fenetre = s[max(0, i - 260):i]
    assert "mesure && !vide" in fenetre, fenetre[-160:]


def test_sans_actif_le_tableau_de_bord_ne_note_pas_maitrise():
    """Le repli local calculait un risque sur une liste vide et rendait
    « 0/100 · niveau maîtrisé » — la même contrevérité par un autre chemin."""
    s = _lire("audit-conformite.html")
    assert "var mesurable=a.length>0" in s
    assert "aucun actif : indice non calculable" in s


# ── 2. Une adresse inconnue reste sur le site ─────────────────────────────

def test_une_adresse_inconnue_rend_une_page_du_site(anonyme):
    r = anonyme.get("/cette-page-na-jamais-existe")
    assert r.status_code == 404
    corps = r.get_data(as_text=True)
    assert "CONSEILPREV" in corps
    # LE POINT DU CONSTAT : la page par défaut du serveur n'offrait AUCUN lien.
    assert corps.count("<a href=") >= 4, "une page d'erreur sans issue"
    assert 'href="/"' in corps


def test_une_adresse_d_api_inconnue_rend_du_json(anonyme):
    """Un client qui attend du JSON échouerait sur « Unexpected token '<' »."""
    r = anonyme.get("/api/route-inexistante")
    assert r.status_code == 404
    assert r.get_json()["error"] == "introuvable"


def test_le_chemin_demandé_ressort_échappé(anonyme):
    """Le chemin est écrit dans la page : il vient du visiteur."""
    r = anonyme.get("/x<img src=x onerror=alert(1)>")
    corps = r.get_data(as_text=True)
    assert "<img src=x" not in corps
    assert "&lt;img" in corps


def test_la_page_404_n_est_pas_indexée(anonyme):
    assert 'name="robots" content="noindex"' in \
        anonyme.get("/inconnue").get_data(as_text=True)


# ── 3. Un champ de formulaire porte son nom ───────────────────────────────

PAGES_COMPTE = ["inscription.html", "connexion.html",
                "mot-de-passe-oublie.html", "reinitialiser.html"]


@pytest.mark.parametrize("page", PAGES_COMPTE)
def test_chaque_libellé_est_rattaché_à_son_champ(page):
    """Sans `for`, un lecteur d'écran annonce « zone de saisie » sans dire
    laquelle : sur un parcours de mot de passe, c'est bloquant."""
    s = _lire(page)
    labels = re.findall(r"<label\b[^>]*>", s)
    assert labels, page
    for l in labels:
        assert "for=" in l, (page, l[:120])


@pytest.mark.parametrize("page", PAGES_COMPTE)
def test_chaque_for_désigne_un_champ_qui_existe(page):
    """Un `for` qui pointe dans le vide ne vaut pas mieux que pas de `for`."""
    s = _lire(page)
    ids = set(re.findall(r'<input[^>]*\bid="([^"]+)"', s))
    for cible in re.findall(r'<label\b[^>]*\bfor="([^"]+)"', s):
        assert cible in ids, (page, cible)


# ── 4. L'aide est atteignable, et la cible visable ────────────────────────

def test_le_texte_d_aide_est_le_nom_accessible_du_bouton():
    """Il n'existait que dans `data-tip`, rendu par `content: attr(...)` sur
    un ::after : le contenu généré par CSS n'est pas exposé de façon fiable
    aux lecteurs d'écran, et il est en display:none hors survol."""
    s = _lire("inscription.html")
    m = re.search(r'class="tipi" data-tip="([^"]+)" aria-label="([^"]+)"', s)
    assert m, "bouton d'aide introuvable"
    tip, nom = m.group(1), m.group(2)
    assert tip in nom, (tip[:60], nom[:60])


def test_aucun_bouton_d_aide_ne_garde_un_libellé_plus_court_que_son_aide():
    import glob
    manques = []
    for f in glob.glob(os.path.join(ICI, "*.html")):
        s = open(f, encoding="utf-8").read()
        for m in re.finditer(r'class="tipi"[^>]*data-tip="([^"]*)"[^>]*aria-label="([^"]*)"', s):
            if m.group(1) not in m.group(2):
                manques.append((os.path.basename(f), m.group(1)[:50]))
    assert not manques, manques[:5]


def test_la_cible_des_pastilles_d_aide_atteint_24_pixels():
    """En deçà, le critère « taille de cible » (WCAG 2.2, AA) n'est pas tenu —
    et sur un poste d'atelier, avec des gants, la pastille est hors de
    portée."""
    s = _lire("styles.css")
    i = s.index(".tipi{")
    bloc = s[i:i + 400]
    assert "width:24px" in bloc and "height:24px" in bloc, bloc[:200]
    assert "min-width:24px" in bloc


# ── 5. Les références normatives sont exactes ─────────────────────────────

def test_la_table_des_parties_iso30134_est_juste():
    """ERREUR FACTUELLE. La partie 8 est le CUE, pas le CER ; le CER est la
    partie 7, qui manquait. Un exploitant qui contractualiserait « CER selon
    30134-8 » achèterait autre chose que ce qu'il croit."""
    import datacenter as DC
    p = DC.CADRE_UE["iso30134"]["parties"]
    assert p["-8"] == "CUE", p
    assert p["-7"] == "CER", p
    assert p["-2"] == "PUE" and p["-9"] == "WUE"
    assert "-1" in p, "la vue d'ensemble manquait : la série paraissait " \
                      "commencer au PUE"


def test_le_cue_nomme_la_partie_de_la_norme_et_non_la_famille():
    """« ISO/IEC 30134 (famille) » ne désigne aucun document : c'était le seul
    indicateur du moteur dont la référence n'était pas re-dérivable."""
    s = _lire("datacenter.py")
    i = s.index('"CUE — Carbon Usage Effectiveness"')
    bloc = s[i:i + 700]
    assert "30134-8" in bloc, bloc[:400]
    assert "30134 (famille)" not in bloc
