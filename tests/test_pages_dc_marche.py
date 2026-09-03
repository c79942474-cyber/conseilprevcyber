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
import html
import json
import os
import re
import subprocess
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc  # noqa: E402


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
    ("ig-reseau", "raccordement au réseau"),
    ("ig-travaux", "phase travaux"),
    ("ig-ao", "appel d'offres"),
])
def test_chaque_section_ajoutee_est_dans_la_page(ancre, titre):
    h = lire("ingenierie-datacenter.html")
    assert 'id="%s"' % ancre in h, ancre
    i = h.index('id="%s"' % ancre)
    assert titre.lower() in h[i:i + 400].lower(), (ancre, titre)


def test_les_zones_de_rendu_des_sections_ajoutees_existent():
    """Une fonction qui écrit dans un identifiant absent échoue en silence :
    `$("#…")` rend null, et le rendu ne se produit jamais."""
    h = lire("ingenierie-datacenter.html")
    for zid in ("ig-icpe-form", "ig-icpe-out", "ig-icpe-msg",
                "ig-icpe-bareme",
                "ig-res-form", "ig-res-out", "ig-res-msg",
                "ig-tr-form", "ig-tr-out", "ig-tr-msg",
                "ig-ao-depot", "ig-ao-out", "ig-ao-cand-out", "ig-ao-msg",
                "ig-ao-fiche", "ig-ao-rempli"):
        assert 'id="%s"' % zid in h, zid


# ── Le câblage : ce qui est défini est appelé, ce qui est appelé existe ────

