"""Le parcours guidé — ce qu'il montre, dans quel ordre, et à qui.

CE QUI EST ÉPROUVÉ, et pourquoi ces règles-là. Le parcours a dérivé en silence
pendant des semaines : il annonçait cinq sections quand la page en portait
treize, et ses cinq numéros de section étaient TOUS faux. Rien ne levait, rien
ne s'affichait en rouge — un guide qui envoie au mauvais endroit se lit comme
un guide.

Les règles qui suivent tiennent les trois liens qui avaient cédé :

  · TOUTE ANCRE CITÉE EXISTE DANS LA PAGE. C'est le lien que le module Python
    ne peut pas vérifier lui-même — il ne lit pas le HTML — et c'est
    précisément pour cela qu'une règle d'essai le tient.
  · TOUTE SECTION DE LA PAGE EST ATTEINTE par au moins un parcours. C'est la
    règle qui manquait : huit sections existaient, étaient bonnes, et aucun
    guide n'y menait.
  · LE NUMÉRO DE SECTION N'EST PLUS SERVI par le serveur. Il se lit sur la
    page, là où il s'affiche. Deux endroits pour un même nombre, c'était
    garantir qu'ils divergeraient.
"""
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ingenierie_dc as G  # noqa: E402


def lire(nom):
    with open(os.path.join(ICI, nom), encoding="utf-8") as f:
        return f.read()


def sans_commentaires_js(src):
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(^|[^:])//[^\n]*", r"\1", src)


def ancres_de_la_page():
    """Les identifiants réellement posés dans la page."""
    return set(re.findall(r'id="([^"]+)"', lire("ingenierie-datacenter.html")))


# ── LE LIEN AVEC LA PAGE, QUI AVAIT CÉDÉ ───────────────────────────────────

def test_toute_ancre_du_parcours_existe_dans_la_page():
    """LE DÉFAUT QUE CETTE RÈGLE EMPÊCHE. Une ancre absente ne lève rien : le
    bouton « Aller à la section » ne fait rien, et le surlignage ne surligne
    rien. Le lecteur croit que la page est cassée, ou pire, qu'il a mal
    cliqué."""
    page = ancres_de_la_page()
    manquantes = sorted(a for a in G.SECTIONS_PAGE if a not in page)
    assert not manquantes, (
        "le parcours conduit vers des ancres qui n'existent pas : %s"
        % ", ".join(manquantes))


def test_toute_section_numerotee_de_la_page_est_atteinte_par_un_parcours():
    """LA RÈGLE QUI MANQUAIT, et qui a coûté huit sections. Elles existaient,
    elles étaient bonnes, et aucun guide n'y menait — le prix de la maîtrise
    d'œuvre, le coût des travaux, le programme, le régime réglementaire, la
    phase travaux, le dépôt, la réponse à l'appel d'offres.

    Une section que personne ne visite ne se signale jamais toute seule : elle
    n'est pas en erreur, elle est simplement invisible."""
    h = lire("ingenierie-datacenter.html")
    # Les sections numérotées de la page, et l'ancre par laquelle on y entre.
    sections = re.findall(
        r'<section class="wrap rc-sec"([^>]*)>\s*<div class="rc-etape">'
        r'<span class="n">(\d+)</span><h2>([^<]*)</h2>', h)
    assert len(sections) >= 13, len(sections)
    atteintes = {a for seq in G.SEQUENCES.values() for a in seq}
    # Pour chaque section, au moins une ancre du catalogue doit s'y trouver.
    orphelines = []
    for attrs, num, titre in sections:
        deb = h.index('<span class="n">%s</span><h2>%s</h2>' % (num, titre))
        fin = h.find("<section", deb)
        corps = h[deb:fin if fin > 0 else len(h)]
        ids = set(re.findall(r'id="([^"]+)"', corps)) | set(
            re.findall(r'id="([^"]+)"', attrs))
        if not (ids & atteintes):
            orphelines.append("%s · %s" % (num, titre))
    assert not orphelines, (
        "section(s) de la page qu'aucun parcours guidé ne fait visiter : %s"
        % " ; ".join(orphelines))


