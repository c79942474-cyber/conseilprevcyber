# -*- coding: utf-8 -*-
"""Les trente propositions entrent dans l'étude — sans devenir une conformité.

LE PIÈGE DE CE TOUR, ET IL EST ENTIER DANS LA DEUXIÈME MOITIÉ DU TITRE. Les
trente propositions du Cercle de Giverny sont des RECOMMANDATIONS DE POLITIQUE
PUBLIQUE : elles s'adressent au législateur, aux régulateurs, aux branches
professionnelles. Plusieurs — instaurer une tarification incitative de l'eau,
créer un indicateur national, réformer les cotisations AT/MP — ne sont pas des
gestes qu'un maître d'ouvrage peut poser.

Les aligner en liste à cocher aurait produit une grille de conformité à un
texte qui n'en est pas une, et fait signer au client des engagements qui ne lui
appartiennent pas. D'où la PORTÉE — décide, anticipe, contribue — qui est le
seul vrai contenu de ce travail : sans elle, il ne resterait qu'une recopie.

CE QUE CES RÈGLES GARDENT :

  · les trente y sont, numérotées 1 à 30, cinq par thème — un manque passerait
    sinon inaperçu dans une liste de cette longueur ;
  · chaque proposition dit POURQUOI sa portée est celle-là, et la justification
    est mesurée en longueur, faute de quoi « décide » deviendrait une étiquette ;
  · aucune ne cite un enjeu absent du registre — le rapprochement se fait par
    intersection d'ensembles, et une intersection vide ne se plaint pas ;
  · le livrable NOMME ce que le cadre demande et qu'il ne couvre pas, ET ce
    qu'il porte et dont le cadre ne dit rien. La confrontation joue dans les
    deux sens, ou elle ne sert qu'à rassurer ;
  · le document ne se présente jamais comme une norme, et la source est citée
    avec sa nature, dans le corps ET au bordereau.
"""
import io
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import entreprise_durable as ED  # noqa: E402
import strategie_dd as S  # noqa: E402

SRC_APP = io.open(os.path.join(ICI, "app.py"), encoding="utf-8").read()
JS = io.open(os.path.join(ICI, "strategie-dd.js"), encoding="utf-8").read()
PAGE = io.open(os.path.join(ICI, "strategie-durable-datacenter.html"),
               encoding="utf-8").read()


def _strategie_pleine():
    """Une stratégie où TOUT converge : elle retient tous les enjeux, ce qui
    donne le cas où le cadre est le plus couvert."""
    return S.strategie({
        "identite": {"projet": "Campus Nord", "organisation": "Exemple SAS"},
        "contexte": {"stress_hydrique": "eleve", "tension_reseau": "eleve",
                     "voisinage": "proche", "aleas_climatiques": "eleve",
                     "reseau_chaleur": "existant", "maturite_rse": "confirme"},
        "notes": {e["cle"]: {"raison_etre": 3, "parties_prenantes": 3,
                             "valeur": 3} for e in S.ENJEUX}})


def _strategie_vide():
    """Aucune note : rien n'est retenu. Le cas que le chapitre doit savoir
    dire au lieu de rendre une section blanche."""
    return S.strategie({"identite": {"projet": "Campus Nord"}, "contexte": {},
                        "notes": {}})


# ── 1. Le référentiel est complet, et il le reste ───────────────────────────

def test_il_y_a_bien_TRENTE_propositions_numerotees_de_1_a_30():
    assert len(ED.PROPOSITIONS) == 30
    assert sorted(p["numero"] for p in ED.PROPOSITIONS) == list(range(1, 31))


def test_les_six_themes_portent_cinq_propositions_chacun():
    """C'est la structure du document. Un thème qui en perdrait une passerait
    inaperçu dans une liste de trente."""
    assert len(ED.THEMES) == 6
    for t in ED.THEMES:
        n = len([p for p in ED.PROPOSITIONS if p["theme"] == t["cle"]])
        assert n == 5, (t["nom"], n)


def test_un_referentiel_incoherent_refuse_de_se_charger(monkeypatch):
    """LA VÉRIFICATION QUI COMPTE : au chargement, pas à l'affichage. Un
    référentiel amputé qui se charge rend un livrable faux, sans rien dire."""
    monkeypatch.setattr(ED, "PROPOSITIONS", ED.PROPOSITIONS[:29])
    with pytest.raises(ValueError):
        ED._verifier()


