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
