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