def test_le_numero_de_section_n_est_plus_servi_par_le_serveur():
    """DEUX ENDROITS POUR UN MÊME NOMBRE, c'était garantir qu'ils
    divergeraient — ils ont divergé, et les cinq numéros servis étaient faux.
    Le nombre vit désormais là où il s'affiche."""
    g = G.guide("moe", ["cout"], {"puissance_it_kw": 1000}, "APD")
    for e in g["etapes"]:
        assert "section" not in e, (
            "le serveur sert de nouveau un numéro de section : il divergera "
            "de la page à la prochaine section ajoutée")


def test_la_page_lit_le_numero_de_section_sur_elle_meme():
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    assert "function guideSection(" in js
    i = js.index("function guideSection(")
    corps = js[i:i + 500]
    assert ".rc-etape .n" in corps, (
        "le numéro n'est pas lu sur la puce de la section")
    assert "closest(\"section\")" in corps


# ── LES CONSIGNES SONT APPARIÉES, PLUS POSITIONNÉES ───────────────────────

def test_chaque_role_porte_une_consigne_par_etape_de_sa_sequence():
    """LE DÉFAUT DE LA STRUCTURE PRÉCÉDENTE. Les consignes étaient zippées
    rang par rang sur la liste des sections : ajouter une étape décalait
    TOUTES les consignes d'un cran, en silence, et chaque rôle se retrouvait à
    conseiller la section suivante. Clées par ancre, l'appariement ne peut
    plus glisser."""
    assert G._verifier_parcours() == []


def test_aucune_consigne_n_est_ecrite_pour_une_etape_hors_sequence():
    """Du texte écrit pour rien, qui ne s'affiche jamais — et qu'on croit
    livré."""
    for rid, consignes in G._CONSIGNES.items():
        hors = sorted(set(consignes) - set(G.SEQUENCES[rid]))
        assert not hors, (rid, hors)


def test_le_controle_attrape_une_section_orpheline(monkeypatch):
    """La règle se vérifie elle-même : si elle ne bite pas, plus rien ne
    protège les sections nouvellement ajoutées."""
    faux = {k: list(v) for k, v in G.SEQUENCES.items()}
    for seq in faux.values():
        while "ig-ao" in seq:
            seq.remove("ig-ao")
    monkeypatch.setattr(G, "SEQUENCES", faux)
    fautes = G._verifier_parcours()
    assert any("ig-ao" in f and "aucun parcours" in f for f in fautes), fautes


def test_le_controle_attrape_une_consigne_manquante(monkeypatch):
    faux = {k: dict(v) for k, v in G._CONSIGNES.items()}
    faux["moe"].pop("ig-dossier")
    monkeypatch.setattr(G, "_CONSIGNES", faux)
    assert any("ig-dossier" in f for f in G._verifier_parcours())


def test_le_controle_attrape_une_ancre_inconnue(monkeypatch):
    faux = {k: list(v) for k, v in G.SEQUENCES.items()}
    faux["moe"].append("ig-section-qui-n-existe-pas")
    monkeypatch.setattr(G, "SEQUENCES", faux)
    assert any("inconnue" in f for f in G._verifier_parcours())


# ── LA PÉDAGOGIE : ce que chaque étape doit dire ──────────────────────────

@pytest.mark.parametrize("rid", sorted(G.SEQUENCES))
def test_chaque_etape_dit_pourquoi_elle_vient_la(rid):
    """C'EST LA PARTIE QUI MANQUAIT. Une suite d'écrans sans logique se subit ;
    une séquence dont on comprend l'ordre se retient, et se refait seul la
    fois suivante."""
    g = G.guide(rid, ["cout"], {"puissance_it_kw": 1000})
    for e in g["etapes"]:
        assert len(e["pourquoi_ici"]) > 40, (rid, e["ancre"])