@pytest.mark.parametrize("fn", ["icpeFormulaire", "icpeCribler", "icpeRendre",
                                "icpeFiche", "icpeBareme", "icpeEchelles",
                                "icpeSeuilEtat", "icpeVariante",
                                "icpeEchelleTexte", "icpeBaremeChamp",
                                "reseauFormulaire",
                                "reseauChiffrer", "reseauRendre", "reseauMode",
                                "reseauNonServi", "reseauProduction",
                                "travauxFormulaire",
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
    ("ig-res-go", "reseauChiffrer"),
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


def test_les_formulaires_ajoutes_sont_dessines_au_demarrage():
    """Un bouton sans formulaire au-dessus n'invite personne. Les formulaires
    se dessinent d'emblée ; aucun ne calcule tant qu'on ne le demande pas."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function démarrer(")
    corps = js[i:i + 6000]
    for appel in ("icpeFormulaire(", "icpeBareme(", "reseauFormulaire(",
                  "travauxFormulaire(", "aoDocuments("):
        assert appel in corps, appel


# ── Les seuils de la nomenclature, là où on les saisit ────────────────────

def test_aucun_seuil_de_la_nomenclature_n_est_ecrit_dans_le_rendu():
    """LA FAUTE QUE CETTE RÈGLE EMPÊCHE. La nomenclature est modifiée par
    décret plusieurs fois par an. Un seuil recopié dans la page continuerait
    de s'afficher, juste et rassurant, longtemps après être devenu faux — et
    il contredirait en silence le criblage, qui, lui, aurait été mis à jour.

    LA RECHERCHE EST CIBLÉE SUR LES DEUX FONCTIONS QUI DESSINENT UNE ÉCHELLE,
    et c'est délibéré. Balayer tout le fichier pour des nombres comme 1 ou 50
    remonterait des largeurs de fenêtre et des découpes de chaîne : une règle
    qu'il faut assortir d'exceptions cesse vite d'être lue. Un seuil en dur ne
    peut vivre qu'à l'endroit où une échelle se compose, et c'est là qu'on
    regarde — toutes valeurs confondues, converties comprises."""
    import icpe_dc
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    seuils = set()
    for r in icpe_dc.RUBRIQUES.values():
        for cle in r:
            if cle.startswith("seuils"):
                seuils |= {bas for bas, _h, _rg in r[cle] if bas}
    b = icpe_dc.bareme()
    for e in b["champs"].values():
        for v in e["variantes"]:
            seuils |= {p["a_partir_de_champ"] for p in v["paliers"]
                       if p["a_partir_de_champ"]}
    assert len(seuils) >= 8, "trop peu de seuils cherchés pour prouver quoi que ce soit"
    for nom, fin in (("icpeEchelleTexte", "function icpeSeuilEtat("),
                     ("icpeBareme", "function icpeVariante(")):
        i = js.index("function %s(" % nom)
        corps = js[i:js.index(fin)] if fin in js[i:] else js[i:i + 3000]
        for v in sorted(seuils):
            formes = {str(v)}
            if float(v).is_integer():
                formes.add(str(int(v)))
            for forme in formes:
                motif = r"(?<![\d.])%s(?![\d.])" % re.escape(forme)
                assert not re.search(motif, corps), (
                    "le seuil %s est écrit dans %s" % (forme, nom))


def test_le_bareme_et_les_echelles_viennent_du_serveur():
    """Les seuils, les conversions et les valeurs d'essai sont calculés par le
    module qui connaît la nomenclature ET les unités de saisie. La page les
    lit ; elle ne les recompose pas."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    assert "CADRE.icpe_bareme" in js
    i = js.index("function icpeBaremeChamp(")
    assert "b.champs" in js[i:i + 400]


def test_la_variante_de_bareme_se_choisit_sur_le_discriminant_servi():
    """TROIS RUBRIQUES CHANGENT DE BARÈME selon le projet. La correspondance
    entre la réponse et le barème applicable appartient au module — une règle
    écrite dans la page divergerait du criblage au premier alinéa modifié, et
    le lecteur viserait un seuil que le criblage n'applique pas."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function icpeVariante(")
    corps = js[i:i + 1200]
    assert "d.valeurs" in corps and "d.sinon" in corps
    # Aucune clé de variante n'est écrite dans la page : elles viennent
    # toutes de la table du module.
    import icpe_dc
    cles = {v["cle"] for r in icpe_dc.RUBRIQUES
            for v in icpe_dc._variantes(r) if v["cle"] != "defaut"}
    for cle in cles:
        assert '"%s"' % cle not in corps, cle


def test_le_depassement_de_seuil_se_voit_pendant_la_saisie():
    """Un contour qui n'apparaîtrait qu'après avoir demandé le criblage
    arriverait trop tard : le lecteur a déjà quitté le champ, et il ne fait
    plus le lien entre la valeur qu'il vient de taper et le régime."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function icpeFormulaire(")
    corps = js[i:js.index("function icpeBareme(")]
    assert 'addEventListener("input"' in corps
    assert "icpeSeuilEtat" in corps


def test_le_depassement_ne_se_signale_pas_que_par_la_couleur():
    """UN CONTOUR ROUGE SEUL EST MUET pour un lecteur d'écran, et invisible
    pour qui ne distingue pas les rouges. Le régime atteint s'écrit — et il
    le faut de toute façon : les trois régimes ne coûtent pas le même délai,
    et un contour ne dit pas lequel vient d'être déclenché."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function icpeSeuilEtat(")
    corps = js[i:i + 2000]
    assert "ig-depasse" in corps
    assert "regime_nom" in corps
    assert "ig-franchi" in corps


def test_les_valeurs_d_essai_remplissent_le_champ_et_ne_le_prefixent_pas():
    """Le menu PROPOSE, il ne décide pas : il retombe sur son entrée vide
    après avoir rempli le champ, de sorte qu'aucune valeur ne reste
    présélectionnée dans le formulaire."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function icpeFormulaire(")
    corps = js[i:js.index("function icpeBareme(")]
    j = corps.index("ig-seuil-sel")
    assert "cible.value = sel.value" in corps
    assert "sel.value = \"\"" in corps[j:]


def test_le_formulaire_de_raccordement_est_alimente_par_le_referentiel():
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    assert "reseauFormulaire(CADRE.reseau_champs)" in js


def test_les_termes_du_calcul_non_servi_sont_tous_rendus():
    """UN POURCENTAGE NU NE SE DISCUTE PAS. Sans la décomposition, le lecteur
    ne peut ni contester le chiffre auprès du gestionnaire de réseau, ni le
    défendre auprès d'un client : il ne peut que le croire ou le rejeter.

    Éprouvé sur les CLÉS du résultat réellement lues par le rendu, et non sur
    la présence d'un mot : une section qui parlerait des termes sans les lire
    passerait une règle de vocabulaire."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function reseauNonServi(")
    corps = js[i:i + 4000]
    for cle in ("puissance_tenue_en_effacement_kw", "puissance_appelee_kw",
                "deficit_horaire_kw", "non_servi_brut_kwh_an",
                "creux_de_rattrapage_kwh_an", "reporte_kwh_an",
                "non_servi_net_kwh_an"):
        assert cle in corps, cle


def test_le_plafonnement_du_report_est_rendu_comme_un_bandeau():
    """Les deux conduites sont OPPOSÉES : tant que le report n'est pas
    plafonné, chercher de la flexibilité réduit encore le chiffre ; une fois
    plafonné, cela ne sert plus à rien et seule de la puissance ferme agit.
    Rien d'autre sur la page ne le dit."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function reseauNonServi(")
    assert "plafonne_par_le_creux" in js[i:i + 4000]


def test_aucune_infobulle_n_est_posee_sur_une_option_de_menu():
    """UNE INFOBULLE MORTE EST PIRE QU'UNE ABSENCE D'INFOBULLE : la relecture
    la voit, le lecteur ne la voit jamais. Le menu déroulant natif est dessiné
    par le système d'exploitation, qui ignore les attributs de la page — un
    `data-info` posé sur une <option> ne s'affichera dans aucun navigateur.

    L'explication d'une option se montre APRÈS sélection, dans un bloc de la
    page. C'est le motif que suit déjà l'identification du projet, et cette
    règle empêche qu'un nouveau formulaire y déroge sans que rien ne le dise.

    Éprouvé sur la construction du balisage, pas sur le rendu : `info(...)`
    rend une chaîne d'attributs, et la faute consiste à la concaténer dans une
    balise <option>."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    fautes = re.findall(r"<option[^>]{0,120}?\+\s*info\(", js)
    assert not fautes, (
        "%d infobulle(s) posée(s) sur une <option> : elles ne s'afficheront "
        "jamais" % len(fautes))
    # Et dans le HTML servi tel quel.
    h = lire("ingenierie-datacenter.html")
    assert not re.findall(r"<option[^>]*data-info=", h)


def test_le_repere_publie_est_rendu_avec_son_auteur():
    """Un ordre de grandeur de marché affiché sans son auteur se lit comme un
    résultat du moteur — c'est exactement ce que la discipline de l'état de
    l'art existe pour empêcher."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function reseauMode(")
    corps = js[i:i + 2500]
    assert "repere.editeur" in corps
    assert "repere.enonce" in corps


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


# ── Le bloc de qualification du niveau ─────────────────────────────────────

def test_le_bloc_de_qualification_existe_sous_la_disponibilite():
    """Il PROLONGE le champ « niveau visé » plutôt que d'ouvrir une section :
    le champ recueille une intention, ce bloc constate ce que la topologie
    permettrait de revendiquer."""
    h = lire("ingenierie-datacenter.html")
    assert 'id="ig-qualif"' in h
    assert h.index('id="ig-dispo"') < h.index('id="ig-qualif"')


@pytest.mark.parametrize("fn", ["bâtirQualification", "qualifierLire",
                                "qualifier", "qualifierRendre"])
def test_chaque_fonction_de_qualification_est_definie_et_referencee(fn):
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    assert "function %s(" % fn in js, fn
    assert len(re.findall(r"\b%s\b" % re.escape(fn), js)) >= 2, fn


def test_le_bloc_se_dessine_avec_le_formulaire_de_disponibilite():
    """Un bouton sans listes au-dessus n'invite personne."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function bâtirDisponibilite(")
    corps = js[i:js.index("function bâtirQualification(")]
    assert "bâtirQualification()" in corps


def test_les_sous_systemes_viennent_du_referentiel_et_ne_sont_pas_ecrits():
    """Une liste recopiée dans la page finit par noter un sous-système que le
    calcul ne connaît plus."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function bâtirQualification(")
    corps = js[i:js.index("function qualifierLire(")]
    assert "CADRE.tier_sous_systemes" in corps
    assert "CADRE.tier_ordre" in corps


