"""La consigne de la frise ne doit avoir qu'UNE source.

CE QU'ON PROTÈGE, ET POURQUOI CE TEST N'A PAS BESOIN D'UN NAVIGATEUR.

Le bloc du dossier affichait « Choisissez une phase dans la frise ci-dessus »
depuis TROIS endroits différents : le HTML servi avant tout script, le
gestionnaire de clic sur un onglet de filière, et la fonction de
rafraîchissement. Aucun des trois ne regardait si la frise contenait quoi que
ce soit — et elle ne contient rien tant que la puissance informatique n'est pas
saisie, seul champ du formulaire à n'avoir aucune valeur par défaut.

Le défaut n'était donc pas une erreur de logique, mais une DUPLICATION : trois
copies d'une même phrase, dont aucune ne pouvait savoir ce que les deux autres
affichaient. Le corriger à un endroit l'aurait laissé aux deux autres.

Ce test n'ouvre pas de navigateur. Il vérifie l'invariant à la source :

  1. La phrase d'invitation n'est écrite qu'à UN seul endroit du script, dans
     la fonction qui consulte l'état de la frise.
  2. Le HTML servi avant le script ne l'affirme plus — c'est ce que voit le
     visiteur pendant le chargement, et c'est faux à ce moment-là par
     construction.
  3. Le champ qui commande la frise n'a toujours PAS de valeur par défaut : en
     inventer une ferait sortir un dossier d'ingénierie complet et chiffré pour
     un projet qui n'est pas celui du lecteur.
"""
import os
import re
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

JS = os.path.join(ICI, "ingenierie-dc.js")
HTML = os.path.join(ICI, "ingenierie-datacenter.html")

INVITATION = "Choisissez une phase dans la frise"


def _lire(chemin):
    with open(chemin, encoding="utf-8") as f:
        return f.read()


def test_invitation_ecrite_une_seule_fois():
    """Trois copies d'une phrase, c'est trois occasions de la voir mentir."""
    src = _lire(JS)
    assert src.count(INVITATION) == 1, (
        "la phrase est écrite %d fois dans le script : chaque copie peut "
        "s'afficher sans savoir ce que montre la frise"
        % src.count(INVITATION))


def test_invitation_conditionnee_a_l_etat_de_la_frise():
    """Elle doit vivre dans la fonction qui CONSULTE l'état, pas ailleurs."""
    src = _lire(JS)
    i = src.index(INVITATION)
    debut = src.rfind("function ", 0, i)
    porteuse = src[debut:i]
    assert "messageAttente" in porteuse, (
        "la phrase n'est pas dans messageAttente() mais dans : "
        + porteuse.split("(")[0])
    assert "friseVide" in porteuse, (
        "la fonction qui porte la phrase ne consulte pas l'état de la frise")


def test_le_html_ne_l_affirme_plus_avant_le_script():
    """Ce que voit le visiteur pendant le chargement doit être vrai aussi."""
    html = _lire(HTML)
    bloc = re.search(r'<div id="ig-dossier">(.*?)</div>', html, re.S)
    assert bloc, "le bloc du dossier n'a pas été trouvé"
    assert INVITATION not in bloc.group(1), (
        "le HTML invite à choisir une phase alors que la frise n'est jamais "
        "dessinée à ce stade")
    assert "puissance informatique" in bloc.group(1), (
        "la consigne d'ouverture ne désigne pas le premier geste réel")


def test_les_deux_zones_ont_un_bouton_vers_le_champ():
    """Un défilement à trouver soi-même parmi treize champs n'est pas un guide."""
    src = _lire(JS)
    assert src.count("data-vers-champ") >= 3, (
        "il faut le bouton dans les deux messages, et son écouteur")
    assert "ig-designe" in src, "le champ visé n'est pas désigné à l'arrivée"
    assert "ig-designe" in _lire(HTML), "la désignation n'a pas de style"


def test_la_puissance_n_a_toujours_pas_de_valeur_par_defaut():
    """Le contrôle qui interdit la fausse bonne idée.

    Poser 5 000 kW par défaut ferait disparaître le symptôme — et produirait
    une note de calcul complète pour un projet imaginaire, sans que le lecteur
    puisse le savoir. Le champ DOIT rester vide.
    """
    import datacenter as dc

    champs = {c["id"]: c for c in dc.CHAMPS}
    p = champs["puissance_it_kw"]
    assert p.get("defaut") in (None, ""), (
        "une puissance par défaut a été posée (%r) : la frise s'afficherait "
        "sur un projet qui n'est celui de personne" % p.get("defaut"))
    assert p.get("requis") is True, "le champ doit rester déclaré nécessaire"
    # …et il doit bien être le SEUL dans ce cas, sinon la consigne ment.
    sans_defaut = [c["id"] for c in champs.values()
                   if c.get("defaut") in (None, "") and c["id"] != "puissance_it_kw"
                   and c.get("requis")]
    assert not sans_defaut, (
        "d'autres champs sont nécessaires sans valeur par défaut (%s) : la "
        "consigne qui annonce « le seul champ nécessaire » devient fausse"
        % ", ".join(sans_defaut))
