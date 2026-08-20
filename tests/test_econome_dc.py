"""L'ÉCONOMISTE — chiffrer des quantités, et refuser d'inventer un ratio.

LA DEMANDE ÉTAIT DE « S'APPUYER SUR DES PROJETS DÉJÀ EXÉCUTÉS ». Le référentiel
a été recompté pour l'occasion : 249 centres de données recensés, AUCUN ne
publiant sa capacité informatique, DEUX publiant un investissement, ZÉRO les
deux. Il n'existe donc aucune base permettant de calibrer un euro par kilowatt.

Ce module en tire la seule conséquence tenable : il ne porte AUCUN prix. Il
chiffre des quantités par des prix fournis, et il tient le compte de ce qui
n'est pas chiffré. Les contrôles ci-dessous gardent ce parti pris, parce que
c'est lui qu'on aura envie d'assouplir « juste pour donner un ordre de
grandeur » — et un ordre de grandeur inventé est crédible, ce qui est pire
qu'une case vide.

  1. AUCUN RATIO N'EST EMBARQUÉ, et rien ne peut en introduire un en silence.
  2. CE QUI CHANGE ENTRE DEUX NATURES EST LA LISTE DES POSTES, pas un
     coefficient. Une réhabilitation porte la dépose, le curage, le site
     occupé ; un neuf ne les porte pas — et un ratio de neuf ne les
     sous-estime pas, il les ignore.
  3. CHAQUE POSTE EST SOIT RETENU, SOIT ÉCARTÉ AVEC SA RAISON. Ni l'un ni
     l'autre, et il disparaît sans laisser de trace.
  4. UN POSTE SANS PRIX VAUT « NON CHIFFRÉ », JAMAIS ZÉRO. Un zéro muet
     laisserait croire que le poste n'est pas dû.
  5. LA MAINTENANCE EST ANNUELLE et le dit : l'additionner à un investissement
     produirait un nombre qui ne veut rien dire.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import econome_dc as E


def test_LE_POINT_QUI_DECIDE_aucun_prix_n_est_embarque():
    """Le parti pris du module, et le seul qu'on aura envie d'assouplir.

    On lit le fichier plutôt que l'API : un ratio pourrait être introduit dans
    une table que `sante()` ne compterait pas."""
    assert E.sante()["ratios_embarques"] == 0
    assert E.sante()["references_livrees"] == 0, (
        "des opérations de référence sont apparues : le contrôle suivant doit "
        "alors vérifier leur forme, pas leur absence")
    # LE CONTRÔLE PORTE SUR LE CODE, PAS SUR LA PROSE. Écrit d'abord comme une
    # recherche de chaînes dans tout le fichier, il tombait sur la docstring du
    # module — qui contient le mot « RATIO » précisément pour expliquer qu'il
    # n'y en a pas. On analyse donc l'arbre syntaxique : toute constante de
    # module est examinée, et aucune ne doit ressembler à une table de prix.
    import ast
    arbre = ast.parse(open(os.path.join(os.path.dirname(E.__file__),
                                        "econome_dc.py"), encoding="utf-8").read())
    constantes = [n.targets[0].id for n in arbre.body
                  if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                  and n.targets[0].id.isupper()]
    # ON NE DEVINE PAS DES NOMS, ON REGARDE LA FORME. Une première version
    # cherchait les mots « PRIX », « COUT », « RATIO » dans les noms de
    # constantes : « OPERATIONS » contient RATIO, et le contrôle tombait sur
    # lui-même. Un contrôle qui échoue sur un nom innocent apprend à être
    # désactivé — c'est pire que pas de contrôle.
    #
    # UN RATIO A UNE FORME RECONNAISSABLE : une table qui associe un nombre à
    # un poste ou à une nature d'opération. C'est cela qu'on interdit, quel que
    # soit le nom qu'on lui donne.
    reperes = set(E.POSTES) | set(E.OPERATIONS) | set(E.QUANTITES)
    for nom in constantes:
        v = getattr(E, nom)
        if not isinstance(v, dict):
            continue
        numeriques = {k for k, x in v.items()
                      if isinstance(x, (int, float)) and not isinstance(x, bool)}
        assert not (numeriques & reperes), (
            "%s associe un nombre à %s : c'est un ratio embarqué, quel que "
            "soit son nom" % (nom, sorted(numeriques & reperes)))

    # …ET LA SEULE CONSTANTE NUMÉRIQUE DU MODULE EST LE SEUIL. Toute autre
    # serait un coefficient qui s'ignore.
    nombres = [n for n in constantes
               if isinstance(getattr(E, n), (int, float))
               and not isinstance(getattr(E, n), bool)]
    assert nombres == ["SEUIL_NON_CHIFFRE"], nombres


def test_chaque_poste_est_RETENU_ou_ECARTE_dans_chaque_nature():
    """Un poste ni retenu ni écarté disparaîtrait sans laisser de trace — la
    faute même que ce module reproche aux ratios. Le contrôle de chargement la
    refuse déjà ; celui-ci le prouve sur les cinq natures."""
    for cle, o in E.OPERATIONS.items():
        couverts = set(o["postes"]) | set(o["sans_objet"])
        assert couverts == set(E.POSTES), (
            "%s ne dit rien de %s" % (cle, sorted(set(E.POSTES) - couverts)))
        assert not (set(o["postes"]) & set(o["sans_objet"])), cle


def test_LE_POINT_QUI_DECIDE_la_rehabilitation_porte_ce_que_le_neuf_ignore():
    """LE FAIT QUI JUSTIFIE TOUT LE MODULE. Ce ne sont pas les mêmes postes.
    Un chiffrage de réhabilitation bâti sur un ratio de neuf ne sous-estime pas
    la dépose et le site occupé : il ne les porte pas."""
    neuf = set(E.OPERATIONS["neuf"]["postes"])
    rehab = set(E.OPERATIONS["rehabilitation_technique"]["postes"])
    propres = rehab - neuf
    assert "depose_curage" in propres
    assert "site_occupe" in propres
    assert "raccordement_existant" in propres
    # …et le neuf porte le clos-couvert, que la réhabilitation ne porte pas.
    assert "clos_couvert" in (neuf - rehab)
    assert "clos_couvert" in E.OPERATIONS["rehabilitation_technique"]["sans_objet"]


def test_un_poste_sans_prix_vaut_NON_CHIFFRE_et_jamais_zero():
    r = E.chiffrer("neuf", {"puissance_it_kw": 1000, "surface_batiment_m2": 2000,
                            "surface_salle_m2": 800},
                   {"froid": 700})
    assert r["ok"]
    par = {L["poste"]: L for L in r["lignes"]}
    assert par["froid"]["etat"] == "chiffree"
    assert par["froid"]["montant"] == 700000.0, par["froid"]["montant"]
    ouvert = par["distribution_secours"]
    assert ouvert["etat"] == "non_chiffree"
    assert ouvert["montant"] is None, "un zéro laisserait croire que rien n'est dû"
    assert "prix unitaire manquant" in ouvert["dit"]


def test_la_part_non_chiffree_est_PUBLIEE_et_change_la_lecture():
    """C'est elle la vraie information, pas le total : au-delà d'un quart, un
    total cesse d'être une estimation."""
    maigre = E.chiffrer("neuf", {"puissance_it_kw": 1000}, {"froid": 700})
    assert maigre["part_non_chiffree"] > E.SEUIL_NON_CHIFFRE
    assert "n'est plus une estimation" in maigre["lecture"]

    complet = E.chiffrer(
        "neuf",
        {"puissance_it_kw": 1000, "surface_batiment_m2": 2000, "surface_salle_m2": 800},
        {p: 100 for p in E.OPERATIONS["neuf"]["postes"]})
    assert complet["postes_non_chiffres"] == 0
    assert complet["part_non_chiffree"] == 0.0
    assert "Tous les postes" in complet["lecture"]