@pytest.mark.parametrize("rid", sorted(G.SEQUENCES))
def test_chaque_etape_dit_ce_qu_on_perd_a_la_sauter(rid):
    """Dire qu'une étape peut se sauter est plus honnête — et plus efficace —
    que de présenter sept étapes comme également obligatoires : le lecteur
    pressé saute de toute façon, autant qu'il sache laquelle."""
    g = G.guide(rid, ["cout"], {"puissance_it_kw": 1000})
    for e in g["etapes"]:
        assert len(e["si_vous_sautez"]) > 25, (rid, e["ancre"])


@pytest.mark.parametrize("rid", sorted(G.SEQUENCES))
def test_chaque_etape_annonce_un_ordre_de_grandeur_de_duree(rid):
    """Savoir qu'une étape prend deux minutes ou un quart d'heure décide si on
    la commence. C'est de l'accessibilité, pas du confort."""
    g = G.guide(rid, ["cout"], {"puissance_it_kw": 1000})
    for e in g["etapes"]:
        assert e["duree"] and len(e["duree"]) > 3, (rid, e["ancre"])


@pytest.mark.parametrize("rid", sorted(G.SEQUENCES))
def test_chaque_etape_dit_ce_que_la_section_EST(rid):
    """Un impératif servi sans son contexte s'exécute sans se comprendre. « Ce
    que la section est » vient donc avant « ce qu'il faut y faire »."""
    g = G.guide(rid, ["cout"], {"puissance_it_kw": 1000})
    for e in g["etapes"]:
        assert len(e["objet"]) > 40, (rid, e["ancre"])


def test_les_notions_citees_existent_toutes_au_glossaire():
    """Une notion qui renvoie à une famille inconnue affiche une puce muette :
    le lecteur la survole, rien ne vient, et il cesse de survoler les
    suivantes."""
    gl = G.glossaire()
    manquantes = []
    for rid, consignes in G._CONSIGNES.items():
        for ancre, c in consignes.items():
            for ref in c.get("notions") or []:
                fam, _, cle = ref.partition(":")
                if cle not in (gl.get(fam) or {}):
                    manquantes.append("%s/%s → %s" % (rid, ancre, ref))
    assert not manquantes, manquantes


def test_une_notion_rend_le_nom_du_glossaire_et_non_une_etiquette_recopiee():
    """Deux noms pour une notion valent moins qu'un seul : l'étiquette du
    parcours et celle de l'infobulle doivent être la même."""
    g = G.guide("discipline", ["disponibilite"], {"puissance_it_kw": 1000}, "APD")
    notions = [n for e in g["etapes"] for n in e["notions"]]
    assert notions
    gl = G.glossaire()
    for n in notions:
        fam, _, cle = n["ref"].partition(":")
        assert n["nom"] == gl[fam][cle]["nom"], n


def test_une_notion_inconnue_rend_sa_cle_plutot_que_rien():
    """Mieux vaut un code lisible qu'une puce vide, et l'anomalie se voit."""
    assert G._nom_notion("famille_absente:xyz") == "xyz"


# ── LES PARCOURS EUX-MÊMES ────────────────────────────────────────────────

def test_chaque_role_a_sa_propre_sequence():
    """UN PARCOURS N'EST PAS UNE VISITE COMPLÈTE. Faire passer tout le monde
    par les treize sections ne serait pas un parcours, ce serait un
    sommaire."""
    seqs = [tuple(s) for s in G.SEQUENCES.values()]
    assert len(set(seqs)) == len(seqs), "deux rôles suivent le même chemin"
    for rid, seq in G.SEQUENCES.items():
        assert len(seq) < len(G.SECTIONS_PAGE), rid


def test_tout_parcours_commence_par_ce_qui_conditionne_le_reste():
    """Le profil, ou le portefeuille pour la direction de programme. Une
    séquence qui commencerait par une section de lecture ferait perdre le
    lecteur avant qu'il ait saisi quoi que ce soit."""
    for rid, seq in G.SEQUENCES.items():
        assert seq[0] in ("ig-form", "ig-sec-projet", "ig-prog"), (rid, seq[0])