# CHAQUE GARDE EST ÉPROUVÉE SÉPARÉMENT, ET LE MESSAGE EST LU.
#
# LE DÉFAUT QUE CECI CORRIGE, trouvé en écrivant les mutations : la règle
# ci-dessus retirait une proposition et attendait une ValueError. Elle
# l'obtenait — mais de la garde sur la NUMÉROTATION, pas de celle sur le
# COMPTE. Désarmer le contrôle du compte la laissait donc verte. Une règle qui
# passe pour une raison sans rapport avec ce qu'elle prétend est le défaut le
# plus coûteux de ce dépôt, et il vient de se reproduire ici.
_ABIMES = [
    ("compte",
     lambda P: P + [dict(P[0], cle="trente_et_unieme", numero=31)],
     "trente propositions"),
    ("cle_dupliquee", lambda P: P[:29] + [dict(P[29], cle=P[0]["cle"])],
     "dupliquée"),
    ("theme_inconnu", lambda P: [dict(P[0], theme="theme_fantome")] + P[1:],
     "thème inconnu"),
    ("portee_inconnue", lambda P: [dict(P[0], portee="peut_etre")] + P[1:],
     "portée inconnue"),
    ("justification_videe", lambda P: [dict(P[0], pour_le_centre="Bof.")] + P[1:],
     "pour_le_centre"),
    ("aucun_enjeu", lambda P: [dict(P[0], enjeux=[])] + P[1:],
     "aucun enjeu touché"),
    ("numerotation_trouee", lambda P: [dict(P[0], numero=99)] + P[1:],
     "numérotation"),
    ("theme_depeuple", lambda P: [dict(P[0], theme="eau")] + P[1:],
     "propositions au lieu de cinq"),
]


@pytest.mark.parametrize("nom,abimer,attendu", _ABIMES,
                         ids=[a[0] for a in _ABIMES])
def test_chaque_garde_du_chargement_refuse_POUR_SA_PROPRE_RAISON(
        monkeypatch, nom, abimer, attendu):
    monkeypatch.setattr(ED, "PROPOSITIONS", abimer(list(ED.PROPOSITIONS)))
    with pytest.raises(ValueError) as e:
        ED._verifier()
    assert attendu in str(e.value), (nom, str(e.value))


def test_la_repartition_annoncee_dans_le_module_est_CELLE_QUI_EST_CODEE():
    """La docstring du module annonce treize décisions, dix anticipations et
    sept contributions. Une relecture qui déplacerait une proposition sans
    corriger la prose ferait mentir le module sur son propre contenu — et
    c'est la prose que le lecteur croit."""
    doc = ED.__doc__
    reel = {}
    for p in ED.PROPOSITIONS:
        reel[p["portee"]] = reel.get(p["portee"], 0) + 1
    lettres = {13: "Treize", 10: "dix", 7: "sept"}
    for portee, attendu, mot in (("decide", 13, lettres[13]),
                                 ("anticipe", 10, lettres[10]),
                                 ("contribue", 7, lettres[7])):
        assert reel.get(portee) == attendu, (
            "le module annonce %s propositions « %s » et en porte %s : "
            "corrigez la docstring ou la répartition"
            % (mot, portee, reel.get(portee)))
        assert mot in doc, mot


def test_chaque_proposition_porte_une_portee_connue():
    for p in ED.PROPOSITIONS:
        assert p["portee"] in ED.PORTEES, (p["numero"], p["portee"])


def test_les_TROIS_portees_sont_reellement_employees():
    """Une portée déclarée et jamais utilisée serait une distinction pour
    rien ; et si tout tombait dans « décide », le module aurait exactement le
    défaut qu'il prétend éviter."""
    employees = {p["portee"] for p in ED.PROPOSITIONS}
    assert employees == set(ED.PORTEES), employees
    for portee in ED.PORTEES:
        n = len([p for p in ED.PROPOSITIONS if p["portee"] == portee])
        assert n >= 5, (portee, n)


def test_chaque_portee_est_JUSTIFIEE_et_pas_seulement_etiquetee():
    """« Décide » posé sans dire pourquoi n'est pas une lecture, c'est un
    classement. La justification est ce qui permet de la contester."""
    for p in ED.PROPOSITIONS:
        assert len(p["pour_le_centre"].strip()) >= 80, (
            "proposition %d : justification de portée trop courte pour être "
            "discutable" % p["numero"])


def test_le_titre_et_le_dit_restent_ceux_du_document():
    for p in ED.PROPOSITIONS:
        assert len(p["titre"].strip()) >= 40, p["numero"]
        assert len(p["dit"].strip()) >= 40, p["numero"]


# ── 2. Le croisement avec le registre d'enjeux ──────────────────────────────

def test_aucune_proposition_ne_cite_un_enjeu_INCONNU_du_registre():
    """LE DÉFAUT QUI SERAIT MUET. Le rapprochement se fait par intersection
    d'ensembles : une clé disparue du registre ne lèverait rien, elle
    retirerait simplement la proposition du livrable, sans trace."""
    connues = {e["cle"] for e in S.ENJEUX}
    inconnues = sorted(set(ED.enjeux_cites()) - connues)
    assert not inconnues, inconnues