def test_SANS_CE_CONTRASTE_le_controle_precedent_ne_prouverait_rien():
    """Les deux cas doivent bien tomber de part et d'autre du seuil, sinon ils
    testeraient deux fois la même situation."""
    assert 0 < E.SEUIL_NON_CHIFFRE < 1
    maigre = E.chiffrer("neuf", {"puissance_it_kw": 1000}, {"froid": 700})
    assert maigre["postes_non_chiffres"] > 0
    assert maigre["postes_non_chiffres"] < maigre["postes_total"], (
        "tout est non chiffré : le cas ne distingue plus rien")


def test_la_maintenance_est_ANNUELLE_et_le_dit():
    r = E.chiffrer("maintenance", {"puissance_it_kw": 1000},
                   {"maintenance_preventive": 40, "gros_entretien": 20})
    assert r["annuel"] is True
    assert r["total_chiffre"] == 60000.0
    # …et aucune autre nature ne se déclare annuelle.
    for cle in E.ORDRE_OPERATIONS:
        if cle == "maintenance":
            continue
        assert E.chiffrer(cle, {}, {})["annuel"] is False, cle


def test_LE_POINT_QUI_DECIDE_le_module_refuse_le_coefficient_et_tient_un_ORDRE():
    """Il ne dit pas de combien la provision d'une réhabilitation dépasse celle
    d'un neuf — personne ne peut le dire sans base d'opérations livrées. Il dit
    qu'elle ne peut pas être inférieure, ce qui suffit à empêcher la faute
    courante : reprendre la provision d'un neuf sur de l'existant."""
    a = E.ordre_des_aleas()
    rangs = {x["operation"]: x["rang"] for x in a["ordre"]}
    assert rangs["neuf"] < rangs["extension"] < rangs["rehabilitation_technique"] \
        < rangs["reprise_travaux"]
    assert "Aucune valeur de provision n'est proposée" in a["refus"]
    # La provision n'existe QUE si on la saisit.
    sans = E.chiffrer("rehabilitation_technique", {"puissance_it_kw": 100}, {"froid": 10})
    assert sans["provision"] is None
    avec = E.chiffrer("rehabilitation_technique", {"puissance_it_kw": 100},
                      {"froid": 10}, provision_pct=15)
    assert avec["provision"]["saisi"] is True
    assert avec["provision"]["montant"] == 150.0, avec["provision"]