def test_le_sous_systeme_limitant_se_distingue_a_l_oeil():
    """C'est lui, et lui seul, qui décide du niveau du site. Le noyer dans la
    liste ferait rater l'information."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function qualifierRendre(")
    corps = js[i:i + 6000]
    assert "s.limitant" in corps
    assert "ig-qua-lim" in corps
    assert ".ig-qua-lim{" in lire("ingenierie-datacenter.html")


def test_un_plafond_se_distingue_d_un_verdict_autrement_que_par_le_mot():
    """Un lecteur pressé ne lit pas la mention : le cadre doit le dire aussi."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function qualifierRendre(")
    corps = js[i:i + 6000]
    assert "q.plafond" in corps
    assert "ig-qua-plafond" in corps
    h = lire("ingenierie-datacenter.html")
    assert ".ig-qua-plafond{" in h
    j = h.index(".ig-qua-plafond{")
    assert "dashed" in h[j:j + 140]


def test_un_sous_systeme_non_note_affiche_pourquoi():
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function qualifierRendre(")
    corps = js[i:i + 6000]
    assert "non_evalue" in corps
    assert "s.pourquoi" in corps


def test_la_reserve_et_la_source_ferment_le_bloc():
    """Elles distinguent une qualification d'une certification. Un bloc qui
    les omettrait ferait lire un niveau décerné."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function qualifierRendre(")
    corps = js[i:i + 7000]
    assert "q.reserve" in corps
    assert "q.source" in corps


def test_les_essais_a_demontrer_sont_rendus_avec_l_ecart():
    """Le niveau se constate par des essais dont l'issue est observable. Un
    écart sans ses essais laisse croire qu'atteindre les exigences suffit."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    i = js.index("function qualifierRendre(")
    corps = js[i:i + 7000]
    assert "essais_a_demontrer" in corps


def test_la_page_dit_la_regle_du_plus_bas_avant_tout_calcul():
    """Un lecteur qui n'a pas encore qualifié doit déjà savoir que son site
    vaut son maillon le plus faible."""
    h = lire("ingenierie-datacenter.html")
    i = h.index('id="ig-qualif"')
    entete = h[max(0, i - 900):i + 200]
    assert "PLUS BAS" in entete
    assert "moyenne" in entete


# ═══════════════════════════════════════════════════════════════════════════
#  UN SCRIPT RÉFÉRENCÉ QUI N'EST PAS SERVI REND UNE PAGE INERTE, EN SILENCE
# ═══════════════════════════════════════════════════════════════════════════

def test_chaque_script_reference_par_une_page_est_REELLEMENT_SERVI(admin):
    """LE DÉFAUT QUI A MOTIVÉ CETTE RÈGLE, ET QUI NE LEVAIT RIEN.

    Une page neuve référençait `/ia-factory.js`. Le fichier était sur le
    disque, son URL était versionnée dans `_ASSETS_VERSIONNES` — mais chaque
    script de ce site est servi par une route EXPLICITE, et celle-là n'avait
    pas été écrite. Le serveur rendait 404 ; la page, elle, se servait
    parfaitement en 200. Résultat pour le visiteur : aucun secteur, aucun
    champ, aucun parcours — une page morte. RIEN NE LE SIGNALAIT côté serveur,
    parce qu'une page qui référence un script absent reste une page valide, et
    la règle qui existait vérifiait la liste de versionnage, pas le service.

    LA PROPRIÉTÉ, ICI, EST GLOBALE : tout script que N'IMPORTE QUELLE page
    référence doit répondre 200 avec un type JavaScript. Elle ne demande à
    aucune liste ; elle demande au serveur. L'administrateur est employé parce
    qu'il atteint toutes les pages — une page fermée porte les mêmes scripts.
    """
    import app as _app
    vus, fautes, pages_sautees = {}, [], 0
    for chemin in sorted(_app.PAGES):
        r = admin.get(chemin)
        if r.status_code != 200:
            pages_sautees += 1
            continue
        for src in re.findall(r'<script src="(/[^"?]+\.js)', r.get_data(as_text=True)):
            vus.setdefault(src, chemin)
    assert vus, "aucune page ne référence de script : la règle ne mesurerait rien"
    for src, ou in sorted(vus.items()):
        rr = admin.get(src)
        t = (rr.headers.get("Content-Type") or "").lower()
        if rr.status_code != 200 or "javascript" not in t:
            fautes.append("%s (référencé par %s) → %d, type %r"
                          % (src, ou, rr.status_code, t))
    assert not fautes, (
        "%d script(s) référencé(s) mais non servi(s) — les pages concernées "
        "sont inertes dans un navigateur :\n  %s" % (len(fautes), "\n  ".join(fautes)))


# ═══════════════════════════════════════════════════════════════════════════
#  LE REMPLISSAGE DES PIÈCES DANS LA PAGE
# ═══════════════════════════════════════════════════════════════════════════

def test_la_fiche_du_candidat_ne_quitte_pas_le_navigateur():
    """CE QUE LA PAGE PROMET, LE SCRIPT DOIT LE TENIR. La page annonce que la
    fiche « ne quitte pas ce navigateur ». Un envoi au serveur POUR ÊTRE
    CONSERVÉ démentirait la promesse — et personne ne le verrait, puisque la
    page continuerait de s'afficher normalement."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    # LA CLÉ CHERCHÉE DANS TOUT LE FICHIER NE PROUVAIT RIEN : elle figure aussi
    # dans la LECTURE. Mutation vérifiée — l'écriture supprimée, la règle
    # restait verte et la fiche se perdait à chaque rechargement. On borne donc
    # à la fonction qui écrit, et à celle qui lit.
    enr = js[js.index("function aoFicheEnregistrer("):]
    enr = enr[:enr.index("\n  }")]
    assert 'setItem("ao-fiche-v1"' in enr, (
        "la fiche n'est pas écrite localement : elle se perd au rechargement")
    cha = js[js.index("function aoFicheCharger("):]
    cha = cha[:cha.index("\n  }")]
    assert 'getItem("ao-fiche-v1"' in cha, "la fiche n'est jamais relue"
    # Le seul point qui reçoit la fiche est le calcul, et il ne conserve rien —
    # c'est éprouvé côté route. Aucun autre appel ne doit l'emporter.
    envois = re.findall(r'demander\(\s*"(/api/[^"]+)"[^;]*?AO_FICHE', js, re.S)
    assert set(envois) <= {"/api/datacenter/marche/remplir",
                           "/api/datacenter/marche/export"}, envois


def test_la_page_ne_recalcule_pas_le_critere_de_remplissage():
    """LE CRITÈRE QUI FAIT QU'UNE RUBRIQUE EST REMPLIE EST UNE DÉCISION DU
    MODULE. Recopié dans le script, il dériverait au premier ajout de rubrique,
    et une pièce annoncée prête pour un critère périmé est pire qu'une pièce
    annoncée incomplète."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    for interdit in ('a_declarer"] ==', "compte.a_saisir === 0",
                     "compte.non_trouve === 0", 'statut = "rempli"'):
        assert interdit not in js, (
            "le script recalcule un critère au lieu de le recevoir : %r"
            % interdit)
    assert "l.statut_nom" in js or "statut_nom" in js, (
        "la page réécrit le libellé des statuts au lieu de l'afficher")