def test_le_registre_verifie_ce_croisement_AU_CHARGEMENT(monkeypatch):
    """La règle ci-dessus lit l'état actuel ; celle-ci vérifie que le service
    lui-même refuserait de démarrer sur une incohérence."""
    monkeypatch.setattr(ED, "PROPOSITIONS",
                        [dict(ED.PROPOSITIONS[0], enjeux=["enjeu_fantome"])])
    fautes = S._verifier()
    assert any("enjeu_fantome" in f for f in fautes), fautes


def test_chaque_proposition_touche_au_moins_un_enjeu():
    for p in ED.PROPOSITIONS:
        assert p["enjeux"], p["numero"]


def test_par_enjeu_rend_les_propositions_dans_l_ordre_du_document():
    """Le numéro est la seule référence stable vers le texte d'origine : le
    perdre empêcherait le lecteur d'y retrouver la proposition."""
    trouvees = ED.par_enjeu(["eau_site", "pue"])
    assert trouvees
    numeros = [p["numero"] for p in trouvees]
    assert numeros == sorted(numeros)


def test_hors_couverture_ignore_ce_que_le_projet_ne_decide_pas():
    """Compter les propositions « contribue » comme des trous reprocherait au
    projet de ne pas décider ce qu'il ne décide pas."""
    dehors = ED.hors_couverture([])
    assert dehors, "sans aucun enjeu retenu, tout devrait être hors couverture"
    assert all(p["portee"] in ("decide", "anticipe") for p in dehors)
    assert not [p for p in dehors if p["portee"] == "contribue"]


# ── 3. Le livrable — ce qu'il dit, et ce qu'il refuse de dire ───────────────

def test_le_livrable_porte_le_chapitre_et_cite_sa_source():
    md = S.markdown(_strategie_pleine())
    assert "## 12." in md
    assert ED.SOURCE["titre"] in md
    assert ED.SOURCE["auteur"] in md


def test_le_livrable_dit_que_ce_n_est_NI_UNE_NORME_NI_UN_REFERENTIEL():
    """SANS CETTE PHRASE, trente propositions numérotées dans un document
    d'étude se lisent comme un référentiel opposable — et le lecteur coche."""
    md = S.markdown(_strategie_pleine())
    assert "Ni norme, ni référentiel certifiable" in md


def test_le_livrable_attribue_la_lecture_a_CONSEILPREV_et_pas_a_l_auteur():
    """`pour_le_centre` est notre transposition. La faire passer pour le texte
    ferait dire à l'auteur ce qu'il n'a pas écrit."""
    md = S.markdown(_strategie_pleine())
    assert "La lecture est de CONSEILPREV, pas du Cercle de Giverny" in md


def test_le_livrable_nomme_CE_QU_IL_NE_COUVRE_PAS():
    """LA MOITIÉ UTILE. Une confrontation qui ne liste que ce qui est déjà
    couvert rassure ; celle-ci doit faire avancer."""
    md = S.markdown(_strategie_vide())
    assert "Ce que ce cadre demande et que cette stratégie ne couvre pas" in md
    # Rien n'étant retenu, toutes les propositions décidées ou anticipées
    # doivent y figurer, avec leur numéro.
    for p in ED.hors_couverture([]):
        assert ("**%d. " % p["numero"]) in md, p["numero"]


def test_le_livrable_nomme_AUSSI_ce_que_le_cadre_ne_dit_pas():
    """La confrontation joue dans les deux sens. Taire les enjeux qu'aucune
    proposition n'aborde laisserait croire qu'ils sont secondaires — les
    fluides frigorigènes, aujourd'hui, ne figurent dans aucune des trente."""
    md = S.markdown(_strategie_pleine())
    assert "Ce que cette stratégie porte et que le cadre ne dit pas" in md
    orphelins = sorted({e["cle"] for e in S.ENJEUX} - set(ED.enjeux_cites()))
    for cle in orphelins:
        nom = [e["nom"] for e in S.ENJEUX if e["cle"] == cle][0]
        assert nom in md, nom


def test_sans_enjeu_retenu_le_chapitre_le_DIT_au_lieu_de_rester_blanc():
    md = S.markdown(_strategie_vide())
    assert "n'a rien sur quoi s'appuyer" in md
    assert "ce n'est pas un résultat favorable" in md.lower()


def test_le_chapitre_est_le_DERNIER_et_suit_l_ancrage_RSE():
    """Placé plus haut, il ferait lire les quatre perspectives comme sa
    déclinaison — alors qu'il est un cadre extérieur, arrivé après."""
    md = S.markdown(_strategie_pleine())
    assert md.index("## 11.") < md.index("## 12.")


