"""Les trois sections ajoutées aux pages, et le bloc des fluides.

CE QU'UN TEST QUI LIT LE SOURCE PEUT ÉPROUVER, et ce qu'il ne peut pas. Il ne
voit pas le rendu ; il voit le MATÉRIAU. Les règles portent donc sur des
propriétés vérifiables sans navigateur :

  · une fonction appelée existe, et une fonction définie est appelée — une
    section dont le formulaire n'est jamais dessiné n'existe pas pour le
    lecteur, et rien ne le signale ;
  · un bouton posé dans le HTML a un écouteur, et réciproquement ;
  · une classe CSS employée par le rendu est définie ;
  · les réserves qui font tenir le reste sont sur la page, pas seulement dans
    la réponse du serveur.

LA LEÇON EST ACQUISE dans ce dépôt : une règle qui cherche un TEXTE se
satisfait d'un commentaire. Celles qui suivent cherchent des appels, des
identifiants et des définitions — des choses qui n'existent pas en prose.
"""
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)


def lire(nom):
    with open(os.path.join(ICI, nom), encoding="utf-8") as f:
        return f.read()


def sans_commentaires_js(src):
    """Le JavaScript débarrassé de ses commentaires.

    POURQUOI C'EST NÉCESSAIRE ICI. Ce dépôt commente abondamment, et une règle
    qui cherche `icpeFormulaire(` trouverait la phrase d'un commentaire qui
    l'explique. Le défaut s'est déjà produit six fois dans ce projet : une
    règle satisfaite par la prose qui la décrit ne vérifie plus rien.
    """
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(^|[^:])//[^\n]*", r"\1", src)


# ── Les sections existent et sont numérotées ───────────────────────────────

@pytest.mark.parametrize("ancre,titre", [
    ("ig-icpe", "régime ICPE"),
    ("ig-travaux", "phase travaux"),
    ("ig-ao", "appel d'offres"),
])
def test_chaque_section_ajoutee_est_dans_la_page(ancre, titre):
    h = lire("ingenierie-datacenter.html")
    assert 'id="%s"' % ancre in h, ancre
    i = h.index('id="%s"' % ancre)
    assert titre.lower() in h[i:i + 400].lower(), (ancre, titre)


def test_les_zones_de_rendu_des_trois_sections_existent():
    """Une fonction qui écrit dans un identifiant absent échoue en silence :
    `$("#…")` rend null, et le rendu ne se produit jamais."""
    h = lire("ingenierie-datacenter.html")
    for zid in ("ig-icpe-form", "ig-icpe-out", "ig-icpe-msg",
                "ig-tr-form", "ig-tr-out", "ig-tr-msg",
                "ig-ao-depot", "ig-ao-out", "ig-ao-cand-out", "ig-ao-msg"):
        assert 'id="%s"' % zid in h, zid


# ── Le câblage : ce qui est défini est appelé, ce qui est appelé existe ────

@pytest.mark.parametrize("fn", ["icpeFormulaire", "icpeCribler", "icpeRendre",
                                "icpeFiche", "travauxFormulaire",
                                "travauxPlan", "travauxRendre", "aoDocuments",
                                "aoAnalyser", "aoRendre", "aoCandidature",
                                "aoCandRendre", "aoIgnores"])