def test_la_saisie_de_la_fiche_relance_le_remplissage():
    """« EN TEMPS RÉEL » VEUT DIRE : à la frappe. Un formulaire qu'il faut
    valider par un bouton n'est pas ce qui a été demandé, et un bouton oublié
    laisse le lecteur devant des pièces vides en croyant avoir saisi."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    bloc = js[js.index("function aoFicheRendre("):]
    bloc = bloc[:bloc.index("\n  var AO_ETAT_CLASSE")]
    assert 'addEventListener("input"' in bloc and "aoRemplir()" in bloc, (
        "la fiche ne relance rien quand on la saisit")
    # ET L'ANALYSE AUSSI : les rubriques qui viennent des pièces de l'acheteur
    # doivent se remplir au moment où l'analyse arrive.
    # LA PRÉSENCE DU MOT NE PROUVE RIEN : `if (false) aoRemplir(true);` la
    # satisfait. Mutation vérifiée. On exige donc que l'appel soit un FRÈRE du
    # rendu — même niveau d'indentation, aucune condition entre les deux —,
    # ce qui est la propriété réelle : le remplissage suit l'analyse, toujours.
    ana = js[js.index("function aoAnalyser("):]
    ana = ana[:ana.index("function aoIgnores(")]
    lignes = ana.split("\n")
    i = next(k for k, l in enumerate(lignes) if "aoRendre(j.analyse)" in l)
    j = next((k for k, l in enumerate(lignes) if "aoRemplir(" in l), None)
    assert j is not None and j > i, (
        "l'analyse déposée ne remplit rien : il faudrait un second geste")
    entre = "\n".join(lignes[i + 1:j])
    assert not re.search(r"\bif\b|\?|&&|\|\|", entre), (
        "le remplissage qui suit l'analyse est sous condition : %r" % entre)
    creux = lambda l: len(l) - len(l.lstrip())
    assert creux(lignes[j]) == creux(lignes[i]), (
        "le remplissage n'est pas au même niveau que le rendu : il dépend de "
        "quelque chose")


def test_le_debounce_existe_et_n_est_pas_zero():
    """UNE REQUÊTE PAR FRAPPE FERAIT VINGT ALLERS-RETOURS POUR UNE LIGNE
    D'ADRESSE. Le délai de grâce est ce qui rend le temps réel tenable."""
    js = sans_commentaires_js(lire("ingenierie-dc.js"))
    bloc = js[js.index("function aoRemplir("):]
    bloc = bloc[:bloc.index("\n  function aoFicheRendre(")]
    m = re.search(r"\}, immediat \? 0 : (\d+)\)", bloc)
    assert m, "aucun délai de grâce dans aoRemplir"
    assert 200 <= int(m.group(1)) <= 1500, (
        "le délai de grâce est hors de l'intervalle tenable : %s ms"
        % m.group(1))
    assert "clearTimeout" in bloc, (
        "les appels s'empilent au lieu de se remplacer")


