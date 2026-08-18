"""LA BASE CARBONE ADEME DANS CE DÉPÔT-CI — lue, et elle ne remplace rien.

POURQUOI ELLE EST AUSSI ICI. L'autre site du cabinet la porte déjà. La verser
une seconde fois duplique huit méga-octets, et c'est assumé : les deux sites
sont déployés séparément, et une référence réglementaire qui ne serait
disponible que d'un côté produirait exactement l'asymétrie que ce contrôle
cherche à détecter.

CE QUE LA CONFRONTATION MESURE ICI. INTENSITE_RESEAU (millésime 2023-2024,
approche location-based) contre la Base Carbone v22.0 (validité 2017-2019) :
écart MÉDIAN de 37,7 % sur 28 pays. Aucune des deux n'est fausse ; elles ne
décrivent pas la même année.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import base_carbone as BC
import datacenter as DC


def test_la_base_est_bien_versee_a_ce_depot():
    assert BC.disponible(), "le fichier ADEME n'est pas dans donnees/ademe/"
    s = BC.sante()
    assert s["lignes"] > 10000, "%d lignes lues" % s["lignes"]
    assert s["pays_electricite"] >= 25


def test_les_facteurs_sont_LUS_et_non_recopies():
    """Aucun facteur d'électricité n'est écrit dans ce module : ils viennent
    tous du fichier. Un facteur recopié cesserait d'être vrai à la première
    version de la base, sans que rien ne le signale."""
    src = open(os.path.join(os.path.dirname(BC.__file__), "base_carbone.py"),
               encoding="utf-8").read()
    code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    for interdit in ('"FR": 79', "'FR': 79", '"DE": 461', "'DE': 461"):
        assert interdit not in code, "facteur recopié : %s" % interdit


def test_l_ecart_avec_INTENSITE_RESEAU_est_reel_et_date():
    """Sans écart, tout ce dispositif n'aurait rien à dire."""
    c = BC.confronter(DC.INTENSITE_RESEAU)
    assert c["pays_compares"] >= 25
    assert c["ecart_median_pct"] > 20, "médiane %s %%" % c["ecart_median_pct"]
    # L'UNION AGRÉGÉE N'EST PAS UN PAYS de la Base Carbone : elle doit être
    # déclarée absente, jamais estimée.
    assert "UE" in c["pays_absents"]


def test_LA_LECTURE_S_ADAPTE_a_ce_qu_elle_a_mesure():
    """LE DÉFAUT MESURÉ, ET IL VENAIT DE L'AUTRE DÉPÔT.

    La phrase de lecture avait été écrite sur la seule table qui contient
    l'Islande, dont le facteur ADEME vaut 0,2 gCO2e/kWh et fait exploser la
    moyenne des écarts relatifs. Elle affirmait donc la déformation MÊME QUAND
    IL N'Y AVAIT RIEN POUR DÉFORMER : sur INTENSITE_RESEAU, qui ne descend pas
    sous 30 gCO2e/kWh, elle produisait « la moyenne est tirée par AUCUN PAYS,
    dont le facteur ADEME est proche de zéro ». Un défaut latent ne se révèle
    qu'au deuxième cas d'emploi."""
    c = BC.confronter(DC.INTENSITE_RESEAU)
    assert c["references_quasi_nulles"] == [], (
        "cette table ne contient aucun facteur ADEME quasi nul : %s"
        % c["references_quasi_nulles"])
    assert "aucun pays" not in c["lecture"], c["lecture"]
    assert "Aucun facteur ADEME n'est ici proche de zéro" in c["lecture"]
    # …et la branche inverse fonctionne toujours, sur une table qui EN CONTIENT.
    d = BC.confronter(dict(DC.INTENSITE_RESEAU, IS=30))
    assert d["references_quasi_nulles"] == ["IS"]
    assert "tirée par IS" in d["lecture"]


