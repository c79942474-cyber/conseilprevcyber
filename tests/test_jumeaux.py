# -*- coding: utf-8 -*-
"""LES MODULES PARTAGÉS — ce qu'une règle peut garder, et ce qu'elle ne peut pas.

ELLE NE PEUT PAS LIRE L'AUTRE DÉPÔT. Les deux sont des copies de travail
distinctes, et l'intégration n'en voit qu'une. Une règle qui prétendrait
garantir l'identité depuis ici serait verte pour une raison sans rapport avec
ce qu'elle prétend.

ELLE PEUT RENDRE LA DÉRIVE VISIBLE, ET C'EST ASSEZ. Modifier une copie sans la
re-tamponner fait tomber ces règles dans le dépôt modifié, tout de suite. Le
tampon part ensuite au jumeau avec le reste du travail, et les deux manifestes
se comparent d'un coup d'œil — ou par `outils/verifier_jumeaux.py`, qui est le
seul endroit à voir les deux.

CE QUE CES RÈGLES ONT ÉTÉ ÉCRITES POUR EMPÊCHER DE SE REPRODUIRE :
`equipements_it.py` se déclarait « PARTAGÉ À L'IDENTIQUE » depuis son en-tête,
et divergeait de trente-six lignes — dont trois chaînes de source, l'une des
copies revendiquant une traçabilité que l'autre avait déjà reconnu ne pas
avoir.
"""
import io
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import jumeaux as J                                                 # noqa: E402

SRC = io.open(os.path.join(ICI, "jumeaux.py"), encoding="utf-8").read()


def test_AUCUN_jumeau_n_a_ete_modifie_sans_etre_re_tamponne():
    """LA RÈGLE QUI TIENT TOUT LE MÉCANISME. Elle tombe à la seconde où l'un
    des modules partagés change sans que son empreinte suive — c'est-à-dire au
    moment exact où les deux dépôts commencent à diverger."""
    r = J.verifier()
    assert r["absents"] == [], "des modules partagés manquent : %s" % r["absents"]
    assert r["derive"] == [], (
        "des modules partagés ont changé sans être re-tamponnés :\n  %s"
        % "\n  ".join("%s : déclarée %s, réelle %s"
                      % (d["module"], d["declaree"], d["reelle"]) for d in r["derive"]))


def test_le_manifeste_SE_TIENT_LUI_MEME_dans_la_liste():
    """Un manifeste qui ne se surveille pas peut voir sa liste diverger sans
    que rien ne le remarque : il serait le seul point aveugle du dispositif."""
    assert "jumeaux.py" in J.JUMEAUX
    assert J.empreinte_du_fichier("jumeaux.py") == J.JUMEAUX["jumeaux.py"]["empreinte"]


def test_une_empreinte_ne_se_reference_pas_elle_meme():
    """Calculée sur sa propre déclaration, elle ne pourrait jamais tomber
    juste : la mise à blanc est ce qui rend le tampon possible."""
    # LA MESURE EST « PLUS AUCUNE EMPREINTE NE SUBSISTE », pas un compte
    # d'occurrences : la première version comptait cinq « empreinte vide » pour
    # quatre jumeaux, la cinquième étant le littéral de remplacement de la
    # fonction elle-même. Elle tombait sur son propre outil.
    blanchi = J._sans_empreintes(SRC)
    assert not re.search(r'"empreinte": "[0-9a-f]{4,}"', blanchi), (
        "une empreinte a survécu à la mise à blanc : le tampon se référencerait "
        "lui-même et ne pourrait jamais tomber juste")
    for d in J.JUMEAUX.values():
        assert d["empreinte"] and d["empreinte"] not in blanchi


@pytest.mark.parametrize("nom", sorted(J.JUMEAUX))
def test_chaque_jumeau_DIT_ce_qu_il_porte(nom):
    """« Partagé » ne dit pas pourquoi. Sans le porté, personne ne sait si une
    divergence est une dérive ou une adaptation légitime."""
    porte = J.JUMEAUX[nom]["porte"]
    assert len(porte) >= 60, "%s : porté de %d caractères" % (nom, len(porte))
    assert len(J.JUMEAUX[nom]["empreinte"]) == 16


def test_une_divergence_ASSUMEE_porte_une_vraie_raison():
    """LE PIÈGE QUE CETTE RÈGLE FERME : une liste d'exemptions qui grossit avec
    des raisons d'une ligne. Une dispense sans motif substantiel n'est pas une
    décision, c'est un contournement."""
    assert J.DIVERGENTS_ASSUMES, "aucune divergence assumée déclarée ?"
    for nom, raison in J.DIVERGENTS_ASSUMES.items():
        assert len(raison) >= 200, (
            "%s : la raison ne fait que %d caractères" % (nom, len(raison)))
        assert nom not in J.JUMEAUX, (
            "%s est à la fois jumeau et divergence assumée" % nom)


def test_les_deux_listes_ne_se_recouvrent_PAS():
    assert not (set(J.JUMEAUX) & set(J.DIVERGENTS_ASSUMES))


def test_l_outil_qui_voit_les_deux_depots_LIT_le_manifeste():
    """LE DOUBLON QUE CETTE RÈGLE FERME, ET QUI SERAIT LE PLUS DRÔLE. L'outil
    portait sa propre liste de modules partagés : une seconde liste, à côté de
    celle-ci, qui aurait divergé — et l'outil chargé de trouver les
    divergences aurait été le premier à ne pas se voir lui-même."""
    outil = io.open(os.path.join(ICI, "outils", "verifier_jumeaux.py"),
                    encoding="utf-8").read()
    assert "import jumeaux" in outil
    # ON MESURE LE CODE, PAS LE RÉCIT. La première version cherchait les noms
    # de modules n'importe où dans le fichier et tombait sur la documentation,
    # qui RACONTE la divergence d'equipements_it — un récit n'est pas une
    # seconde liste, et l'interdire aurait forcé à taire ce qu'on a trouvé.
    code = re.sub(r'"""(?:.|\n)*?"""', " ", outil, count=1)
    assert not re.search(r'^JUMEAUX\s*=\s*[\(\[\{]\s*["\']', code, re.M), (
        "l'outil redéclare sa propre liste de jumeaux")
    for nom in J.JUMEAUX:
        assert ('"%s"' % nom) not in code and ("'%s'" % nom) not in code, (
            "%s est écrit en dur dans le code de l'outil" % nom)


def test_le_manifeste_DIT_la_limite_du_mecanisme():
    """Le dispositif n'est utile que si sa limite est écrite : sans cela, on
    croirait l'identité garantie par les essais."""
    lu = re.sub(r"\s+", " ", SRC.replace("#", " ")).lower()
    assert "ne peut pas lire l'autre dépôt" in lu
    assert "verifier_jumeaux" in lu