# ═══════════════════════════════════════════════════════════════════════════
#  LE MENU DES PIÈCES À PRODUIRE
# ═══════════════════════════════════════════════════════════════════════════

def _js_fonctions(*noms):
    """Les fonctions demandées, EXTRAITES DE LA SOURCE SERVIE, par comptage
    d'accolades. Recopier leur corps dans la règle éprouverait un script
    imaginaire."""
    src = lire("ingenierie-dc.js")
    out = []
    for nom in noms:
        i = src.index("\n  function %s(" % nom) + 1
        j = src.index("{", i)
        p = 1
        k = j + 1
        while p:
            if src[k] == "{":
                p += 1
            elif src[k] == "}":
                p -= 1
            k += 1
        out.append(src[i:k])
    return "\n".join(out)


def _menu_rendu(remplissage, choix=""):
    """Le HTML que `aoMenuDocs` produit RÉELLEMENT, obtenu en l'exécutant."""
    prog = (_js_fonctions("esc", "aoMenuDocs")
            + "\nconst r = JSON.parse(process.env.AO_REMPLI);"
            + "\nprocess.stdout.write(aoMenuDocs(r, process.env.AO_CHOIX || ''));\n")
    env = dict(os.environ, AO_REMPLI=json.dumps(remplissage), AO_CHOIX=choix)
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60, env=env)
    assert out.returncode == 0, out.stderr
    return out.stdout