def test_tout_parcours_finit_par_les_limites():
    """Elles se lisent autrement une fois qu'on a vu ce que la page produit —
    et personne ne doit citer ces résultats ailleurs sans les avoir lues."""
    for rid, seq in G.SEQUENCES.items():
        assert seq[-1] == "ig-limites", (rid, seq[-1])


def test_la_direction_de_programme_existe_et_atteint_le_portefeuille():
    """Le rôle manquait, et sa section restait donc hors de tout parcours."""
    assert "programme" in G.SEQUENCES
    assert "ig-prog" in G.SEQUENCES["programme"]
    r = [x for x in G.ROLES_GUIDE if x["id"] == "programme"]
    assert r and r[0]["question"] and r[0]["fin"]


def test_un_parcours_inconnu_rend_none_plutot_qu_un_parcours_plausible():
    """Une combinaison mal orthographiée doit échouer, pas produire un
    parcours qui ne correspond à rien."""
    assert G.guide("archeologue", ["cout"]) is None
    assert G.guide("moe", ["gastronomie"]) is None
    assert G.guide("moe", []) is None, "aucun thème choisi doit échouer aussi"


def test_un_theme_envoye_DEUX_FOIS_n_apparait_QU_UNE_FOIS():
    g = G.guide("moe", ["cout", "cout"], {"puissance_it_kw": 1000})
    assert [t["id"] for t in g["themes"]] == ["cout"]


def test_un_theme_inconnu_PARMI_D_AUTRES_est_simplement_ignore():
    """Une faute de frappe sur un second thème ne doit pas faire disparaître
    le premier — c'est la différence avec un thème inconnu SEUL, qui doit
    faire échouer tout le parcours."""
    g = G.guide("moe", ["cout", "gastronomie"], {"puissance_it_kw": 1000})
    assert [t["id"] for t in g["themes"]] == ["cout"]


# ── PLUSIEURS THÈMES : UNION, PAS RÉPÉTITION ────────────────────────────────

def test_plusieurs_themes_UNISSENT_les_pieces_SANS_DOUBLE_COMPTE():
    """DÉFAUT À NE PAS INTRODUIRE : sommer les pièces de chaque thème
    compterait deux fois celles qui relèvent des deux — les chiffres
    cesseraient de décrire le dossier réel pour décrire une lecture qui se
    recoupe elle-même."""
    profil = {"puissance_it_kw": 1000}
    g1 = G.guide("moe", ["energie"], profil, "APD")
    g2 = G.guide("moe", ["eau"], profil, "APD")
    g12 = G.guide("moe", ["energie", "eau"], profil, "APD")
    codes1 = {p["code"] for p in g1["pieces_du_theme"]}
    codes2 = {p["code"] for p in g2["pieces_du_theme"]}
    codes12 = {p["code"] for p in g12["pieces_du_theme"]}
    assert codes12 == codes1 | codes2
    # LE TÉMOIN QUI DISTINGUE UNION ET SOMME : si un seul code est commun aux
    # deux thèmes, l'union porte STRICTEMENT MOINS d'éléments que la somme
    # des deux comptes pris séparément.
    assert codes1 & codes2, "l'essai ne prouve rien sans recouvrement réel"
    assert len(codes12) < len(codes1) + len(codes2)


def test_les_disciplines_de_PLUSIEURS_themes_S_UNISSENT_pas_S_INTERSECTENT():
    """TÉMOIN DISTINCT DE L'UNION DES PIÈCES : « sécurité » (aucun
    `pieces_sup`, uniquement des disciplines) et « carbone » n'ont AUCUNE
    pièce en commun. Si les disciplines des thèmes choisis se recoupaient au
    lieu de s'unir, l'un des deux perdrait TOUTES ses pièces plutôt qu'une
    seule pièce en double — ce qu'un simple test d'union sur deux thèmes qui
    se recouvrent en partie ne verrait pas."""
    profil = {"puissance_it_kw": 1000}
    gs = G.guide("moe", ["securite"], profil)
    gc = G.guide("moe", ["carbone"], profil)
    g = G.guide("moe", ["securite", "carbone"], profil)
    codes_s = {p["code"] for p in gs["pieces_du_theme"]}
    codes_c = {p["code"] for p in gc["pieces_du_theme"]}
    codes = {p["code"] for p in g["pieces_du_theme"]}
    assert codes_s and codes_c, "l'essai suppose des pièces des deux côtés"
    assert not (codes_s & codes_c), "l'essai suppose aucun recouvrement"
    assert codes == codes_s | codes_c