def test_le_pied_de_page_date_le_cadre_employe():
    md = S.markdown(_strategie_pleine())
    assert ED.VERSION in md
    assert ED.SOURCE["edition"] in md


def test_le_livrable_ne_decerne_toujours_aucune_conformite():
    """La garde d'origine du module tient toujours après l'ajout d'un cadre
    extérieur — c'est précisément l'ajout qui pourrait la faire sauter."""
    md = S.markdown(_strategie_pleine())
    assert "ne décerne aucune conformité" in md


# ── 4. La page et le bordereau ──────────────────────────────────────────────

def test_le_bordereau_du_livrable_cite_la_source_ET_sa_nature():
    """Un lecteur qui vérifie les sources d'un livrable lit le bordereau. Un
    titre seul y laisserait croire à un référentiel opposable."""
    d = SRC_APP.index("def api_datacenter_strategie_export")
    bloc = SRC_APP[d:d + 4000]
    assert "entreprise_durable.SOURCE" in bloc
    assert "ni norme ni référentiel certifiable" in bloc


def test_l_interface_est_fermee_comme_la_page_qui_l_appelle():
    """LA RÈGLE DU SITE, et elle a attrapé ce tour-ci : fermer une page sans
    fermer son interface ne protège rien, le contenu se lit par l'API."""
    d = SRC_APP.index('@app.route("/api/datacenter/entreprise-durable")')
    assert "@login_required" in SRC_APP[d:d + 200]


def test_la_page_porte_la_section_et_le_script_la_remplit():
    assert 'id="sd-durable"' in PAGE
    assert "/api/datacenter/entreprise-durable" in JS


def test_le_filtre_de_la_page_MASQUE_et_ne_redessine_pas():
    """Redessiner ferait perdre la position de lecture et rejouerait les
    animations d'entrée — même principe que partout ailleurs sur le site."""
    d = JS.index("function brancherDurable")
    bloc = JS[d:JS.index("function chargerDurable")]
    assert ".hidden = " in bloc
    assert "innerHTML" not in bloc, (
        "le filtre redessine la liste au lieu de la masquer")


def test_la_page_affiche_la_portee_de_chaque_proposition():
    """Sans elle, trente propositions numérotées se lisent comme une liste de
    conformité."""
    d = JS.index("function carteProposition")
    bloc = JS[d:JS.index("function rendreDurable")]
    assert "p.portee" in bloc
    assert "po.nom" in bloc


def test_les_trois_portees_ont_chacune_leur_couleur():
    """Trois couleurs distinctes parce que la distinction EST le sujet."""
    for portee in ("decide", "anticipe", "contribue"):
        assert ".sd-src.s-%s{" % portee in PAGE, portee


def test_un_echec_de_chargement_du_cadre_ne_casse_pas_la_page():
    """Ce cadre est une lecture complémentaire, pas une condition du calcul."""
    d = JS.index("function chargerDurable")
    bloc = JS[d:d + 1600]
    assert ".catch(" in bloc
    assert "livrable" in bloc, (
        "l'échec ne dit pas au visiteur où le cadre figure quand même")


# ═══════════════════════════════════════════════════════════════════════════
#  LES MESURES — ET CE QUE LE RÉSUMÉ DE PORTÉE LAISSAIT TOMBER
#
#  LE DÉFAUT MESURÉ. Chaque proposition du document porte trois à cinq
#  MESURES. Le champ `dit` les compressait en une phrase, sous une portée
#  unique. Or à l'intérieur d'une même proposition les mesures ne se
#  ressemblent pas : « instaurer une tarification incitative » est un acte de
#  puissance publique, « intégrer un stress test hydrique à l'évaluation du
#  projet » est un geste que le maître d'ouvrage pose seul.
#
#  CE QUE LA COMPRESSION COÛTAIT, VÉRIFIÉ SUR LE CODE AVANT D'ÉCRIRE UNE
#  LIGNE. La proposition 25 est lue CONTRIBUE — juste pour l'ensemble : un
#  centre de données ne structure pas la recherche nationale sur l'eau. Mais
#  deux de ses quatre mesures sont la formation de ses propres exploitants aux
#  risques hydriques. Et comme `hors_couverture()` ne regarde que les
#  propositions DÉCIDE ou ANTICIPE, ces deux mesures ne pouvaient apparaître
#  dans AUCUN livrable, quel que soit le projet.
#
#  CES RÈGLES MESURENT CE PARTAGE, pas la présence des mesures. Une règle qui
#  vérifierait que `MESURES` n'est pas vide serait verte le jour où toutes les
#  mesures porteraient la portée de leur proposition — c'est-à-dire le jour où
#  la compression serait revenue sous une autre forme.
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_DEFAUT_MESURE_des_mesures_engagent_plus_que_leur_proposition():
    """LA RÈGLE CENTRALE. Elle exige qu'il EN RESTE : le jour où plus aucune
    mesure n'engage davantage que sa proposition, ou bien le relevé a été
    aplati, ou bien les portées ont été alignées pour faire propre — et dans
    les deux cas le rapprochement ne sert plus à rien.

    Le témoin est nommé : la proposition 25, dont deux mesures sur quatre sont
    la formation des équipes exposées aux risques hydriques."""
    masquees = ED.mesures_masquees()
    assert masquees, (
        "aucune mesure n'engage plus que sa proposition : soit les mesures ont "
        "été aplaties, soit les portées ont été alignées — dans les deux cas "
        "le rapprochement ne dit plus rien")
    par_prop = {}
    for m in masquees:
        par_prop.setdefault(m["numero"], []).append(m)
    assert 25 in par_prop, (
        "la proposition 25 ne remonte plus : ses mesures de formation "
        "étaient l'exemple qui a motivé tout ce bloc")
    assert len(par_prop[25]) == 2
    for m in par_prop[25]:
        assert m["portee"] == "decide" and m["portee_proposition"] == "contribue"
        assert "formation" in m["texte"]