def test_le_menu_liste_TOUTES_les_pieces_en_deux_groupes():
    """CHERCHER « optgroup » DANS LE FICHIER SERAIT VERT POUR UN GROUPE MORT
    DANS UN COMMENTAIRE. On exécute la fonction et on lit ce qu'elle rend —
    comme le navigateur."""
    r = ao_dc.remplir(fiche={"raison_sociale": "Essai"})
    h = _menu_rendu(r)
    assert h.count("<optgroup") == 2, h[:200]
    for f in ao_dc.FAMILLES_PIECE.values():
        assert f["nom"] in h, f["nom"]
    options = re.findall(r'<option value="([^"]*)"[^>]*>([^<]*)</option>', h)
    valeurs = [v for v, _ in options]
    assert valeurs[0] == "", "le menu n'offre pas de retour à « toutes »"
    assert sorted(v for v in valeurs if v) == sorted(
        p["cle"] for p in ao_dc.DOSSIER_CANDIDATURE), (
        "le menu ne liste pas les quatorze pièces : %s" % valeurs)


def test_chaque_entree_du_menu_dit_CE_QU_IL_Y_A_A_FAIRE():
    """UN MENU DE QUATORZE DOCUMENTS D'ÉGALE URGENCE N'EN SIGNALE AUCUN. Chaque
    entrée porte sa voie de production, et les bloquantes se disent."""
    r = ao_dc.remplir(fiche={"raison_sociale": "Essai"})
    h = _menu_rendu(r)
    # LE TEXTE DES OPTIONS EST ÉCHAPPÉ, et il DOIT l'être : la moitié des noms
    # de pièces portent une apostrophe. On le déséchappe pour comparer, ce qui
    # vérifie au passage que l'échappement a bien eu lieu — un nom qui
    # arriverait brut ne se déséchapperait pas en lui-même.
    options = dict(re.findall(r'<option value="([^"]+)"[^>]*>([^<]*)</option>', h))
    for p in r["pieces"]:
        brut = options[p["cle"]]
        t = html.unescape(brut)
        if "'" in p["nom"]:
            assert "&#39;" in brut, (
                "« %s » n'est pas échappé dans le menu" % p["cle"])
        assert p["nom"] in t, p["cle"]
        assert p["voie_nom"].lower() in t.lower(), (
            "« %s » ne dit pas ce qu'il y a à en faire : %r" % (p["cle"], t))
        assert ("bloquante" in t) == bool(p["bloquant"]), (p["cle"], t)