def test_une_quantite_ou_un_poste_inconnu_est_REFUSE_et_non_ignore():
    """Ignorer une clé inconnue ferait disparaître une saisie sans le dire :
    le client croirait avoir chiffré un poste qui n'est pas au tableau."""
    r = E.chiffrer("neuf", {"surface_de_jardin_m2": 400}, {})
    assert r["ok"] is False and r["erreur"] == "quantite_inconnue"
    r = E.chiffrer("neuf", {}, {"piscine": 1000})
    assert r["ok"] is False and r["erreur"] == "poste_inconnu"
    r = E.chiffrer("demolition_totale", {}, {})
    assert r["ok"] is False and r["erreur"] == "operation_inconnue"


def test_chaque_poste_declare_une_assiette_qui_EXISTE():
    """Un poste pointant vers une quantité inconnue ressortirait « non
    chiffré » pour toujours, sans qu'aucune ligne ne dise pourquoi."""
    for cle, P in E.POSTES.items():
        assert P["assiette"] in E.QUANTITES, (cle, P["assiette"])
        assert P["famille"] in E.FAMILLES, cle
        assert E.QUANTITES[P["assiette"]]["ou"], (
            "%s s'appuie sur une quantité dont on ne dit pas où la trouver" % cle)


def test_le_referentiel_servi_porte_tout_ce_dont_la_page_a_besoin():
    r = E.referentiel()
    assert len(r["operations"]) == len(E.OPERATIONS)
    for o in r["operations"]:
        assert o["quantites_utiles"], o["cle"]
        assert o["postes"], o["cle"]
        # La page affiche la raison de chaque poste écarté : sans elle, un
        # poste absent passerait pour un oubli.
        for x in o["sans_objet"]:
            assert x["pourquoi"], (o["cle"], x["poste"])
    assert r["seuil_non_chiffre"] == E.SEUIL_NON_CHIFFRE
    assert "249" in r["avertissement"], (
        "l'avertissement ne dit plus sur quoi repose le refus d'embarquer un ratio")