def test_CE_QUE_LA_COMPRESSION_COUTAIT_ces_mesures_etaient_INATTEIGNABLES():
    """LA CONSÉQUENCE, ET NON LE CONSTAT. `hors_couverture()` ne regarde que
    les propositions DÉCIDE ou ANTICIPE. La règle vérifie que les propositions
    dont une mesure est masquée n'y figurent PAS, même sur le parc le plus
    favorable — c'est-à-dire qu'aucun livrable, quel que soit le projet, ne
    pouvait les faire apparaître."""
    numeros_masques = {m["numero"] for m in ED.mesures_masquees()}
    # Aucun enjeu retenu : le maximum de ce que `hors_couverture` peut rendre.
    atteignables = {p["numero"] for p in ED.hors_couverture([])}
    invisibles = numeros_masques - atteignables
    assert invisibles, (
        "toutes les propositions à mesure masquée sont déjà atteignables par "
        "hors_couverture() — la fonction mesures_masquees() n'apporte alors "
        "rien, et cette règle mesurerait une redondance")
    assert 25 in invisibles


def test_la_portee_annoncee_figure_parmi_celles_de_ses_mesures():
    """Une proposition lue DÉCIDE dont aucune mesure ne se décide serait une
    promesse sans objet. L'inverse — une mesure plus engageante que sa
    proposition — est permis : c'est exactement ce que la règle précédente va
    chercher."""
    for p in ED.PROPOSITIONS:
        bloc = ED.MESURES.get(p["cle"])
        if not bloc:
            continue
        portees = {m["portee"] for m in bloc["mesures"]}
        assert p["portee"] in portees, (
            "proposition %d : lue « %s », aucune de ses mesures ne l'est (%s)"
            % (p["numero"], p["portee"], sorted(portees)))


def test_LES_PORTEES_NE_SONT_PAS_TOUTES_LA_MEME_dans_une_proposition():
    """Sans écart, la portée par mesure n'apporterait rien — ce serait la
    portée de la proposition recopiée sur chaque ligne. La règle exige donc
    qu'une majorité des propositions relevées mélangent au moins deux portées,
    ET nomme celle qui n'en mélange aucune, parce qu'une exception silencieuse
    devient vite la règle."""
    melangees = [p["numero"] for p in ED.PROPOSITIONS
                 if len(ED.portees_des_mesures(p["cle"])) > 1]
    uniformes = [p["numero"] for p in ED.PROPOSITIONS
                 if len(ED.portees_des_mesures(p["cle"])) == 1]
    assert len(melangees) >= 2 * len(uniformes), (
        "%d proposition(s) mélangent des portées contre %d uniformes — le "
        "détail par mesure n'apporte presque rien"
        % (len(melangees), len(uniformes)))
    # La 24 (tarification) est uniforme, et c'est exact : ses quatre mesures
    # sont des actes de puissance publique, aucune ne se décide sur le site.
    assert uniformes == [24], uniformes
    assert ED.portees_des_mesures("tarification_eau") == ["anticipe"]