def test_LE_POINT_QUI_DECIDE_la_reserve_nomme_LE_PAYS_ETUDIE():
    """Une réserve générale se lit et s'oublie. Celle-ci porte l'écart du pays
    qu'on instruit, calculé sur le fichier — pas une moyenne sur vingt-neuf."""
    r = DC._reserve_ademe("FR")
    assert r and "FR" in r
    assert "79.1" in r or "79,1" in r, r
    assert "56" in r
    assert "L229-25" in r, "la réserve ne dit pas à quoi sert le facteur ADEME"


def test_la_reserve_SE_TAIT_quand_il_n_y_a_rien_a_dire():
    """Deux silences voulus : le pays absent de la base, et l'écart trop petit
    pour peser. Une réserve qui paraît sans raison use celle qui en a une."""
    # L'Union agrégée ne figure pas dans la Base Carbone.
    assert DC._reserve_ademe("UE") is None
    # Un pays hors table.
    assert DC._reserve_ademe("XX") is None
    # La Lettonie : 110 contre 120, soit 8 % — sous le seuil.
    assert DC._reserve_ademe("LV") is None


def test_la_reserve_DIT_LE_BON_SENS_et_ne_depasse_pas_cent_pour_cent_a_la_baisse():
    """Le sens annoncé est celui des deux nombres cités, et un manque plafonne
    à 100 % — une valeur « inférieure de 300 % » n'existe pas."""
    for pays, valeur in sorted(DC.INTENSITE_RESEAU.items()):
        r = DC._reserve_ademe(pays)
        if not r:
            continue
        ref = BC.facteur(pays)["g_kwh"]
        if valeur > ref:
            assert "supérieure" in r, "%s : %s > %s mais « inférieure »" % (
                pays, valeur, ref)
        else:
            assert "inférieure" in r, "%s : %s < %s mais « supérieure »" % (
                pays, valeur, ref)
            import re
            m = re.search(r"inférieure de (\d+) %", r)
            assert m and int(m.group(1)) <= 100, (
                "%s : « inférieure de %s %% » est impossible" % (pays, m and m.group(1)))


def test_l_avertissement_du_moteur_PORTE_la_reserve_du_pays():
    """Le calcul ne garde pas sa réserve pour lui : elle part avec le résultat."""
    res = DC.etude({"pays": "FR", "puissance_it_kw": 500})
    av = " ".join(res["avertissements"])
    assert "RÉFÉRENCE RÉGLEMENTAIRE" in av
    assert "L229-25" in av
    # …et l'écart entre les deux sites du cabinet y est toujours, corrigé.
    assert "MÉDIANE de 9 %" in av
    assert "s'inverse pour huit pays" in av.replace("S'INVERSE", "s'inverse")


def test_l_avertissement_DISPARAIT_quand_le_client_fournit_son_facteur():
    """Un client qui apporte le facteur contractuel de son fournisseur n'a que
    faire d'une réserve sur une moyenne nationale qu'il n'emploie pas."""
    res = DC.etude({"pays": "FR", "puissance_it_kw": 500,
                    "intensite_reseau_g": 22})
    av = " ".join(res["avertissements"])
    assert "RÉFÉRENCE RÉGLEMENTAIRE" not in av
    assert "ÉCART CONNU ENTRE LES DEUX RÉFÉRENTIELS" not in av


# ═══════════════════════════════════════════════════════════════════════════
#  LA ROUTE — et la garde que le contrôle de démarrage a exigée
# ═══════════════════════════════════════════════════════════════════════════

def test_la_route_est_FERMEE_au_visiteur_sans_compte(anonyme):
    """POSÉE OUVERTE, ELLE A FAIT REFUSER LE DÉMARRAGE AU SERVEUR.

    Le contrôle de politique d'accès de ce dépôt relève la protection réelle
    sur les décorateurs et refuse de démarrer si une interface non déclarée
    reste ouverte : « /api/base-carbone est ouverte : fermer la page sans
    fermer son interface ne protège rien ». La base de l'ADEME est publique,
    mais ce que la route publie EN PLUS ne l'est pas — la table du cabinet et
    l'écart qui l'en sépare."""
    r = anonyme.get("/api/base-carbone")
    assert r.status_code == 401, r.status_code