# ═══════════════════════════════════════════════════════════════════════════
#  D'OÙ VIENT LE PRIX, ET CE QUE LE MODULE PEUT PROPOSER
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_le_module_ne_propose_AUCUN_prix_sans_operation_livree():
    """LE PARTI PRIS, ET CELUI QU'ON AURA ENVIE D'ASSOUPLIR « pour orienter le
    client ». Il existe des ordres de grandeur publiés, au mégawatt et pour
    l'opération ENTIÈRE. En tirer un prix par lot demanderait une clé de
    répartition qu'aucune source ne donne : deux hypothèses enchaînées, un
    nombre crédible, personne pour dire d'où il sort."""
    s = E.suggestions()
    assert s["references_disponibles"] == 0
    assert s["postes"] == {}, s["postes"]
    assert "ne propose donc aucun prix" in s["dit"]


def test_le_mecanisme_de_suggestion_FONCTIONNE_des_qu_une_operation_est_versee():
    """Sans ce contrôle, le précédent passerait pour une bonne raison — le
    module ne proposant jamais rien — au lieu de la vraie : il n'a pas encore
    de base. On vérifie que le mécanisme existe et rend ce qu'il doit."""
    E.REFERENCES.append({
        "reference": "CONTROLE", "operation": "neuf", "annee_reception": 2024,
        "quantites": {"puissance_it_kw": 1000},
        "prix_unitaires": {"froid": 880, "distribution_secours": 1350},
        "source": "marché notifié"})
    E.REFERENCES.append({
        "reference": "CONTROLE-2", "operation": "neuf", "annee_reception": 2025,
        "quantites": {"puissance_it_kw": 2000},
        "prix_unitaires": {"froid": 940},
        "source": "décompte général définitif"})
    # UNE TROISIÈME OBSERVATION, ET ELLE EST ABERRANTE — C'EST VOULU.
    # Avec seulement 880 et 940, moyenne et médiane valent toutes deux 910 : le
    # contrôle passait AUSSI quand on remplaçait la médiane par la moyenne,
    # donc il ne gardait rien. Une opération hors norme, qui est précisément le
    # cas où la distinction compte, les sépare : médiane 940, moyenne 1 273.
    E.REFERENCES.append({
        "reference": "CONTROLE-3", "operation": "neuf", "annee_reception": 2025,
        "quantites": {"puissance_it_kw": 300},
        "prix_unitaires": {"froid": 2000},
        "source": "petite opération très contrainte"})
    try:
        s = E.suggestions("neuf")
        assert s["references_disponibles"] == 3
        f = s["postes"]["froid"]
        assert f["n"] == 3 and f["min"] == 880.0 and f["max"] == 2000.0
        # MÉDIANE ET NON MOYENNE : une moyenne se laisse emporter par
        # l'exception, qui est justement ce qu'on veut voir.
        assert f["mediane"] == 940.0, f["mediane"]
        moyenne = round(sum(x["valeur"] for x in f["observations"]) / 3, 2)
        assert abs(f["mediane"] - moyenne) > 100, (
            "médiane et moyenne se confondent sur ce jeu : le contrôle ne "
            "distingue plus les deux")
        assert "OBSERVATIONS, pas un barème" in s["dit"]
        # …et le filtre par nature d'opération tient.
        assert E.suggestions("maintenance")["postes"] == {}
    finally:
        del E.REFERENCES[-3:]
    assert E.REFERENCES == [], "les références de contrôle n'ont pas été retirées"


