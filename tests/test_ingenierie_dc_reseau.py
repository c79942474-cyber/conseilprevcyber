"""ingenierie-dc.js porte DEUX modules — et un seul avait le filet réseau.

LE DÉFAUT CORRIGÉ. Le fichier contient deux IIFE indépendantes : le calcul
principal (phases, dossier, rédaction), puis — bien plus loin — le chiffrage
des honoraires de maîtrise d'œuvre. demander(), qui borne chaque requête dans
le temps et traite le 401 en un seul endroit, vivait DANS la première : la
seconde n'y avait pas accès et repartait en fetch nu sur ses trois requêtes
(chiffrage, export du tableau de répartition, chargement du barème). Un
serveur lent laissait alors « chiffrage en cours… » à l'écran sans limite, et
le catch vide qui terminait le chargement du barème faisait disparaître
l'échec en silence.

CE QUE CES CONTRÔLES VÉRIFIENT : demander()/messageDelai() sont maintenant
déclarés une seule fois, à la portée du FICHIER entier plutôt que d'une seule
IIFE — et les trois sites d'appel du module honoraires les utilisent tous.
"""
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)


def _js():
    with open(os.path.join(ICI, "ingenierie-dc.js"), encoding="utf-8") as f:
        return f.read()


def test_demander_est_declare_une_seule_fois_hors_des_deux_iife():
    js = _js()
    assert js.count("function demander(url, options, delai)") == 1
    assert js.count("function messageDelai(") == 1
    i_demander = js.index("function demander(")
    i_iife1 = js.index("(function () {")
    assert i_demander < i_iife1, (
        "demander() doit être déclaré AVANT la première IIFE pour être visible "
        "des deux — c'est tout le correctif")


def test_le_module_honoraires_n_appelle_plus_fetch_directement():
    js = _js()
    i_iife2 = js.index("(function () {", js.index("})();") + 1)
    bloc = js[i_iife2:]
    assert bloc.count("fetch(") == 0, (
        "le module honoraires MOE contourne encore demander() quelque part")
    # …et il s'en sert bien, à ses trois sites d'appel connus (le compte réel
    # de la sous-chaîne peut dépasser 3 : elle apparaît aussi en prose dans
    # les commentaires qui expliquent le correctif).
    assert bloc.count("demander(") >= 3


def test_le_chiffrage_et_l_export_utilisent_le_budget_moyen():
    js = _js()
    assert 'demander("/api/datacenter/moe", {' in js
    i = js.index('demander("/api/datacenter/moe", {')
    assert "DELAI_MOYEN" in js[i:i + 400]
    assert 'demander("/api/datacenter/moe/repartition?format=xlsx"' in js
    i = js.index('demander("/api/datacenter/moe/repartition?format=xlsx"')
    assert "DELAI_MOYEN" in js[i:i + 300]


def test_le_chargement_du_bareme_utilise_le_budget_court_et_a_un_vrai_catch():
    js = _js()
    assert 'demander("/api/datacenter/moe", {}, DELAI_COURT)' in js
    # AVANT LE CORRECTIF, ce catch était vide (`.catch(function () {});`) :
    # un délai dépassé ou une panne réseau laissaient le formulaire muet.
    assert ".catch(function () {});" not in js
    i = js.index('demander("/api/datacenter/moe", {}, DELAI_COURT)')
    fin = js.index("})();", i)
    bloc = js[i:fin]
    assert "messageDelai(e," in bloc, (
        "le chargement du barème doit distinguer le délai dépassé du reste "
        "plutôt que d'échouer en silence")


def test_le_401_n_est_plus_recopie_a_la_main_dans_le_module_honoraires():
    """Le traitement manuel du 401 (auth-dit) doit avoir disparu du module
    honoraires : demander() le fait maintenant une fois pour toutes."""
    js = _js()
    i_iife2 = js.index("(function () {", js.index("})();") + 1)
    bloc = js[i_iife2:]
    assert "auth-dit" not in bloc
    assert 'e.name === "SessionEteinte"' in bloc