def test_chaque_fonction_ajoutee_est_definie_et_appelee(fn):
    """UNE FONCTION DÉFINIE ET JAMAIS APPELÉE est du code mort qui a l'air
    vivant : la relecture la voit, la page ne l'exécute pas, et la section
    reste vide sans erreur."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    assert "function %s(" % fn in js, fn
    # UNE RÉFÉRENCE, pas nécessairement un appel : `icpeCribler` est passée en
    # gestionnaire d'événement — `addEventListener("click", icpeCribler)` —
    # et n'est donc jamais suivie d'une parenthèse ouvrante. Compter les
    # appels aurait déclaré morte une fonction parfaitement branchée.
    refs = len(re.findall(r"\b%s\b" % re.escape(fn), js))
    assert refs >= 2, "%s est définie mais jamais référencée ailleurs" % fn


@pytest.mark.parametrize("bouton,fonction", [
    ("ig-icpe-go", "icpeCribler"),
    ("ig-ao-go", "aoAnalyser"),
    ("ig-ao-cand", "aoCandidature"),
])
def test_chaque_bouton_de_la_page_porte_son_ecouteur(bouton, fonction):
    """Un bouton sans écouteur est le pire des défauts d'interface : il a
    l'air de marcher, il ne fait rien, et le lecteur croit que le serveur ne
    répond pas."""
    assert 'id="%s"' % bouton in lire("ingenierie-datacenter.html"), bouton
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    # `\)+` et non `\)\)` : le nombre de parenthèses fermantes dépend de la
    # forme du garde — `if ((b = $("#x")))` en porte trois. Une règle qui en
    # compte un nombre fixe se casse sur une reformulation qui ne change rien.
    m = re.search(r'\$\("#%s"\)+\s*b\.addEventListener\("click",\s*(\w+)'
                  % re.escape(bouton), js)
    assert m, "aucun écouteur de clic sur #%s" % bouton
    assert m.group(1) == fonction, (bouton, m.group(1))


def test_les_trois_formulaires_sont_dessines_au_demarrage():
    """Un bouton sans formulaire au-dessus n'invite personne. Les formulaires
    se dessinent d'emblée ; aucun ne calcule tant qu'on ne le demande pas."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function démarrer(")
    corps = js[i:i + 6000]
    for appel in ("icpeFormulaire(", "travauxFormulaire(", "aoDocuments("):
        assert appel in corps, appel


def test_le_formulaire_icpe_est_alimente_par_le_referentiel_et_non_ecrit():
    """Une liste de champs recopiée dans la page finit par demander une
    grandeur que le criblage ne sait plus lire."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    assert "icpeFormulaire(CADRE.icpe_champs)" in js


# ── Le criblage n'affiche jamais un régime pour un vide ────────────────────

def test_la_note_du_regime_est_rendue_avec_le_regime():
    """« Aucune rubrique atteinte » sans sa note se lit « votre site n'est pas
    classé ». C'est la note qui dit que c'est un plancher."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function icpeRendre(")
    corps = js[i:js.index("function icpeFiche(")]
    assert "regime_site_note" in corps
    assert "regime_site_detail" in corps


def test_la_reserve_du_criblage_est_rendue_dans_la_page():
    """Elle n'est pas décorative : c'est elle qui distingue un criblage d'un
    classement, et un lecteur qui ne la voit pas croit tenir le second."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function icpeRendre(")
    corps = js[i:js.index("function icpeFiche(")]
    assert "c.reserve" in corps
    assert "c.connexes" in corps


def test_la_fiche_d_une_rubrique_sans_donnee_dit_ce_qui_manque():
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function icpeFiche(")
    corps = js[i:js.index("function travauxFormulaire(")]
    assert "a_verifier" in corps
    assert "l.manque" in corps


def test_les_trois_etats_d_une_rubrique_se_distinguent_autrement_que_par_la_couleur():
    """Une distinction qui ne tient qu'à la teinte n'existe pas pour un
    lecteur daltonien. Les badges portent aussi une forme — pointillé,
    opacité — et un texte."""
    h = lire("ingenierie-datacenter.html")
    for cls in ("ig-icpe-b-declenchee", "ig-icpe-b-a_verifier",
                "ig-icpe-b-ecartee"):
        assert ".%s{" % cls in h, cls
    i = h.index(".ig-icpe-b-a_verifier{")
    assert "dashed" in h[i:i + 120]
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    assert "badge_nom" in js or "r.badge" in js


# ── La phase travaux ───────────────────────────────────────────────────────

def test_le_plan_de_travaux_se_recalcule_quand_les_reglages_changent():
    """Deux réglages seulement, et ils changent le plan pour de bon. Un plan
    figé sur le premier choix afficherait une construction neuve à quelqu'un
    qui vient de saisir un rétrofit."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function travauxFormulaire(")
    corps = js[i:js.index("function travauxPlan(")]
    assert 'addEventListener("change", travauxPlan)' in corps