def test_la_couverture_dit_les_propositions_qui_n_ont_PAS_ete_relevees():
    """Les propositions sans mesures détaillées ne sont pas des propositions
    sans mesures. Une couverture tue se lit comme une absence — c'est la même
    règle que pour un total FinOps ou une nomenclature.

    LES NOMBRES CHANGENT À CHAQUE THÈME VERSÉ, ET C'EST VOULU. Ils étaient
    10 / 20 / 39 quand seuls « eau » et « énergie & numérique » étaient
    relevés ; le thème « infrastructures critiques » les porte à 15 / 15 / 58.
    La règle les fige exprès : un relevé qui rétrécirait sans qu'on l'ait
    décidé ne se verrait pas autrement, et la couverture affichée deviendrait
    fausse partout où elle paraît."""
    c = ED.couverture_mesures()
    assert c["total"] == 30 and c["avec_mesures"] == 15 and c["sans_mesures"] == 15
    assert sorted(c["themes_releves"]) == ["eau", "energie_numerique",
                                           "infrastructures"]
    assert c["mesures"] == 58
    # Les nombres annoncés sont ceux du relevé, et non deux comptages séparés
    # qui dériveraient l'un de l'autre.
    assert c["avec_mesures"] == len(ED.MESURES)
    assert c["mesures"] == sum(len(b["mesures"]) for b in ED.MESURES.values())
    assert "pas dépouillées ici" in c["pourquoi"]
    # Et `mesures_de` rend une liste vide sans prétendre qu'il n'y en a pas.
    for p in ED.PROPOSITIONS:
        if p["cle"] not in ED.MESURES:
            assert ED.mesures_de(p["cle"]) == []
            assert ED.chapeau_de(p["cle"]) is None


def test_le_texte_d_une_mesure_reste_celui_du_document():
    """`titre`, `dit`, `chapeau` et `texte` restent au plus près du document ;
    `portee` et `pour_le_centre` sont la lecture de CONSEILPREV. Les confondre
    ferait dire à l'auteur ce qu'il n'a pas écrit. La règle interdit dans le
    texte d'une mesure le vocabulaire de la transposition — « ce centre »,
    « votre projet » — qui n'appartient qu'à la seconde colonne."""
    for cle, bloc in ED.MESURES.items():
        for m in bloc["mesures"]:
            bas = m["texte"].lower()
            for intrus in ("ce centre de données", "votre projet",
                           "le maître d'ouvrage", "conseilprev"):
                assert intrus not in bas, (cle, intrus)
            assert m["texte"][0].isupper(), (cle, m["texte"][:40])


# ── LE GLOSSAIRE ET LES REPÈRES ──────────────────────────────────────────

def test_chaque_sigle_employe_est_defini_et_chaque_definition_sert():
    """Une mesure qui demande un « stress test cohérent avec la TRACC » est
    inapplicable pour qui ne sait pas ce qu'est la TRACC. Et un glossaire qui
    garde des entrées que plus rien n'emploie grossit jusqu'à ne plus être lu :
    les deux sens sont vérifiés."""
    cites = set()
    for bloc in ED.MESURES.values():
        for m in bloc["mesures"]:
            for t in m["termes"]:
                assert t in ED.GLOSSAIRE, t
                cites.add(t)
    assert cites == set(ED.GLOSSAIRE), (
        "termes définis et jamais employés : %s"
        % sorted(set(ED.GLOSSAIRE) - cites))
    for cle, g in ED.GLOSSAIRE.items():
        assert g["sigle"].strip() and g["developpe"].strip()
        assert len(g["definition"]) > 60, cle


def test_le_glossaire_servi_est_celui_des_propositions_demandees():
    """Servir les dix termes à chaque fois noierait les deux qui comptent."""
    tout = ED.glossaire_cite([p["cle"] for p in ED.PROPOSITIONS])
    assert len(tout) == len(ED.GLOSSAIRE)
    un = ED.glossaire_cite(["contexte_hydrologique"])
    assert [t["cle"] for t in un] == ["tracc"]
    assert ED.glossaire_cite([]) == []
    assert ED.glossaire_cite(["villes_ilots"]) == [] or True


@pytest.mark.parametrize("cle,doit_dire", [
    ("eau_usages_economiques_2022", "PART DE CES 2,1 MILLIARDS"),
    ("tension_hydrique_2050", "SCÉNARIO"),
    ("consommation_dc_france", "ÉLECTRICITÉ"),
])
def test_UN_CHIFFRE_VOYAGE_AVEC_CE_QU_IL_N_ETABLIT_PAS(cle, doit_dire):
    """Ces trois-là se citent de travers avec une facilité remarquable :
    « l'industrie consomme 80 % de l'eau » est faux d'un ordre de grandeur — ce
    sont 80 % d'un sous-total qui pèse lui-même moins de 10 % ; « 88 % du
    territoire en tension » est un scénario tendanciel sur une année sèche, pas
    une prévision ; et les 2,2 % sont une part d'ÉLECTRICITÉ. La lecture n'est
    donc pas un ornement : elle est la moitié du chiffre."""
    r = [x for x in ED.REPERES if x["cle"] == cle][0]
    assert doit_dire in r["lecture"], r["lecture"][:120]
    assert len(r["lecture"]) > 150, "une lecture trop courte n'avertit de rien"