def test_un_prix_porte_sa_PROVENANCE_ou_son_absence_est_dite():
    """Un prix dont on ne sait plus d'où il vient ne se défend pas devant un
    écart — et c'est là que la question se pose."""
    avec = E.chiffrer("neuf", {"puissance_it_kw": 1000}, {"froid": 700},
                      provenances={"froid": "devis"})
    L = [x for x in avec["lignes"] if x["poste"] == "froid"][0]
    assert L["provenance"] == "devis"
    assert L["provenance_nom"] == "Devis d'entreprise"
    assert L["provenance_reserve"], "une provenance sans réserve se lit comme une garantie"
    assert avec["prix_sans_provenance"] == 0

    sans = E.chiffrer("neuf", {"puissance_it_kw": 1000}, {"froid": 700})
    M = [x for x in sans["lignes"] if x["poste"] == "froid"][0]
    assert M["provenance"] is None
    assert "indéfendable" in M["provenance_manquante"]
    assert sans["prix_sans_provenance"] == 1


def test_les_provenances_sont_ORDONNEES_du_plus_opposable_au_moins():
    """C'est le seul jugement que ce module porte sur un prix : un marché
    notifié engage quelqu'un, une estimation interne n'engage personne."""
    rangs = {c: E.PROVENANCES[c]["rang"] for c in E.PROVENANCES}
    assert rangs["marche_notifie"] < rangs["devis"] < rangs["estimation"]
    assert sorted(rangs.values()) == list(range(1, len(E.PROVENANCES) + 1))
    for c, v in E.PROVENANCES.items():
        assert v["vaut"] and v["reserve"], c


def test_une_provenance_inventee_est_REFUSEE():
    r = E.chiffrer("neuf", {"puissance_it_kw": 1}, {"froid": 1},
                   provenances={"froid": "au_pif"})
    assert r["ok"] is False and r["erreur"] == "provenance_inconnue"


def test_AUCUNE_QUANTITE_N_EST_ORPHELINE():
    """LE DÉFAUT MESURÉ SUR MA PROPRE PREMIÈRE VERSION. Trois quantités étaient
    déclarées que nul poste ne consommait — surface des locaux techniques,
    nombre de baies, durée de contrat. Le formulaire ne les aurait jamais
    demandées : elles occupaient le référentiel sans que rien ne les lise."""
    consommees = {P["assiette"] for P in E.POSTES.values()}
    orphelines = sorted(set(E.QUANTITES) - consommees)
    assert orphelines == [], orphelines
    assert E.sante()["quantites_orphelines"] == []


# ═══════════════════════════════════════════════════════════════════════════
#  LE PONT VERS LA MAÎTRISE D'ŒUVRE
# ═══════════════════════════════════════════════════════════════════════════

def _complet(op="rehabilitation_technique", prix=200):
    q = {"puissance_it_kw": 1200, "surface_salle_m2": 900,
         "surface_batiment_m2": 2400, "surface_a_deposer_m2": 1500,
         "montant_marche_repris_eur": 500000}
    return E.chiffrer(op, q, {p: prix for p in E.OPERATIONS[op]["postes"]})


def test_LE_POINT_QUI_DECIDE_la_part_technique_est_CALCULEE_et_non_supposee():
    """LE FAIT QUI JUSTIFIE CE PONT. Sans lui, le barème d'honoraires retombe
    sur une hypothèse à 70 % dont son propre texte dit qu'elle « pèse plus
    lourd que n'importe quel taux du barème » — les taux y étant inversés
    entre clos-couvert et lot technique. Ici, le rapport est une conséquence
    du chiffrage."""
    r = E.avec_maitrise_oeuvre(_complet())
    assert r["ok"], r
    pt = r["part_technique"]
    assert pt["nature"] == "calculee"
    assert 0.0 < pt["valeur"] < 1.0
    # Sur une réhabilitation de lots techniques, le bâtiment n'est pas repris :
    # la part technique doit être NETTEMENT au-dessus de l'hypothèse de 70 %.
    assert pt["valeur"] > 0.70, pt["valeur"]
    assert "70" in pt["dit"], "le texte ne dit pas ce qu'on a évité"