def test_l_orphelinat_d_une_operation_est_rendu_et_non_masque():
    """Retirer les essais du plan parce que personne n'est payé pour les faire
    est ce qui produit une réception sans essai intégré. La mention doit
    s'afficher."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function travauxRendre(")
    corps = js[i:js.index("function aoDocuments(")]
    assert "sans_titulaire" in corps
    assert "ig-tr-orph" in corps


def test_les_acteurs_portent_la_couleur_de_leur_lien():
    """On ne pilote pas de la même façon quelqu'un qui doit un résultat et
    quelqu'un dont l'avis est réglementé. Les afficher au même rang ferait
    donner des instructions à qui n'en reçoit pas."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    assert "ig-tr-a-" in js
    h = lire("ingenierie-datacenter.html")
    import travaux_dc
    for lien in travaux_dc.LIENS:
        assert ".ig-tr-a-%s{" % lien in h, lien


def test_chaque_solution_affiche_son_cout_et_son_moment():
    """Une solution dont le prix n'est pas dit ne se décide pas ; une solution
    posée après la consultation se négocie au lieu de s'appliquer."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function travauxRendre(")
    corps = js[i:js.index("function aoDocuments(")]
    for champ in ("s.obtient", "s.coute", "s.quand_poser"):
        assert champ in corps, champ


# ── L'appel d'offres ───────────────────────────────────────────────────────

def test_les_pieces_sont_transmises_sans_etre_deposees():
    """On lit un dossier de consultation avant de décider s'il vaut la peine
    d'être conservé. Les pièces d'une consultation à laquelle on ne répondra
    pas n'ont rien à faire dans la base de connaissance."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function aoDocuments(")
    corps = js[i:js.index("function aoLire(")]
    assert "multiple" in corps, "plusieurs pièces à la fois"
    assert "/api/datacenter/depot" not in corps


def test_les_citations_sont_rendues_avec_leur_position():
    """Un relevé sans repère ne se vérifie pas. « À 38 % du document » suffit
    à retrouver le passage dans un CCAP de quatre-vingts pages."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function aoRendre(")
    corps = js[i:js.index("function aoCandidature(")]
    assert "c.part" in corps
    assert "blockquote" in corps


def test_ce_qui_n_a_pas_ete_trouve_est_rendu_comme_tel():
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function aoRendre(")
    corps = js[i:js.index("function aoCandidature(")]
    assert "r.note" in corps
    assert "ig-ao-rk" in corps, "et se distingue visuellement d'un relevé trouvé"


def test_les_pieces_absentes_du_dossier_sont_rendues():
    """C'est l'information la plus utile de l'analyse, et celle qu'on remarque
    le moins."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function aoRendre(")
    corps = js[i:js.index("function aoCandidature(")]
    assert "a.manquantes" in corps
    assert "a.inconnues" in corps


def test_les_fichiers_ecartes_sont_rendus_apres_le_reste():
    """LE PIÈGE D'ORDRE. `aoRendre` écrase le contenu du bloc : appelé avant,
    le relevé des fichiers écartés disparaîtrait sans laisser de trace."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function aoRendre(")
    corps = js[i:js.index("function aoCandidature(")]
    assert corps.index("out.innerHTML = h") < corps.index("aoIgnores(")


def test_la_rediction_d_une_note_est_annoncee_depuis_le_serveur():
    """Une page qui devinerait quel livrable rédige quelle pièce se tromperait
    le jour où l'un des deux changerait de nom."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function aoCandRendre(")
    corps = js[i:i + 3000]
    assert "p.redaction" in corps