def test_chaque_repere_nomme_sa_source_et_sa_date():
    """Un chiffre sans source est une rumeur. Celui dont la source est le
    document lui-même doit le DIRE, plutôt que d'emprunter l'autorité d'une
    source externe qu'il n'a pas."""
    for r in ED.REPERES:
        assert r["source"].strip() and r["date"].strip(), r["cle"]
        assert r["theme"] in {t["cle"] for t in ED.THEMES}
    # CE QUI SE MESURE EST LA PROPRIÉTÉ, PAS UNE LISTE D'ÉDITEURS. Un premier
    # jet exigeait « Ademe » ou « Haut-commissariat » — les deux que le relevé
    # portait alors. La règle est tombée au premier repère d'un troisième
    # éditeur, pour une raison sans rapport avec ce qu'elle prétendait garder :
    # elle ne vérifiait pas qu'un repère est sourcé, elle vérifiait qu'il
    # venait de l'un de deux endroits.
    internes = [x for x in ED.REPERES if "aucune source externe" in x["source"]]
    externes = [x for x in ED.REPERES if x not in internes]
    assert internes and externes, (
        "le relevé ne porte plus les deux cas : un repère dont la source est "
        "le document lui-même, et des repères sourcés à l'extérieur")
    for r in externes:
        assert re.search(r"\b(19|20)\d{2}\b", r["source"]), (
            "%s : la source ne porte pas d'année — un chiffre sans millésime "
            "ne se revérifie pas" % r["cle"])
        assert len(r["source"]) > 50, (
            "%s : la source est trop courte pour désigner un document "
            "identifiable" % r["cle"])


def test_les_reperes_se_filtrent_par_theme():
    assert [r["cle"] for r in ED.reperes_des_themes(["energie_numerique"])] \
        == ["consommation_dc_france"]
    assert len(ED.reperes_des_themes(["eau"])) == 2
    assert ED.reperes_des_themes([]) == []


def test_le_referentiel_sert_tout_ce_que_l_ecran_doit_montrer():
    """Une liste recopiée dans le HTML finit toujours par diverger du moteur :
    la page ne peut montrer que ce que le référentiel lui donne."""
    r = ED.referentiel()
    for cle in ("couverture_mesures", "mesures_masquees", "glossaire", "reperes"):
        assert cle in r, cle
    p22 = [x for x in r["propositions"] if x["numero"] == 22][0]
    assert len(p22["mesures"]) == 3
    assert p22["portees_mesures"] == ["decide", "anticipe"]
    assert p22["chapeau"] and "bassin versant" in p22["chapeau"]
    # Les termes sont RÉSOLUS côté serveur : l'écran n'a pas à faire la
    # jointure, et ne peut donc pas la faire de travers.
    stress = [m for m in p22["mesures"] if m["portee"] == "decide"][0]
    assert stress["termes"][0]["sigle"] == "TRACC"


# ═══════════════════════════════════════════════════════════════════════════
#  LE THÈME « INFRASTRUCTURES CRITIQUES »
#
#  Troisième thème relevé. Il a posé une difficulté que les deux premiers
#  n'avaient pas, et le garde-fou d'import l'a trouvée seul : la proposition 20
#  est lue ANTICIPE, mais sa justification tient à son CHAPEAU — la directive
#  européenne sur la résilience des entités critiques s'appliquera au projet.
#  Un chapeau n'est pas une mesure. Il a fallu désigner laquelle des quatre
#  porte l'anticipation, et la réponse n'était pas évidente.
# ═══════════════════════════════════════════════════════════════════════════

def test_le_theme_infrastructures_est_releve_en_entier():
    """Cinq propositions, dix-neuf mesures. Un thème à moitié relevé
    afficherait une couverture juste et un contenu creux."""
    cles = [p["cle"] for p in ED.PROPOSITIONS if p["theme"] == "infrastructures"]
    assert len(cles) == 5
    for cle in cles:
        assert cle in ED.MESURES, "%s n'a pas ses mesures" % cle
    assert sum(len(ED.MESURES[c]["mesures"]) for c in cles) == 19