def test_les_disciplines_RENVOYEES_couvrent_TOUS_les_themes_choisis():
    g = G.guide("moe", ["securite", "carbone"], {"puissance_it_kw": 1000})
    cles = {d["cle"] for d in g["disciplines"]}
    securite = next(t for t in G.THEMES_GUIDE if t["id"] == "securite")
    carbone = next(t for t in G.THEMES_GUIDE if t["id"] == "carbone")
    assert set(securite["disciplines"]) <= cles, (
        "les disciplines de « sécurité » ont disparu de la réponse")
    assert set(carbone["disciplines"]) <= cles, (
        "les disciplines de « carbone » ont disparu de la réponse")


def test_plusieurs_themes_gardent_L_ORDRE_DU_CATALOGUE_pas_celui_du_clic():
    profil = {"puissance_it_kw": 1000}
    a = G.guide("moe", ["cout", "energie"], profil)
    b = G.guide("moe", ["energie", "cout"], profil)
    assert [t["id"] for t in a["themes"]] == [t["id"] for t in b["themes"]]
    ordre_catalogue = [t["id"] for t in G.THEMES_GUIDE if t["id"] in
                       ("cout", "energie")]
    assert [t["id"] for t in a["themes"]] == ordre_catalogue


def test_chaque_theme_choisi_GARDE_SON_PROPRE_PIEGE():
    """Fondre les pièges en un seul texte perdrait lequel vient d'où — la
    règle éprouve que chaque thème renvoyé porte SON piège à lui, distinct
    de celui d'un autre thème choisi en même temps."""
    g = G.guide("moe", ["energie", "eau"], {"puissance_it_kw": 1000})
    par_id = {t["id"]: t["piege"] for t in g["themes"]}
    energie = next(t for t in G.THEMES_GUIDE if t["id"] == "energie")
    eau = next(t for t in G.THEMES_GUIDE if t["id"] == "eau")
    assert par_id["energie"] == energie["piege"]
    assert par_id["eau"] == eau["piege"]
    assert par_id["energie"] != par_id["eau"]


def test_un_poste_demande_par_DEUX_themes_n_apparait_QU_UNE_FOIS():
    """« énergie » et « disponibilite » demandent tous deux le PUE — un
    profil qui choisit les deux ne doit pas le voir deux fois de suite dans
    le même parcours."""
    g = G.guide("moe", ["energie", "disponibilite"], {"puissance_it_kw": 1000})
    cles = [p["cle"] for p in g["postes"]]
    assert cles.count("pue") == 1, cles


def test_la_formule_du_compte_de_pieces_S_ACCORDE_au_nombre_de_themes():
    """Un seul thème se lit « de ce thème » ; en choisir plusieurs doit le
    dire, sous peine de laisser croire qu'un seul a été retenu."""
    profil = {"puissance_it_kw": 1000}
    g1 = G.guide("moe", ["cout"], profil, "APD")
    g2 = G.guide("moe", ["cout", "energie"], profil, "APD")
    texte1 = next(c for e in g1["etapes"] if e["ancre"] == "ig-dossier"
                  for c in e["chiffres"] if "pièce" in c)
    texte2 = next(c for e in g2["etapes"] if e["ancre"] == "ig-dossier"
                  for c in e["chiffres"] if "pièce" in c)
    assert "ce thème" in texte1 and "thèmes" not in texte1
    assert "2 thèmes" in texte2


