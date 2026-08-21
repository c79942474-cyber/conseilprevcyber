"""Trois docstrings promettaient une page ouverte que le code refusait déjà.

LE DÉFAUT CORRIGÉ. datacenter_page(), strategie_durable_datacenter_page() et
api_datacenter_etat_art() portaient chacune un `@login_required` — et
chacune ouvrait sa docstring par « page OUVERTE » ou « OUVERT. », avec toute
une justification pour un état que le décorateur juste au-dessus dément. Un
lecteur qui fait confiance à la docstring plutôt qu'au décorateur — ce
qu'une docstring est précisément là pour permettre — en conclut la mauvaise
politique d'accès. Le même relâchement avait laissé un intitulé de section
« La route est ouverte » juste au-dessus d'un test qui, LUI, vérifie
qu'elle exige un compte (tests/test_etat_art.py).

Ces contrôles ne vérifient pas seulement que le mot « OUVERT » a disparu :
ils vérifient qu'il a disparu LÀ OÙ LE DÉCORATEUR EST TOUJOURS LÀ — sans
quoi corriger le texte en retirant la protection réelle passerait le
contrôle tout aussi bien, pour la mauvaise raison.
"""
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import app as A  # noqa: E402

ROUTES_CONCERNEES = [
    "datacenter_page",
    "strategie_durable_datacenter_page",
    "api_datacenter_etat_art",
]


def test_les_trois_routes_restent_gardees_par_login_required():
    """Le préalable : si l'une d'elles n'était plus gardée, le contrôle
    suivant ne prouverait plus rien."""
    for endpoint in ROUTES_CONCERNEES:
        vue = A.app.view_functions.get(endpoint)
        assert vue is not None, endpoint
        assert getattr(vue, "auth_gated", False) is True, (
            "%s n'est plus gardée par login_required — ce test ne peut "
            "plus garantir que sa docstring ne contredit pas le décorateur"
            % endpoint)


def test_leurs_docstrings_ne_promettent_plus_une_page_ouverte():
    for endpoint in ROUTES_CONCERNEES:
        vue = A.app.view_functions.get(endpoint)
        doc = (vue.__doc__ or "")
        assert "OUVERT" not in doc, (
            "%s : la docstring contredit encore le login_required juste "
            "au-dessus" % endpoint)


def test_le_commentaire_de_section_du_test_etat_art_suit_le_test_juste_apres():
    chemin = os.path.join(ICI, "tests", "test_etat_art.py")
    with open(chemin, encoding="utf-8") as f:
        source = f.read()
    i = source.index("La route demande un compte")
    fin = source.index("def test_", i)
    bloc = source[i:fin]
    assert "route est ouverte" not in bloc.lower(), (
        "l'intitulé de section contredit encore le test "
        "test_la_route_demande_un_compte qui le suit")
