"""L'organisation de la phase travaux — l'ordre, les tiers, et ce qui bloque.

CE QUI EST ÉPROUVÉ. Les propriétés qui font qu'un plan de travaux tient :

  · une opération de commissioning non commandée NE DISPARAÎT PAS du plan ;
  · les trois natures de lien avec la maîtrise d'ouvrage sont distinguées —
    on ne pilote pas de la même façon quelqu'un qui doit un résultat et
    quelqu'un dont l'avis est réglementé ;
  · les préalables d'un rétrofit et d'un fit-out sont BLOQUANTS, et non des
    bonnes pratiques ;
  · chaque solution dit ce qu'elle coûte et où la poser — une solution posée
    après la consultation se négocie au lieu de s'appliquer.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import travaux_dc as T  # noqa: E402


# ── Ce qui ne disparaît pas ────────────────────────────────────────────────

def test_le_commissioning_non_commande_reste_au_plan_avec_son_orphelinat():
    """LE DÉFAUT QUE CETTE RÈGLE EMPÊCHE. Retirer les essais du plan parce que
    personne n'est payé pour les faire est exactement ce qui produit une
    réception sans essai intégré : le plan devient cohérent, et l'installation
    n'est jamais éprouvée. Les opérations restent, avec la mention de qui
    devra les assumer."""
    p = T.plan(None, avec_commissioning=False)
    cx = [o for o in p["operations"] if o["famille"] == "commissioning"]
    assert cx, "les opérations de commissioning ont disparu du plan"
    for o in cx:
        assert o.get("sans_titulaire"), o["cle"]
        assert "risque" in o["sans_titulaire"].lower()


def test_le_commissioning_commande_ne_porte_aucune_mention_d_orphelinat():
    p = T.plan(None, avec_commissioning=True)
    for o in p["operations"]:
        assert not o.get("sans_titulaire"), o["cle"]


def test_le_plan_porte_les_douze_operations_quel_que_soit_le_reglage():
    """Ni la nature des travaux ni l'absence de commissioning ne retirent une
    opération : elles changent ce qu'il faut y mettre, pas ce qui est dû."""
    n = len(T.OPERATIONS)
    for nature in (None, "neuf", "fit_out", "retrofit"):
        for cx in (True, False):
            assert len(T.plan(nature, cx)["operations"]) == n, (nature, cx)


# ── Les préalables imposés par la nature des travaux ───────────────────────

def test_un_retrofit_impose_le_phasage_d_exploitation_avant_tout():
    """C'est cette étude, et non les plans, qui décide de la faisabilité. La
    ranger parmi les bonnes pratiques laisserait croire qu'on peut l'arbitrer."""
    p = T.plan("retrofit")
    cles = [x["cle"] for x in p["prealables"]]
    assert "phasage" in cles, cles
    assert all(x["bloquant"] for x in p["prealables"])


def test_un_fit_out_impose_le_releve_de_l_existant():
    """Les plans d'origine ne correspondent plus. Le relevé est la seule
    donnée fiable, et la provision qui l'accompagne est du chiffrage."""
    assert "releve" in [x["cle"] for x in T.plan("fit_out")["prealables"]]


def test_une_construction_neuve_n_a_pas_de_prealable_de_ce_genre():
    """Un préalable affiché sans raison apprend au lecteur à ne plus les
    regarder."""
    assert T.plan("neuf")["prealables"] == []
    assert T.plan(None)["prealables"] == []


def test_les_solutions_imposees_par_le_projet_passent_en_tete():
    """Le phasage d'un rétrofit n'est pas une bonne pratique : c'est une
    condition de faisabilité. L'afficher au même rang que les autres
    laisserait croire qu'on peut l'arbitrer."""
    sols = T.plan("retrofit")["solutions"]
    imposees = [i for i, s in enumerate(sols) if s["impose"]]
    autres = [i for i, s in enumerate(sols) if not s["impose"]]
    assert imposees and autres
    assert max(imposees) < min(autres), [s["cle"] for s in sols]


# ── Les intervenants et la nature de leur lien ─────────────────────────────

def test_les_quatre_natures_de_lien_sont_toutes_peuplees():
    """On ne pilote pas de la même façon quelqu'un sous contrat, un tiers
    réglementé et un concessionnaire. Les fondre en « intervenants » fait
    donner des instructions à qui n'en reçoit pas."""
    for lien in T.LIENS:
        assert any(v["lien"] == lien for v in T.INTERVENANTS.values()), lien


