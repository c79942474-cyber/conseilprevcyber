"""datacenter.js — le 401 a maintenant le même traitement central que sur
la page d'ingénierie.

LE DÉFAUT CORRIGÉ. demander() bornait chaque requête dans le temps mais ne
reconnaissait pas le 401 : chaque appelant se débrouillait seul, ou pas du
tout. chargerReferentiel() recopiait à la main un test `r.status === 401`
suivi d'un sentinel de message (« auth ») — exactement le motif qu'ingenierie-
dc.js portait AVANT son propre correctif — pendant qu'apercuProfil() et
exporter() n'en avaient aucun : un aperçu ou un export qui expirait par 401
affichait un message générique (« Aperçu indisponible », « Réseau
indisponible ») sans jamais dire qu'il fallait se reconnecter. Et
messageErreur() promettait « Connectez-vous pour utiliser le moteur
d'ingénierie » — le nom de l'AUTRE page, copié-collé sans être adapté.

Le correctif reprend exactement le motif d'ingenierie-dc.js : demander()
reconnaît le 401 en un seul endroit, affiche une bannière de reconnexion, et
rejette la promesse avec un nom distinctif (SessionEteinte) — que les
appelants n'ont plus besoin de dupliquer.
"""
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)


def _js():
    with open(os.path.join(ICI, "datacenter.js"), encoding="utf-8") as f:
        return f.read()


def _html():
    with open(os.path.join(ICI, "datacenter.html"), encoding="utf-8") as f:
        return f.read()


def test_demander_reconnait_desormais_le_401():
    js = _js()
    assert js.count("function demander(url, options, delai)") == 1
    i = js.index("function demander(url, options, delai)")
    # LA BORNE ÉTAIT LE FORMATEUR VOISIN, ET ELLE A CASSÉ le jour où celui-ci a
    # pris un second paramètre. Une règle qui se repère sur le code d'à côté
    # tombe pour une raison sans rapport avec ce qu'elle éprouve. On compte les
    # accolades de la fonction qu'on veut lire.
    j = js.index("{", i)
    p, k = 1, j + 1
    while p:
        if js[k] == "{":
            p += 1
        elif js[k] == "}":
            p -= 1
        k += 1
    bloc = js[i:k]
    assert "r.status === 401" in bloc
    assert "sessionEteinte()" in bloc
    assert '"SessionEteinte"' in bloc


def test_sessionEteinte_pose_une_banniere_de_reconnexion():
    js = _js()
    assert "function sessionEteinte()" in js
    assert "function sessionTexte()" in js
    i = js.index("function sessionTexte()")
    fin = js.index("function sessionEteinte()", i)
    texte = js[i:fin]
    assert "/connexion?next=/datacenter" in texte, (
        "le lien de reconnexion doit ramener sur CETTE page, pas une autre")
    assert "Se reconnecter" in texte


def test_chargerreferentiel_ne_recopie_plus_le_401_a_la_main():
    js = _js()
    i = js.index("function chargerReferentiel()")
    fin = js.index("function démarrer()", i)
    bloc = js[i:fin]
    assert 'r.status === 401' not in bloc, (
        "chargerReferentiel() ne doit plus tester le 401 lui-même — "
        "demander() rejette déjà la promesse avant que ce .then() ne s'exécute")
    assert 'e.name === "SessionEteinte"' in bloc
    assert "moteur d'ingénierie" not in bloc, (
        "texte copié-collé de la page d'ingénierie, jamais adapté à cette page")


def test_messageerreur_ne_promet_plus_le_mauvais_moteur():
    js = _js()
    i = js.index("function messageErreur(res)")
    fin = js.index("function lancer()", i)
    bloc = js[i:fin]
    assert "moteur d'ingénierie" not in bloc
    # LE 401 n'y arrive plus jamais : demander() a déjà rejeté la promesse
    # avant que poster() ne produise un `res` — le laisser ici serait du code
    # mort qui suggérerait, à tort, que ce chemin est encore emprunté.
    assert "401" not in bloc


def test_la_page_porte_le_style_de_la_banniere_de_session():
    html = _html()
    assert ".dc-session-alerte" in html