def test_les_couleurs_de_role_restent_distinctes():
    """Deux rôles de même couleur ne s'identifient plus, et c'est toute la
    raison d'être de la couleur."""
    couleurs = [r["couleur"] for r in G.ROLES_GUIDE]
    assert len(set(couleurs)) == len(couleurs), couleurs


# ── LE RENDU DE LA PAGE ───────────────────────────────────────────────────

@pytest.mark.parametrize("champ", ["objet", "pourquoi_ici", "si_vous_sautez",
                                   "duree", "notions"])
def test_la_page_rend_chaque_nouveau_champ(champ):
    """Un champ servi et non rendu est du texte écrit pour rien — et personne
    ne s'en aperçoit, puisque la page s'affiche normalement.

    LA RÈGLE PORTE SUR LE GARDE, pas sur la simple présence du nom. Sa
    première version cherchait « e.pourquoi_ici » n'importe où dans la
    fonction : remplacer le garde par `if (false)` la laissait passer, puisque
    le nom survivait dans la branche morte. Ce qui se vérifie, c'est que le
    champ commande son propre affichage — présent, il s'affiche ; absent, il
    ne laisse pas de trou."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function guideRendreEtape(")
    corps = js[i:js.index("function guideAller(")]
    assert "e." + champ in corps, "%s n'est pas rendu du tout" % champ
    # Le champ conditionne son propre rendu : dans un `if`, ou dans le
    # ternaire d'une concaténation.
    garde = ("if (e.%s" % champ) in corps or ("e.%s ?" % champ) in corps
    assert garde, (
        "%s est cité mais son affichage ne dépend pas de lui : un garde "
        "constant le rendrait invisible sans que rien ne le signale" % champ)


def test_les_notions_portent_l_attribut_d_infobulle_existant():
    """Le mécanisme existe et couvre trente-cinq familles : en ouvrir un
    second pour le parcours l'aurait fait diverger."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function guideRendreEtape(")
    corps = js[i:js.index("function guideAller(")]
    assert "info(x.ref)" in corps