def test_le_controleur_technique_et_le_csps_ne_recoivent_pas_d_instruction():
    """Leur avis engage leur propre responsabilité. On les informe tôt ; on ne
    les dirige pas — et l'ignorer coûte au rapport final."""
    for cle in ("controle_technique", "csps"):
        assert T.INTERVENANTS[cle]["lien"] == "tiers_reglemente", cle
    aide = T.LIENS["tiers_reglemente"]["aide"].lower()
    assert "instruction" in aide


def test_le_commissioning_agent_est_commande_mais_tiers_au_marche_de_travaux():
    """Son efficacité vient de ce que le marché de travaux lui donne — points
    d'arrêt, essais opposables — et de rien d'autre."""
    i = T.INTERVENANTS["commissioning"]
    assert i["lien"] == "tiers_commande"
    assert "contractualis" in i["interface"].lower()


def test_les_delais_hors_contrat_se_planifient_en_premier():
    """Aucun ne se négocie et aucun ne dépend du chantier : le raccordement
    électrique est le premier délai du projet et le dernier qu'on regarde."""
    i = T.INTERVENANTS["concessionnaires"]
    assert i["lien"] == "hors_contrat"
    assert "raccordement" in i["interface"].lower()


def test_la_maitrise_d_oeuvre_figure_en_tant_que_groupement():
    """LE DÉFAUT TROUVÉ AU PREMIER CONTRÔLE DE CHARGEMENT. Sept opérations
    citaient « la maîtrise d'œuvre » comme acteur alors que seuls l'architecte
    et les bureaux d'études étaient déclarés. Or c'est le groupement, sous son
    mandataire, qui dirige l'exécution et propose la réception : désigner un
    de ses membres aurait nommé un responsable qui n'en est pas un."""
    m = T.INTERVENANTS["moe"]
    assert "mandataire" in m["nom"].lower() or "groupement" in m["nom"].lower()
    assert "mandataire" in m["interface"].lower()


def test_chaque_acteur_d_une_operation_est_rendu_avec_son_lien():
    """La page colore l'acteur selon son lien. Sans lui, elle afficherait des
    noms au même rang — et le lecteur croirait pouvoir tous les diriger."""
    for o in T.plan()["operations"]:
        assert o["acteurs"], o["cle"]
        for a in o["acteurs"]:
            assert a["lien"] in T.LIENS, a
            assert a["lien_nom"], a


# ── L'ordre, et ce qui bloque ──────────────────────────────────────────────

def test_chaque_operation_dit_ce_qu_il_faut_avant_elle():
    """C'est le préalable, pas la durée, qui rend l'ordre non négociable : le
    franchir produit un travail à refaire, pas un gain de temps."""
    for o in T.OPERATIONS:
        assert len(o["prealable"]) > 15, o["cle"]


def test_les_essais_integres_exigent_les_essais_par_systeme():
    """Un écart en essai intégré sur des systèmes non clos devient
    inattribuable, et chaque entreprise désigne l'autre."""
    ist = [o for o in T.OPERATIONS if o["cle"] == "ist"][0]
    assert "système" in ist["prealable"].lower()
    sat = [o for o in T.OPERATIONS if o["cle"] == "sat"][0]
    assert "intégré" in (sat["point_arret"] or "").lower()


def test_la_reception_exige_le_dossier_des_ouvrages_executes():
    """Prononcer la réception sans lui fait accepter un ouvrage dont on n'a pas
    la description — et c'est l'exploitant qui en héritera."""
    opr = [o for o in T.OPERATIONS if o["cle"] == "opr"][0]
    assert "ouvrages exécutés" in opr["prealable"]


def test_les_points_d_arret_sont_rendus_a_part():
    """C'est le seul outil qui donne prise sur un chantier — et il n'existe
    que s'il est écrit au marché. Les noyer dans la liste des opérations les
    rendrait invisibles au moment de rédiger le CCAP."""
    pa = T.plan()["points_arret"]
    assert len(pa) >= 5
    for x in pa:
        assert x["operation"] and x["exigence"]


def test_le_point_d_arret_des_ouvrages_caches_existe():
    """Un ouvrage fermé ne se contrôle plus, il se rouvre."""
    ct = [o for o in T.OPERATIONS if o["cle"] == "controle_travaux"][0]
    assert "caché" in ct["point_arret"].lower()


# ── Les solutions ──────────────────────────────────────────────────────────