def test_l_assiette_des_honoraires_EXCLUT_l_exploitation_et_inclut_l_existant():
    """L'exploitation est annuelle : elle n'est pas une assiette d'honoraires.
    L'existant, lui, est bien du travail — mais il ne tranche pas le rapport
    clos-couvert / technique, et le module le dit."""
    c = _complet()
    r = E.avec_maitrise_oeuvre(c)
    d = r["travaux"]["detail"]
    attendu = d["batiment_eur"] + d["technique_eur"] + d["existant_eur"]
    assert abs(r["travaux"]["assiette_eur"] - attendu) < 0.01
    assert "pas dans le rapport" in r["part_technique"]["exclus"]


def test_une_MAINTENANCE_ne_porte_aucun_honoraire_au_pourcentage():
    """Un coût annuel d'exploitation n'est pas une opération de travaux :
    y asseoir des honoraires au pourcentage serait un contresens."""
    c = E.chiffrer("maintenance", {"puissance_it_kw": 1000},
                   {"maintenance_preventive": 40, "gros_entretien": 20})
    r = E.avec_maitrise_oeuvre(c)
    assert r["ok"] is False and r["erreur"] == "operation_annuelle"


def test_sans_travaux_chiffres_le_pont_REFUSE():
    vide = E.chiffrer("neuf", {}, {})
    r = E.avec_maitrise_oeuvre(vide)
    assert r["ok"] is False and r["erreur"] == "assiette_vide"
    assert E.avec_maitrise_oeuvre(None)["erreur"] == "chiffrage_absent"


def test_LE_POINT_QUI_DECIDE_les_deux_incompletudes_restent_SEPAREES():
    """Des postes de travaux sans prix et des missions sans taux ne portent pas
    sur la même chose. Les fondre en un « taux de complétude » unique donnerait
    un nombre que ni l'un ni l'autre ne défend — et c'est celui-là qu'on
    citerait."""
    partiel = E.chiffrer("neuf",
                         {"puissance_it_kw": 1000, "surface_batiment_m2": 2000,
                          "surface_salle_m2": 800},
                         {"froid": 700, "clos_couvert": 900})
    r = E.avec_maitrise_oeuvre(partiel)
    k = r["kpi"]
    assert k["travaux_non_chiffres"]["postes"] > 0
    assert k["moe_sans_taux"]["missions"] == 3
    # Les deux mesures sont distinctes et aucune ne les résume.
    assert k["travaux_non_chiffres"]["part_pct"] != k["moe_sans_taux"]["part_pct"]
    assert "Aucun indicateur unique" in k["refus"]
    for interdit in ("completude", "complétude_globale", "score"):
        assert interdit not in k, interdit


def test_les_indicateurs_se_RECALCULENT_a_la_main():
    """Un indicateur qu'on ne peut pas recompter n'est pas un indicateur."""
    r = E.avec_maitrise_oeuvre(_complet())
    k, a = r["kpi"], r["travaux"]["assiette_eur"]
    moe = r["maitrise_oeuvre"]["total_eur"]
    assert abs(k["part_moe_sur_travaux_pct"] - round(moe / a * 100, 2)) < 0.01
    assert abs(k["cout_operation_eur"] - (a + moe)) < 0.01
    assert abs(k["part_moe_dans_operation_pct"]
               - round(moe / (a + moe) * 100, 2)) < 0.01


def test_les_trois_missions_sans_taux_REMONTENT_jusqu_au_pont():
    """Elles ne doivent pas disparaître en route : le lecteur du chiffrage
    d'opération doit voir qu'elles attendent un taux."""
    r = E.avec_maitrise_oeuvre(_complet())
    ouvertes = [m["cle"] for m in r["maitrise_oeuvre"]["missions_ouvertes"]]
    assert set(ouvertes) == {"bet_economiste", "bet_incendie", "coord_ssi"}, ouvertes
    assert "attendent leur taux" in r["kpi"]["lecture"]