def test_la_route_sert_la_confrontation_au_client(connecte):
    r = connecte.get("/api/base-carbone?table=reseau")
    assert r.status_code == 200, r.status_code
    d = r.get_json()
    assert d["ok"] is True
    assert len(d["electricite"]) >= 25
    c = d["confrontation"]
    assert c["pays_compares"] >= 25
    assert c["ecart_median_pct"] > 20
    # LA SOURCE PART AVEC LA DONNÉE : un facteur sans son éditeur ni son
    # millésime ne se défend pas, et c'est ce que cette page reproche ailleurs.
    assert "ADEME" in d["source"]["editeur"]
    assert d["source"]["url"].startswith("https://")


def test_sans_table_demandee_la_route_ne_confronte_rien(connecte):
    """On ne fait pas payer à chaque appel une comparaison que personne n'a
    demandée."""
    d = connecte.get("/api/base-carbone").get_json()
    assert d["ok"] is True
    assert "confrontation" not in d


# ═══════════════════════════════════════════════════════════════════════════
#  L'AUTRE FACTEUR D'ÉMISSION : LE CARBONE INCORPORÉ
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_l_encadrement_repond_a_l_incertitude_declaree():
    """DEUX CHIFFRES QUI DIFFÈRENT D'UN FACTEUR DEUX NE SE CONTREDISENT PAS si
    la référence annonce ±80 %. La question n'est pas « sont-ils égaux » mais
    « la valeur tient-elle dans l'intervalle publié ». Mesuré : 1 200 sort de
    [120 ; 1 080] par le haut, de 11 % — ce qui ne tranche rien et doit être
    écrit ainsi plutôt qu'en verdict."""
    ref = BC.poste("Serveurs informatiques")[0]
    assert ref["incertitude_pct"] == 80.0, ref
    e = BC.encadre(DC.INCORPORE["serveur_kgCO2e"]["valeur"], ref)
    assert e["encadre"] is False
    assert e["haut"] == 1080.0
    assert 0 < e["depassement_pct"] < 20, e
    # Une valeur au milieu de l'intervalle est, elle, encadrée.
    assert BC.encadre(600, ref)["encadre"] is True


def test_sans_incertitude_declaree_on_N_EN_INVENTE_PAS():
    e = BC.encadre(1000, {"valeur": 600, "incertitude_pct": None})
    assert e["encadre"] is None
    assert "ne déclare pas d'incertitude" in e["dit"]


def test_la_reserve_incorpore_DIT_CE_QUI_N_A_PAS_PU_ETRE_CONFRONTE():
    """Le bâti est exprimé au kW informatique ici, au m² à l'ADEME, et aucun
    modèle de surface ne fait le pont. Inventer un ratio pour produire une
    comparaison serait pire que de n'en produire aucune."""
    r = DC._reserve_incorpore()
    assert r
    assert "1080" in r.replace(".0", "") or "1080.0" in r
    assert "SORT par le haut" in r
    assert "mètre carré" in r
    assert "aucun modèle de surface" in r


def test_l_etude_PORTE_la_confrontation_du_carbone_incorpore():
    """Elle vaut pour toute étude : le carbone incorporé ne dépend ni du pays
    ni du facteur réseau que le client apporterait."""
    for profil in ({"pays": "FR", "puissance_it_kw": 500},
                   {"pays": "SE", "puissance_it_kw": 500,
                    "intensite_reseau_g": 12}):
        av = " ".join(DC.etude(profil)["avertissements"])
        assert "CARBONE INCORPORÉ, CONFRONTÉ À LA RÉFÉRENCE" in av, profil