def test_le_filtre_MASQUE_et_ne_redessine_pas():
    """REDESSINER FERAIT PERDRE LES SAISIES EN COURS dans les champs propres à
    la consultation — et personne ne pense à les refaire."""
    bloc = _js_fonctions("aoBrancherMenu")
    assert "hidden" in bloc, "le filtre ne masque rien"
    for interdit in ("innerHTML", "aoRempliRendre", "aoRemplir("):
        assert interdit not in bloc, (
            "le filtre redessine (« %s ») au lieu de masquer" % interdit)


def test_le_menu_est_construit_sur_ce_que_le_SERVEUR_rend():
    """Une liste de pièces écrite dans le script se désynchroniserait du module
    à la première pièce ajoutée, et le menu proposerait un document qui
    n'existe plus — ou tairait celui qui vient d'apparaître."""
    bloc = _js_fonctions("aoMenuDocs")
    assert "r.pieces" in bloc and "r.familles" in bloc
    for cle in ("dc1", "dc2", "pouvoirs", "references", "administratif"):
        assert '"%s"' % cle not in bloc and "'%s'" % cle not in bloc, (
            "« %s » est écrit en dur dans le menu" % cle)


def _bloc_apres(source, ancre):
    """Le bloc `{ … }` qui suit l'ancre, par comptage d'accolades."""
    i = source.index(ancre)
    j = source.index("{", i)
    p, k = 1, j + 1
    while p:
        if source[k] == "{":
            p += 1
        elif source[k] == "}":
            p -= 1
        k += 1
    return source[j:k]