# ═══════════════════════════════════════════════════════════════════════════
#  LES MISSIONS SELON LA NATURE DE L'OPÉRATION
# ═══════════════════════════════════════════════════════════════════════════

def test_chaque_mission_est_RETENUE_ou_ECARTEE_dans_chaque_nature():
    """La même discipline que pour les postes. Une mission ni retenue ni
    écartée disparaîtrait d'une nature d'opération sans laisser de trace."""
    for cle, o in E.MISSIONS_PAR_OPERATION.items():
        couvertes = set(o["retenues"]) | set(o["sans_objet"])
        assert couvertes == set(E._TOUTES_MISSIONS), (cle, couvertes)
        assert not (set(o["retenues"]) & set(o["sans_objet"])), cle
        for m, r in o["sans_objet"].items():
            assert len(r) >= 30, (cle, m, r)


def test_LE_POINT_QUI_DECIDE_la_selection_CHANGE_avec_la_nature():
    """Sans cela, « selon les projets choisis » ne voudrait rien dire : la même
    liste de seize missions s'appliquerait partout, et une réhabilitation
    paierait des VRD sur un bâtiment qu'elle ne touche pas."""
    neuf = E.missions_pour("neuf")
    rehab = E.missions_pour("rehabilitation_technique")
    assert neuf["ok"] and rehab["ok"]
    cles_neuf = {m["cle"] for m in neuf["retenues"]}
    cles_rehab = {m["cle"] for m in rehab["retenues"]}
    assert cles_neuf != cles_rehab, "la sélection ne dépend pas de la nature"
    assert cles_rehab < cles_neuf
    ecartee = {m["cle"] for m in rehab["sans_objet"]}
    assert ecartee == {"bet_vrd"}, ecartee
    # …et l'écart se répercute jusqu'au chiffrage, pas seulement à l'affichage.
    r = E.avec_maitrise_oeuvre(_complet("rehabilitation_technique"))
    portees = {m["cle"] for m in r["missions_ecartees"]}
    assert "bet_vrd" in portees
    assert r["kpi"]["moe_sans_taux"]["sur"] == len(cles_rehab), (
        "le pont a chiffré une liste de missions qui n'est pas celle que la "
        "nature d'opération propose")


def test_une_mission_INCERTAINE_est_retenue_ET_signalee_pas_tranchee():
    """L'état le plus utile est le troisième. Un tableau ordinaire n'a que
    « oui » et « non » : il tranche à la place du maître d'ouvrage sur des
    questions — catégorie de SSI, classement ICPE — que le chiffrage ne
    qualifie pas."""
    rehab = E.missions_pour("rehabilitation_technique")
    par = {m["cle"]: m for m in rehab["retenues"]}
    # L'architecte est retenu, et le module AVOUE que son montant va ressortir
    # très bas parce que son assiette principale est nulle ici.
    assert par["architecte"]["a_qualifier"], "l'anomalie d'assiette est tue"
    assert "TRÈS BAS" in par["architecte"]["a_qualifier"]
    # Le SSI est retenu par prudence, sans que sa catégorie soit qualifiée.
    assert "61-931" in par["coord_ssi"]["a_qualifier"]
    for cle in ("bet_environnement", "controle_technique"):
        assert par[cle]["a_qualifier"], cle
    # Un signalement ne porte jamais sur une ligne absente.
    for o in E.MISSIONS_PAR_OPERATION.values():
        assert not (set(o["a_qualifier"]) - set(o["retenues"]))