def test_chaque_solution_dit_ce_qu_elle_coute_et_ou_la_poser():
    """Une solution dont le prix n'est pas dit ne se décide pas ; une solution
    posée au mauvais moment ne s'applique pas — elle se négocie."""
    for s in T.SOLUTIONS:
        assert len(s["obtient"]) > 40, s["cle"]
        assert len(s["coute"]) > 30, s["cle"]
        assert len(s["quand_poser"]) > 20, s["cle"]


def test_les_deux_natures_de_solution_sont_representees():
    """La demande portait sur des solutions techniques ET managériales. N'en
    servir qu'une famille répondrait à moitié."""
    for nature in T.NATURES_SOLUTION:
        assert any(s["nature"] == nature for s in T.SOLUTIONS), nature


def test_le_point_d_arret_se_pose_avant_la_consultation():
    """Posé en cours de chantier, il se négocie ; posé au CCAP, il s'applique."""
    s = [x for x in T.SOLUTIONS if x["cle"] == "points_arret"][0]
    assert "avant la consultation" in s["quand_poser"].lower()


def test_le_delai_de_levee_d_un_point_d_arret_est_encadre():
    """Un point d'arrêt sans délai de levée transforme un contrôle en risque
    de retard, et l'entreprise a raison de s'en plaindre."""
    s = [x for x in T.SOLUTIONS if x["cle"] == "points_arret"][0]
    assert "délai" in s["coute"].lower()


# ── Le plan n'est pas un planning, et le dit ───────────────────────────────

def test_le_plan_annonce_qu_il_ne_porte_aucune_duree():
    """Une structure prise pour un planning se retrouve au marché, et la
    première durée inventée y devient contractuelle."""
    note = T.plan()["note"]
    assert "structure" in note.lower()
    assert "durée" in note.lower()


def test_le_plan_dit_avec_quoi_il_se_raccorde():
    """Trois documents se contredisent habituellement sur les mêmes points ;
    ne pas les nommer laisse croire que ce plan les remplace."""
    note = T.plan()["note"].lower()
    for mot in ("planning d'entreprise", "contrôleur technique",
                "commissioning"):
        assert mot in note, mot


# ── Le contrôle de chargement se vérifie lui-même ──────────────────────────

def test_le_controle_attrape_un_acteur_inconnu(monkeypatch):
    """C'est ce contrôle qui a trouvé la faute réelle du premier jet. Une
    ligne sans nom dans le plan se lit comme une ligne sans responsable."""
    faux = [dict(o) for o in T.OPERATIONS]
    faux[0] = dict(faux[0], acteurs=["quelqu_un_qui_n_existe_pas"])
    monkeypatch.setattr(T, "OPERATIONS", faux)
    fautes = T._verifier()
    assert any("quelqu_un_qui_n_existe_pas" in f for f in fautes), fautes


def test_le_controle_attrape_une_famille_sans_operation(monkeypatch):
    """Une famille annoncée et vide ferait afficher un filtre qui ne rend
    rien."""
    faux = dict(T.FAMILLES_OPERATION)
    faux["fantome"] = {"nom": "Famille fantôme", "aide": "x"}
    monkeypatch.setattr(T, "FAMILLES_OPERATION", faux)
    fautes = T._verifier()
    assert any("fantome" in f for f in fautes), fautes


def test_le_controle_attrape_une_phase_inconnue_du_cadre(monkeypatch):
    """Une opération rattachée à une phase qui n'existe pas ne se retrouverait
    nulle part dans le dossier."""
    faux = [dict(o) for o in T.OPERATIONS]
    faux[0] = dict(faux[0], phase="PHASE-QUI-N-EXISTE-PAS")
    monkeypatch.setattr(T, "OPERATIONS", faux)
    fautes = T._verifier()
    assert any("PHASE-QUI-N-EXISTE-PAS" in f for f in fautes), fautes


# ── Le glossaire ───────────────────────────────────────────────────────────

def test_le_glossaire_couvre_les_trois_tables():
    g = T.glossaire()
    assert set(g) == {"intervenant", "operation", "solution"}
    assert set(g["intervenant"]) == set(T.INTERVENANTS)
    assert set(g["operation"]) == {o["cle"] for o in T.OPERATIONS}
    assert set(g["solution"]) == {s["cle"] for s in T.SOLUTIONS}


@pytest.mark.parametrize("famille", ["intervenant", "operation", "solution"])
def test_aucune_infobulle_n_est_vide(famille):
    for cle, e in T.glossaire()[famille].items():
        assert len(e["aide"]) > 80, (famille, cle, len(e["aide"]))