def test_une_piece_qu_on_ne_remplit_pas_dit_QUAND_MEME_ce_qu_elle_contient():
    """LE MENU LA NOMME : IL FAUT QUELQUE CHOSE DERRIÈRE. Neuf des quatorze
    pièces ne se remplissent pas ici. Si leur carte était vide, le menu
    proposerait un document et le lecteur ne trouverait rien — ce qui est pire
    que de ne pas l'avoir nommé.

    LA RÈGLE EST BORNÉE À LA BRANCHE, pas au fichier. Chercher « p.contient »
    dans tout le script serait vert pour un rendu mort ailleurs — le défaut
    exact corrigé deux fois dans ce dépôt. Une mutation a d'ailleurs survécu à
    la première version de cette batterie, faute de cette règle."""
    rendu = _js_fonctions("aoRempliRendre")
    branche = _bloc_apres(rendu, "if (!p.mesurable)")
    for attendu in ("p.contient", "p.produit_par", "p.voie_aide", "p.delai"):
        assert attendu in branche, (
            "la carte d'une pièce non remplissable ne montre pas « %s » : le "
            "menu la nommerait pour rien" % attendu)
    # ET LE TÉMOIN : la branche doit être conditionnée à la non-mesurabilité,
    # sinon elle s'afficherait aussi sur les pièces à rubriques et doublerait
    # ce qu'elles disent déjà.
    assert "if (!p.mesurable)" in rendu and "if (false)" not in rendu.lower()


def test_le_choix_du_menu_SURVIT_au_redessin():
    """DÉFAUT ÉPROUVÉ DANS UN NAVIGATEUR, PAS IMAGINÉ. Le bloc est redessiné à
    CHAQUE FRAPPE dans la fiche du candidat. La première version perdait la
    sélection à la première lettre tapée : on filtrait sur « Références », on
    tapait un caractère, et les quatorze cartes revenaient. Un menu qu'on doit
    reposer après chaque mot n'est pas un menu.

    LA RÈGLE EXÉCUTE LA FONCTION avec un choix, et lit l'option marquée — la
    présence du mot « selected » quelque part dans le fichier serait verte pour
    un attribut mort."""
    r = ao_dc.remplir(fiche={"raison_sociale": "Essai"})
    h = _menu_rendu(r, "references")
    marquees = re.findall(r'<option value="([^"]*)"[^>]*\bselected\b', h)
    assert marquees == ["references"], (
        "le menu redessiné ne retient pas le choix : %s" % marquees)
    # Et sans choix, AUCUNE option n'est marquée : sinon la première pièce
    # paraîtrait sélectionnée alors que tout est affiché.
    assert not re.search(r"\bselected\b", _menu_rendu(r)), (
        "une option est marquée alors qu'aucun choix n'a été fait")


def test_le_filtre_est_reapplique_apres_le_redessin_sans_faire_sauter_la_page():
    """LE MARQUAGE DE L'OPTION NE SUFFIT PAS : les cartes, elles, sont
    redessinées visibles. Le filtre doit être réappliqué — et SANS défiler,
    sous peine de faire sauter la page sous les doigts de quelqu'un qui saisit."""
    bloc = _js_fonctions("aoBrancherMenu")
    assert "appliquer(false)" in bloc, (
        "le filtre n'est pas réappliqué après le redessin")
    assert "appliquer(true)" in bloc, "le choix explicite ne défile plus"
    corps = _bloc_apres(bloc, "function appliquer(defiler)")
    assert "if (!defiler) return;" in corps, (
        "le redessin fait défiler la page : elle saute sous les doigts")
    assert "scrollIntoView" in corps.split("if (!defiler) return;")[1], (
        "le défilement n'est pas gardé par la condition")
    # ET LE CHOIX DOIT ÊTRE RETENU HORS DE LA FONCTION. Sans cela, `appliquer`
    # relit une valeur qui n'a jamais bougé : le menu change sous les yeux et
    # rien ne se filtre. Mutation vérifiée — elle survivait aux deux règles
    # précédentes, qui n'éprouvaient que le rendu et la structure.
    change = _bloc_apres(bloc, 'addEventListener("change"')
    assert "AO_DOC = sel.value" in change, (
        "le gestionnaire ne retient pas le choix : il ne survivra à rien")