def test_les_classes_du_parcours_sont_definies():
    h = lire("ingenierie-datacenter.html")
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function guideRendreEtape(")
    corps = js[i:js.index("function guideAller(")]
    for cls in sorted(set(re.findall(r'class="(ig-g-(?:ob|pq|sa|no|nt|du))"',
                                     corps))):
        assert ".%s{" % cls in h, cls


# ── PLUSIEURS THÈMES CHOISIS EN PAGE — le choix, le rendu, l'envoi ─────────

def _corps(js, debut, fin):
    return js[js.index("function %s(" % debut):js.index("function %s(" % fin)]


def test_le_bouton_theme_BASCULE_au_lieu_de_REMPLACER():
    """DÉFAUT À NE PAS RÉINTRODUIRE : `GUIDE_THEME = ...` remplaçait tout
    choix précédent — la sélection multiple exige une bascule
    (push/splice), pas une affectation."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    corps = _corps(js, "guideRendreChoix", "guideCharger")
    assert "GUIDE_THEME =" not in corps, (
        "le clic sur un thème remplace encore la sélection au lieu de la "
        "compléter")
    assert "GUIDE_THEMES.splice" in corps and "GUIDE_THEMES.push" in corps


def test_commencer_le_parcours_EXIGE_au_moins_UN_theme_pas_UN_SEUL():
    """« au moins un » et pas « exactement un » : `GUIDE_THEMES.length` seul
    doit conditionner le départ — un `=== 1` accolé redeviendrait une
    exigence d'un SEUL thème, silencieusement, sans qu'un simple test de
    présence de la sous-chaîne `GUIDE_THEMES.length` le voie passer."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    corps_choix = _corps(js, "guideChoix", "guideRendreChoix")
    corps_charger = _corps(js, "guideCharger", "guideRendreEtape")
    for corps in (corps_choix, corps_charger):
        assert "GUIDE_THEMES.length" in corps, (
            "le déclenchement du parcours ne vérifie plus la longueur du "
            "tableau de thèmes")
        # \b évite qu'un « GUIDE_THEME » retrouvé comme simple SOUS-CHAÎNE de
        # « GUIDE_THEMES » (son propre remplaçant) fasse échouer la règle.
        assert not re.search(r"\bGUIDE_THEME\b", corps), (
            "un ancien test scalaire sur GUIDE_THEME subsiste")
        assert "GUIDE_THEMES.length ===" not in corps, (
            "la longueur du tableau de thèmes est comparée à une valeur "
            "exacte — redevenue une exigence d'UN SEUL thème")


def test_guideCharger_ENVOIE_le_TABLEAU_de_themes_au_serveur():
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    corps = _corps(js, "guideCharger", "guideRendreEtape")
    assert "p.themes = GUIDE_THEMES" in corps


def test_chaque_bouton_theme_REFLETE_SA_PROPRE_selection():
    """`GUIDE_THEMES.indexOf(t.id) >= 0` doit conditionner CHAQUE bouton
    individuellement — une condition qui ne dépendrait que d'UN thème
    global marquerait tous les boutons pareil, ou aucun."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    corps = _corps(js, "guideChoix", "guideRendreChoix")
    assert "GUIDE_THEMES.indexOf(t.id)" in corps


def test_aria_pressed_REFLETE_la_selection_REELLE_de_chaque_bouton():
    """`aria-pressed` est une promesse faite au lecteur d'écran : un bouton
    qui l'affiche doit REFLÉTER son propre état, pas une valeur fixe — sinon
    la bascule visuelle (classe `.on`) existe sans que l'accessibilité la
    porte."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    corps = _corps(js, "guideChoix", "guideRendreChoix")
    assert '(choisi ? "true" : "false")' in corps, (
        "aria-pressed ne dépend plus de l'état réel du bouton")


def test_l_entete_du_parcours_LISTE_TOUS_LES_THEMES():
    """`GUIDE.themes[0]` seul suffirait à la couleur de la jauge, mais PAS à
    l'intitulé : un lecteur qui a choisi deux thèmes doit voir les deux
    dans l'en-tête, pas seulement le premier.

    LA RÈGLE EST BORNÉE À L'EN-TÊTE, pas à toute la fonction : le bloc final
    itère LUI AUSSI sur `GUIDE.themes.map(`, pour ses pièges — chercher cette
    chaîne n'importe où dans `guideRendreEtape` resterait vert même si
    l'en-tête, seul, retombait sur `GUIDE.themes[0]`. Défaut réel, trouvé en
    écrivant cette règle : la première version cherchait sans borne et ne
    voyait pas une mutation qui cassait spécifiquement l'en-tête."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    corps = _corps(js, "guideRendreEtape", "guideAller")
    entete = corps[corps.index('class="ig-g-rt"'):corps.index('id="ig-g-changer"')]
    assert "GUIDE.themes.map(" in entete
    assert "GUIDE.themes[0].icone" not in entete
    assert "GUIDE.themes[0].nom" not in entete


def test_le_bloc_final_RENVOIE_UN_PIEGE_PAR_THEME():
    """Fondre les pièges en un seul texte perdrait lequel vient d'où — la
    règle éprouve que le rendu itère sur `GUIDE.themes`, pas sur un thème
    unique."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    corps = _corps(js, "guideRendreEtape", "guideAller")
    fin = corps[corps.index("GUIDE_ETAPE === n - 1"):]
    assert "GUIDE.themes.map(" in fin
    assert "GUIDE.theme." not in fin, (
        "le bloc final lit encore un thème unique au lieu du tableau")


def test_la_classe_de_l_indication_multi_choix_est_definie():
    h = lire("ingenierie-datacenter.html")
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    corps = _corps(js, "guideChoix", "guideRendreChoix")
    classes = sorted(set(re.findall(r'class="(ig-g-plu)"', corps)))
    assert classes, "la classe ig-g-plu n'apparaît plus dans le rendu"
    for cls in classes:
        assert ".%s{" % cls in h, cls