def test_les_missions_OBLIGATOIRES_ne_s_ecartent_d_aucune_operation_de_travaux():
    """Les retirer afficherait une économie qui n'aura pas lieu : la dépense
    sera engagée de toute façon."""
    import moe_dc
    for cle, o in E.MISSIONS_PAR_OPERATION.items():
        if E.OPERATIONS[cle].get("annuel"):
            continue
        for c in moe_dc.OBLIGATOIRES:
            assert c in o["retenues"], (cle, c)
    par = {m["cle"]: m for m in E.missions_pour("neuf")["retenues"]}
    assert par["sps"]["obligatoire"] is True
    assert par["controle_technique"]["obligatoire"] is True
    assert par["opc"]["obligatoire"] is False


def test_la_MAINTENANCE_n_appelle_aucune_mission_mais_ne_nie_pas_l_obligation():
    """« Aucune » est une réponse, et elle se motive. Ce que le module refuse
    est de facturer au pourcentage d'un montant annuel — pas de rappeler qu'un
    coordonnateur SPS reste dû quand plusieurs entreprises interviennent."""
    m = E.missions_pour("maintenance")
    assert m["ok"] and m["retenues"] == []
    assert len(m["sans_objet"]) == len(E._TOUTES_MISSIONS)
    assert "SPS" in m["dit"], "le texte laisse croire que l'obligation tombe"
    assert "annuel" in m["dit"].lower() or "annuel" in m["sans_objet"][0]["raison"].lower()


def test_une_selection_EXPLICITE_prime_sur_la_proposition():
    """La proposition oriente ; elle n'enferme pas. Si le maître d'ouvrage sait
    que son aéroréfrigérant sort du bâtiment, il rétablit les VRD."""
    c = _complet("rehabilitation_technique")
    propose = E.avec_maitrise_oeuvre(c)
    force = E.avec_maitrise_oeuvre(c, missions=["architecte", "bet_fluides"])
    assert force["ok"]
    assert force["maitrise_oeuvre"]["total_eur"] != propose["maitrise_oeuvre"]["total_eur"]
    # Les obligatoires restent comptées : moe_dc les recompte même décochées.
    assert force["kpi"]["moe_sans_taux"]["sur"] == 4, force["kpi"]["moe_sans_taux"]


def test_les_montants_des_PHRASES_sont_ecrits_en_francais():
    """Le calcul était juste et la page avait l'air fausse : « 612000.0 € » au
    milieu d'un tableau qui affiche « 612 000 € » partout ailleurs. Le lecteur
    ne doute pas du chiffre, il doute du reste de la page.

    Les valeurs BRUTES restent publiées à côté : c'est le texte qu'on habille,
    jamais le calcul."""
    # L'ESPACE DES MILLIERS EST INSÉCABLE (U+202F), comme celle que produit
    # toLocaleString('fr-FR') dans le reste de la page. Une espace ordinaire
    # laisserait « 612 » finir une ligne et « 000 » commencer la suivante.
    assert E._nb(612000) == "612 000"
    assert " " not in E._nb(612000), "espace ordinaire : le nombre peut se couper"
    assert E._nb(84.08, 2) == "84,08"
    assert E._nb(1200.0, 3) == "1 200"     # pas de décimale inutile
    assert E._nb(0.5, 2) == "0,5"

    c = _complet("rehabilitation_technique", prix=100)
    r = E.avec_maitrise_oeuvre(c)
    phrases = [c["lignes"][0]["dit"], r["part_technique"]["dit"],
               r["part_technique"]["exclus"], r["kpi"]["lecture"]]
    for t in phrases:
        assert ".0 " not in t and ".0€" not in t and ".0 €" not in t, t
        # un séparateur décimal anglais dans une phrase française
        import re
        assert not re.search(r"\d\.\d", t), t

    # …et les valeurs brutes, elles, restent des nombres exploitables.
    assert isinstance(r["travaux"]["detail"]["existant_eur"], float)
    assert isinstance(r["kpi"]["part_moe_sur_travaux_pct"], float)


def test_une_nature_inconnue_est_REFUSEE_et_non_traitee_comme_du_neuf():
    r = E.missions_pour("renovation_energetique")
    assert r["ok"] is False and r["erreur"] == "operation_inconnue"
    assert r["connues"] == E.ORDRE_OPERATIONS
