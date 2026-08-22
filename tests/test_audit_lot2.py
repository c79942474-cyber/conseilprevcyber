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


# ── 6. Le cockpit ne dit plus son état par la seule couleur ───────────────

def test_le_statut_de_zone_est_ecrit_et_non_seulement_colore():
    """L'état n'était porté que par une pastille de 9 px, complétée d'un
    `title` en anglais — attribut que les lecteurs d'écran n'exposent pas de
    façon fiable et qui n'apparaît jamais au doigt. Un exploitant daltonien
    voyait le même écran pour une zone saine et une zone en alerte."""
    s = _lire("demo.html")
    assert "var ETAT_MOT" in s
    for mot in ("'OK'", "'Surveillé'", "'Alerte'"):
        assert mot in s, mot
    # la pastille ne porte plus l'information : elle la redouble
    assert 'class="st \'+st+\'" aria-hidden="true"' in s
    assert 'title="\'+st+\'"' not in s, "le title anglais est revenu"


def test_le_mot_et_la_pastille_sont_ecrits_ensemble():
    """Les mettre à jour séparément laisserait un écran affichant « OK » en
    rouge — pire que l'absence de mot."""
    s = _lire("demo.html")
    i = s.index("function updateMapCounts")
    bloc = s[i:i + 700]
    assert "ETAT_MOT[st]" in bloc and "className='st '+st" in bloc, bloc[:400]


def test_le_journal_d_evenements_est_annonce():
    """Il s'écrivait sans aucune région annoncée : un utilisateur de lecteur
    d'écran ne recevait rien, pas même les alertes critiques — alors que
    c'est ce que cette page existe pour signaler."""
    s = _lire("demo.html")
    i = s.index('id="feed"')
    bloc = s[max(0, i - 120):i + 260]
    assert 'role="log"' in bloc and 'aria-live="polite"' in bloc, bloc
    assert 'aria-label=' in bloc


def test_seul_le_critique_interrompt():
    """Tout passer en assertif rendrait la page inutilisable : le flux parle
    en continu, et la seule issue serait de le couper — donc de perdre aussi
    les alertes."""
    s = _lire("demo.html")
    assert 'id="critLive"' in s and 'aria-live="assertive"' in s
    i = s.index("if(tag==='crit')")
    assert "critLive" in s[i:i + 200]


def test_les_etiquettes_du_flux_se_prononcent():
    """« CRIT » et « WARN » en capitales abrégées ne veulent rien dire lus à
    voix haute — or c'est ainsi qu'ils arrivent au lecteur d'écran."""
    s = _lire("demo.html")
    assert "var TAG_MOT" in s
    for mot in ("'Découverte'", "'À surveiller'", "'Critique'", "'Correctif'"):
        assert mot in s, mot
    assert '<span class="tg \'+tag+\'" aria-hidden="true">' in s


# ── 7. La recherche couvre le menu, et le marquage dit ce qui manque ──────

def _listes_nav():
    s = _lire("nav.js")
    i = s.index("=", s.index("NAV_SECTIONS"))
    tiroir = re.findall(r'\["(/[^"]*)"', s[i:s.index("\n  ];", i)])
    k = s.index("var SEARCH = [")
    recherche = re.findall(r'^\s*\["(/[^"]*)"', s[k:s.index("\n  ];", k)], re.M)
    return tiroir, recherche


def test_toute_page_du_menu_est_trouvable_par_la_recherche():
    """DÉFAUT CORRIGÉ : l'index couvrait 34 des 43 pages du tiroir. Toute la
    rubrique « Conseil & transformation » (neuf pages), trois pages de centres
    de données et le conseil juridique étaient introuvables. Un visiteur qui
    tapait « maturité » ou « feuille de route » — deux des entrées les plus
    commerciales du site — lisait « aucun résultat », ce qui s'entend comme
    « ce cabinet ne le fait pas ».

    La dérive est silencieuse par construction : on ajoute une page au tiroir,
    on oublie l'index, et rien ne le signale. D'où ce contrôle."""
    tiroir, recherche = _listes_nav()
    manquantes = [p for p in tiroir if p not in recherche]
    assert not manquantes, manquantes


def test_la_recherche_ne_propose_aucune_page_absente_du_site():
    """L'inverse compte aussi : une entrée pointant dans le vide envoie le
    visiteur sur un 404 depuis la fonction censée l'orienter."""
    import app
    connus = {str(r.rule) for r in app.app.url_map.iter_rules()}
    _, recherche = _listes_nav()
    fantomes = [p for p in recherche if p not in connus]
    assert not fantomes, fantomes


def test_les_deux_niveaux_d_acces_sont_servis_separement(anonyme):
    """Fondus en une seule liste, ils empêchaient de signaler à un client
    CONNECTÉ ce qui lui reste fermé."""
    j = anonyme.get("/api/acces").get_json()
    assert j["admin"], "aucune page d'administration relevée"
    assert set(j["admin"]) <= set(j["client"])


def test_un_client_connecte_voit_marquer_ce_qui_lui_reste_ferme():
    """Le marquage s'arrêtait dès qu'un visiteur était connecté — vrai des
    pages client, faux des pages d'administration. Un client validé voyait
    donc les liens de l'espace administrateur sans marque, et le clic le
    menait à un refus."""
    s = _lire("nav.js")
    i = s.index("function initAcces")
    bloc = s[i:i + 700]
    assert "a.estAdmin" in bloc, bloc[:300]
    assert "a.connecte ? a.admin : a.client" in bloc, bloc[:300]


def test_le_message_ne_propose_pas_un_compte_a_qui_en_a_un():
    """« Compte validé requis » adressé à quelqu'un qui en possède un le
    renvoie créer ce qu'il a déjà."""
    s = _lire("nav.js")
    i = s.index("function _legendeAcces")
    bloc = s[i:i + 1100]
    assert "réservées à" in bloc and "n’a" in bloc
    assert "Votre compte est bien validé" in bloc, bloc[:400]