def test_les_pieces_bloquantes_se_distinguent_dans_le_dossier_de_candidature():
    """Traiter quatorze pièces avec la même urgence revient à n'en traiter
    aucune correctement."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    assert "ig-ao-cpb" in js
    assert ".ig-ao-cpb{" in lire("ingenierie-datacenter.html")


# ── Les réserves sur la page elle-même ─────────────────────────────────────

def test_la_page_dit_que_le_criblage_ne_classe_pas():
    """Dans le corps de la page, pas seulement dans la réponse du serveur :
    un lecteur qui n'a pas lancé le criblage doit déjà le savoir."""
    h = lire("ingenierie-datacenter.html")
    i = h.index('id="ig-icpe"')
    entete = h[i:i + 2500]
    assert "pas un classement" in entete.lower()
    assert "préfet" in entete


def test_la_page_dit_que_les_formulaires_ne_se_generent_pas():
    """DC1, DC2 et la déclaration sur l'honneur portent des déclarations dont
    la fausseté est sanctionnée."""
    h = lire("ingenierie-datacenter.html")
    i = h.index('id="ig-limites"')
    limites = h[i:i + 4000]
    assert "ne se génèrent pas" in limites
    assert "habilitée" in limites


def test_les_limites_de_la_page_couvrent_les_trois_ajouts():
    h = lire("ingenierie-datacenter.html")
    i = h.index('id="ig-limites"')
    limites = h[i:i + 4000].lower()
    for sujet in ("icpe", "consultation", "candidature"):
        assert sujet in limites, sujet


# ── Le bloc des fluides, sur la page de calcul ─────────────────────────────

def test_le_bloc_des_fluides_existe_et_se_met_a_jour_au_changement():
    """La liste proposait sept libellés opaques. Le lecteur qui ne connaissait
    pas la différence choisissait au hasard — et produisait une étude complète,
    d'apparence normale, sur une conception qu'il n'aurait pas retenue."""
    assert 'id="dc-fluides"' in lire("datacenter.html")
    js = sans_commentaires_js(lire("datacenter.js"))
    assert "function expliquerFluides(" in js
    i = js.index('$("#dc-form").addEventListener("change"')
    assert "expliquerFluides()" in js[i:i + 400]


def test_le_bloc_des_fluides_rend_les_cinq_choses_demandees():
    """Principe, condition, coût, contrainte, erreur classique — dans l'ordre
    où on les demande en réunion."""
    js = sans_commentaires_js(lire("datacenter.js"))
    i = js.index("function expliquerFluides(")
    corps = js[i:i + 2600]
    for champ in ("m.principe", "m.quand", "m.cout", "m.contrainte", "m.erreur"):
        assert champ in corps, champ


def test_le_bloc_des_fluides_annonce_les_conduites_hors_liste():
    """Le free-chilling n'est pas dans la liste déroulante. Le taire ferait
    croire qu'il n'existe pas ; le présenter comme une famille ferait chercher
    une option absente."""
    js = sans_commentaires_js(lire("datacenter.js"))
    assert "function conduitesDe(" in js
    i = js.index("function conduitesDe(")
    corps = js[i:i + 900]
    assert "porte_par" in corps
    assert "!M[k].famille" in corps


def test_un_choix_absent_dit_ce_qui_manque_au_lieu_de_rester_vide():
    """Un bloc vide se lit comme un bloc cassé."""
    js = sans_commentaires_js(lire("datacenter.js"))
    i = js.index("function expliquerFluides(")
    corps = js[i:i + 1300]
    assert "Choisissez une famille" in corps


def test_le_bloc_des_fluides_ferme_sur_la_source():
    """Ces descriptions cadrent un métier, elles ne fixent aucune performance.
    Servies sans leur réserve, elles se lisent comme des spécifications."""
    js = sans_commentaires_js(lire("datacenter.js"))
    i = js.index("function expliquerFluides(")
    assert "modes_source" in js[i:i + 2800]


def test_les_classes_du_bloc_des_fluides_sont_definies():
    """Une classe employée par le rendu et absente de la feuille produit un
    bloc sans mise en forme — lisible en apparence, illisible en pratique."""
    h = lire("datacenter.html")
    js = sans_commentaires_js(lire("datacenter.js"))
    i = js.index("function expliquerFluides(")
    corps = js[i:i + 2800]
    for cls in sorted(set(re.findall(r'class="(dc-fl[a-z-]*)"', corps))):
        assert ".%s{" % cls in h, cls


