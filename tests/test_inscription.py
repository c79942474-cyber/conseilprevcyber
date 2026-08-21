"""inscription.html — le captcha se charge, et sait dire quand il échoue.

LE DÉFAUT CORRIGÉ. loadCaptcha() n'avait ni .catch() ni délai. Une coupure
réseau, une passerelle en erreur ou une réponse non-JSON laissaient la
promesse en rejet non traité : le visiteur lisait « Vérification : … » sans
jamais savoir quelle question lui était posée, ne pouvait pas répondre, et
le navigateur bloquait l'envoi sur le champ obligatoire sans qu'aucun
message n'explique pourquoi. Un second chemin, plus silencieux encore : une
réponse {} sans clé "question" affichait littéralement « undefined ».
"""
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)


def _page():
    with open(os.path.join(ICI, "inscription.html"), encoding="utf-8") as f:
        return f.read()


def test_loadcaptcha_porte_desormais_un_traitement_dechec():
    page = _page()
    i = page.index("function loadCaptcha()")
    fin = page.index("loadCaptcha();", i)
    bloc = page[i:fin]
    assert ".catch(" in bloc, (
        "un échec réseau sur le captcha doit être dit, pas laissé en rejet "
        "non traité")


def test_une_reponse_sans_question_ne_produit_pas_undefined():
    page = _page()
    i = page.index("function loadCaptcha()")
    fin = page.index("loadCaptcha();", i)
    bloc = page[i:fin]
    assert "j.question" in bloc and ("j&&j.question" in bloc or "j && j.question" in bloc), (
        "la présence de la question doit être vérifiée avant affichage, "
        "sinon une réponse {} affiche littéralement \"undefined\"")
