"""equipements-it.js — les listes déroulantes ne contournent plus le délai.

LE DÉFAUT CORRIGÉ. Le fichier définissait poster(), avec AbortController et
délai, pour ses écritures. Mais les deux GET qui CONDITIONNENT L'AFFICHAGE —
remplirListes() (densités, périmètres) et remplirPays() (intensité réseau
par pays) — appelaient fetch() nu. Sur un serveur lent, #eq-densite et
#eq-perimetre restaient des listes VIDES, #eq-go restait cliquable, et les
deux traitements d'échec déjà écrits ne pouvaient jamais se déclencher :
une requête suspendue ne rejette pas. poster() est repris en un demander()
générique, et les deux GET le portent désormais.
"""
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)


def _js():
    with open(os.path.join(ICI, "equipements-it.js"), encoding="utf-8") as f:
        return f.read()


def test_demander_generalise_poster_a_toutes_les_methodes():
    js = _js()
    assert js.count("function demander(url, options, delai)") == 1
    assert "function poster(url, corps)" in js
    i = js.index("function poster(url, corps)")
    fin = js.index("}", js.index("{", i))
    assert "demander(" in js[i:fin + 1], (
        "poster() doit désormais s'appuyer sur demander(), pas dupliquer sa "
        "propre mécanique de délai")


def test_remplirlistes_et_remplirpays_ne_font_plus_de_fetch_nu():
    js = _js()
    i = js.index("function remplirListes()")
    fin = js.index("function ", js.index("}", i))
    bloc_listes = js[i:fin]
    assert "fetch(" not in bloc_listes
    assert "demander(" in bloc_listes

    j = js.index("function remplirPays()")
    fin2 = js.index("function ", js.index("}", j) + 200)
    bloc_pays = js[j:fin2]
    assert "fetch(" not in bloc_pays
    assert "demander(" in bloc_pays


def test_les_deux_get_portent_un_budget_court_distinct_du_dimensionnement():
    js = _js()
    assert "DELAI_COURT" in js
    assert 'demander("/api/datacenter/equipements/referentiel"' in js
    i = js.index('demander("/api/datacenter/equipements/referentiel"')
    assert "DELAI_COURT" in js[i:i + 200]
    assert 'demander("/api/datacenter/referentiel"' in js
    j = js.index('demander("/api/datacenter/referentiel"')
    assert "DELAI_COURT" in js[j:j + 200]


def test_remplirlistes_rejette_toujours_sur_un_referentiel_en_echec():
    """Le contrat observable par demarrer() ne doit pas changer : un échec
    doit toujours REJETER la promesse, pour que le .catch() existant écrive
    le message "Référentiel des équipements indisponible"."""
    js = _js()
    i = js.index("function remplirListes()")
    fin = js.index("function remplirPays()")
    bloc = js[i:fin]
    assert 'throw new Error("referentiel")' in bloc
    assert "!res.ok" in bloc or "!res.j" in bloc