# ── La section de programme ────────────────────────────────────────────────

def test_la_section_de_programme_existe_avec_ses_zones():
    h = lire("ingenierie-datacenter.html")
    assert 'id="ig-prog"' in h
    for zid in ("ig-prog-sites", "ig-prog-out", "ig-prog-msg",
                "ig-prog-add", "ig-prog-go"):
        assert 'id="%s"' % zid in h, zid


@pytest.mark.parametrize("fn", ["progFormulaire", "progAjouter", "progLire",
                                "progConsolider", "progRendre", "progTotal",
                                "nombreFr"])
def test_chaque_fonction_de_programme_est_definie_et_referencee(fn):
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    assert "function %s(" % fn in js, fn
    assert len(re.findall(r"\b%s\b" % re.escape(fn), js)) >= 2, fn


@pytest.mark.parametrize("bouton,fonction", [
    ("ig-prog-add", "progAjouter"),
    ("ig-prog-go", "progConsolider"),
])
def test_les_boutons_de_programme_portent_leur_ecouteur(bouton, fonction):
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    m = re.search(r'\$\("#%s"\)+\s*b\.addEventListener\("click",\s*(\w+)'
                  % re.escape(bouton), js)
    assert m and m.group(1) == fonction, bouton


def test_un_total_affiche_son_perimetre_contre_le_chiffre():
    """LE PÉRIMÈTRE N'EST PAS UNE NOTE DE BAS DE PAGE : c'est lui qui décide
    de ce que le total vaut. Un sous-total doit se distinguer d'un total à
    l'œil, pas seulement au texte."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function progTotal(")
    corps = js[i:js.index("function nombreFr(")]
    assert "SOUS-TOTAL" in corps
    assert "sites_absents" in corps
    assert "ig-prog-partiel" in corps
    assert ".ig-prog-partiel{" in lire("ingenierie-datacenter.html")


def test_un_ratio_non_rendu_affiche_son_motif():
    """« — » sans motif se lit comme une panne ; « les deux grandeurs ne
    couvrent pas les mêmes sites » se lit comme une consigne."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function progRendre(")
    corps = js[i:i + 8000]
    assert "pourquoi" in corps
    assert "ig-prog-w" in corps


def test_la_mise_en_garde_multi_pays_ne_s_affiche_que_si_elle_s_applique():
    """Une mise en garde servie à un programme national apprend à ne plus les
    lire."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function progRendre(")
    corps = js[i:i + 8000]
    assert "v.par_pays.multi_pays" in corps
    j = corps.index("v.par_pays.multi_pays")
    assert "ce_qui_ne_se_replique_pas" in corps[j:j + 700]


def test_ce_qui_ne_se_consolide_pas_est_rendu_et_non_omis():
    """Une absence silencieuse se lirait comme un oubli."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function progRendre(")
    corps = js[i:i + 9000]
    assert "non_consolidables" in corps


def test_une_ligne_de_site_vide_n_est_pas_comptee():
    """La compter gonflerait l'effectif du programme et ferait apparaître un
    « site sans nom » dans les absents de chaque total."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function progLire(")
    corps = js[i:js.index("function progConsolider(")]
    assert "rempli" in corps
    assert "if (rempli)" in corps


def test_la_page_dit_que_consolider_n_est_pas_additionner():
    """Dans le corps de la page, pas seulement dans la réponse : un lecteur
    qui n'a pas encore consolidé doit déjà le savoir."""
    h = lire("ingenierie-datacenter.html")
    i = h.index('id="ig-prog"')
    entete = h[i:i + 2500]
    assert "n'est pas additionner" in entete
    assert "pondère" in entete


def test_les_limites_couvrent_la_vue_de_programme():
    h = lire("ingenierie-datacenter.html")
    i = h.index('id="ig-limites"')
    limites = h[i:i + 5000]
    assert "consolide ce qu'on lui donne" in limites
    assert "nationale" in limites