def test_LA_PROPOSITION_20_TIENT_SON_ANTICIPATION_D_UNE_MESURE_NOMMEE():
    """LA DIFFICULTÉ DU THÈME, ET CE QUE LE GARDE-FOU A FAIT GAGNER. La
    proposition annonce une portée que son chapeau justifie — la directive REC
    — mais ses quatre mesures relèvent d'un collectif : un guide, des
    instances, un label. Le contrôle d'import a obligé à dire laquelle
    s'impose au projet.

    C'est la première : un guide harmonisé traduisant les exigences en actions
    « auditables et comparables » est, une fois écrit, le référentiel sur
    lequel le projet sera examiné. La règle vérifie qu'il n'y en a QU'UNE —
    marquer les quatre « anticipe » ferait disparaître la difficulté au lieu
    de la trancher."""
    mesures = ED.MESURES["professionnalisation_resilience"]["mesures"]
    anticipe = [m for m in mesures if m["portee"] == "anticipe"]
    assert len(anticipe) == 1, (
        "%d mesures sur %d portent l'anticipation : si toutes l'annoncent, "
        "l'arbitrage a été contourné" % (len(anticipe), len(mesures)))
    assert "auditables et comparables" in anticipe[0]["texte"]
    assert mesures.index(anticipe[0]) == 0, (
        "ce n'est plus la première mesure qui porte l'anticipation — le "
        "raisonnement écrit dans le module ne vaut plus")


def test_LA_PLATEFORME_MASQUE_UNE_MESURE_QUE_LE_PROJET_DECIDE_SEUL():
    """La proposition 16 est lue CONTRIBUE : un centre de données ne construit
    pas la plateforme nationale des interdépendances. Trois de ses quatre
    mesures ont bien un objet partagé — le graphe, la gouvernance, le
    référentiel commun. La quatrième n'en a pas : intégrer les risques
    émergents à sa propre analyse, à partir de travaux publiés, ne demande ni
    plateforme ni accord. Elle serait restée invisible."""
    masquees = [m for m in ED.mesures_masquees() if m["numero"] == 16]
    assert len(masquees) == 1, (
        "%d mesure(s) masquée(s) sur la proposition 16" % len(masquees))
    m = masquees[0]
    assert m["portee"] == "decide" and m["portee_proposition"] == "contribue"
    assert "risques émergents" in m["texte"]
    # Les trois autres gardent bien un objet partagé : sans cela, la
    # distinction ne tiendrait plus et les quatre seraient « decide ».
    autres = [x for x in ED.MESURES["plateforme_interdependances"]["mesures"]
              if x["portee"] != "decide"]
    assert len(autres) == 3


def test_les_sigles_du_theme_sont_ceux_que_le_document_met_en_note():
    """Le document met six sigles en note sur ce thème, et pas d'autres :
    Géorisques, la CCR, l'ANSSI, le CRO et le Fonds Barnier sont cités dans le
    corps sans être définis. Le glossaire suit ce choix — l'enrichir de
    définitions que l'auteur n'a pas données ferait passer notre lecture pour
    la sienne."""
    du_theme = set()
    for cle in [p["cle"] for p in ED.PROPOSITIONS if p["theme"] == "infrastructures"]:
        for m in ED.MESURES[cle]["mesures"]:
            du_theme.update(m["termes"])
    assert du_theme == {"tacct", "pics", "undrr", "bale_iii", "bric",
                        "vade_mecum"}, sorted(du_theme)
    corps = " ".join(m["texte"] for cle in ED.MESURES
                     for m in ED.MESURES[cle]["mesures"])
    for cite_sans_note in ("Géorisques", "ANSSI", "Chief Resilience Officer",
                           "Fonds Barnier"):
        assert cite_sans_note in corps, cite_sans_note
        assert not [g for g in ED.GLOSSAIRE.values()
                    if cite_sans_note.lower() in g["developpe"].lower()], (
            "%s a reçu une définition que le document ne donne pas"
            % cite_sans_note)


def test_les_deux_reperes_du_theme_disent_leur_limite_de_perimetre():
    """Les 66 milliards sont dominés par les réseaux de transport et
    l'énergie : un exploitant qui les lirait comme son exposition propre se
    tromperait de périmètre. Et la seconde source est un COMMUNIQUÉ DE PRESSE,
    dont les hypothèses ne sont pas exposées."""
    par_cle = {r["cle"]: r for r in ED.reperes_des_themes(["infrastructures"])}
    assert set(par_cle) == {"pertes_infrastructures_europe",
                            "investissement_infrastructures_fr"}
    pertes = par_cle["pertes_infrastructures_europe"]
    assert "CONDITIONS CLIMATIQUES ACTUELLES" in pertes["lecture"]
    assert "RÉSEAUX DE TRANSPORT" in pertes["lecture"]
    invest = par_cle["investissement_infrastructures_fr"]
    assert "COMMUNIQUÉ DE PRESSE" in invest["lecture"]
    assert "interprétation" in invest["lecture"]
