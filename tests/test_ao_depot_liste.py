# -*- coding: utf-8 -*-
"""La liste déroulante des pièces choisies, au point de dépôt — et son retrait.

CE QUE CECI AJOUTE, ET LE DÉFAUT QU'IL CORRIGE. Le dépôt ne montrait qu'un
`<input type=file>` brut et un aperçu d'une ligne : on ne pouvait ni voir la
liste des pièces cumulées, ni en ôter UNE avant l'analyse. Le FileList natif
l'interdit — il n'est ni modifiable ni cumulable, et re-choisir REMPLACE tout.
On tient donc une file `AO_EN_ATTENTE`, rendue en liste déroulante, à laquelle
chaque dépôt s'ajoute et dont on retire pièce par pièce.

CES RÈGLES MESURENT L'EFFET, PAS LA PRÉSENCE D'UN WIDGET. Le point qui fait
qu'un retrait n'est pas cosmétique : `aoAnalyser` lit LA MÊME file. Si l'analyse
relisait le FileList brut, ôter une pièce de la liste ne l'ôterait pas de ce qui
part à l'analyse — une case vidée à l'écran, pleine sur le fil. La règle la plus
lourde vérifie donc exactement cela.
"""
import io
import os
import re

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = io.open(os.path.join(ICI, "ingenierie-dc.js"), encoding="utf-8").read()


def _fn(nom):
    """Le corps d'une fonction JS, de `function nom(` au `function ` suivant.

    Les fonctions du module sont indentées de deux espaces dans l'IIFE ; on
    borne au prochain `\\n  function ` pour ne pas déborder sur la suivante, et
    mesurer chaque règle dans SON périmètre — pas ailleurs dans le fichier."""
    i = JS.index("function " + nom + "(")
    j = JS.find("\n  function ", i + 1)
    return JS[i:(j if j > 0 else len(JS))]


def test_le_depot_offre_une_liste_deroulante_avec_retrait():
    """Le rendu des pièces choisies est une VRAIE liste déroulante (`<select>`),
    et il porte le bouton de retrait. Un `<ul>` mis à la place ferait tomber la
    première assertion ; un rendu sans bouton, la seconde."""
    corps = _fn("aoEnAttenteRendre")
    assert '<select id="ig-ao-sel"' in corps, (
        "le dépôt ne rend pas une liste déroulante des pièces choisies")
    assert 'id="ig-ao-ret"' in corps, (
        "la liste n'offre pas de bouton pour retirer une pièce")
    assert "AO_EN_ATTENTE.splice(" in corps, (
        "le retrait n'ôte pas la pièce de la file : il ne serait que cosmétique")


def test_l_analyse_lit_la_file_d_attente_et_PAS_le_FileList_brut():
    """LA RÈGLE QUI REND LE RETRAIT RÉEL. `aoAnalyser` construit ses lectures
    depuis `AO_EN_ATTENTE`, jamais depuis `f.files`. Relire le FileList brut
    laisserait partir à l'analyse une pièce qu'on vient d'ôter de la liste —
    le retrait deviendrait un mensonge d'écran."""
    tete = _fn("aoAnalyser")
    tete = tete[:tete.index("demander(")]
    assert "AO_EN_ATTENTE[i].file" in tete, (
        "l'analyse ne lit pas la file d'attente : le retrait n'aurait aucun effet")
    assert "f.files" not in tete, (
        "l'analyse relit le FileList brut : une pièce ôtée de la liste "
        "repartirait quand même à l'analyse")


def test_deposer_AJOUTE_a_la_file_sans_la_remplacer():
    """Chaque dépôt s'ajoute au précédent (un même nom remplace le sien), il ne
    remet pas la file à zéro. Une mutation qui réaffecterait `AO_EN_ATTENTE = […]`
    au lieu d'y pousser casserait le cumul — et tomberait ici."""
    corps = _fn("aoDocuments")
    assert "AO_EN_ATTENTE.push(" in corps, "le dépôt n'ajoute pas à la file"
    assert "aoEnAttenteIndex(" in corps, (
        "le dépôt ne dédoublonne pas par nom : deux versions d'une même pièce "
        "coexisteraient")
    assert "AO_EN_ATTENTE = [" not in corps, (
        "le dépôt REMPLACE la file au lieu d'y ajouter : les dépôts successifs "
        "ne se cumuleraient plus")


def test_les_trois_gestes_partagent_la_MEME_file():
    """Dépôt, liste et analyse doivent parler de la même `AO_EN_ATTENTE` —
    c'est ce partage, et lui seul, qui fait qu'ajouter et retirer changent ce
    qui est analysé. Trois files séparées se désynchroniseraient en silence."""
    for nom in ("aoDocuments", "aoEnAttenteRendre", "aoAnalyser"):
        assert "AO_EN_ATTENTE" in _fn(nom), (
            "%s ne touche pas la file partagée AO_EN_ATTENTE" % nom)


def test_sans_piece_choisie_l_analyse_LE_DIT():
    """LE TÉMOIN NÉGATIF. File vide, l'analyse s'arrête et le dit, au lieu
    d'envoyer une requête sans pièce. Retirer cette garde tomberait ici."""
    tete = _fn("aoAnalyser")
    assert "if (!AO_EN_ATTENTE.length)" in tete, (
        "l'analyse ne vérifie plus qu'une pièce a été choisie")
    assert "Choisissez les pièces de la consultation." in tete


def test_la_file_ne_SURVIT_PAS_a_un_rechargement():
    """LA SÛRETÉ, COMME POUR AO_FOURNIES. La file vit en mémoire : jamais relue
    d'un stockage local, sinon les pièces d'une consultation reparaîtraient sur
    la suivante. Elle démarre vide."""
    assert re.search(r"var AO_EN_ATTENTE = \[\]", JS), "AO_EN_ATTENTE non déclarée vide"
    assert not re.search(r"AO_EN_ATTENTE\s*=\s*JSON\.parse", JS), (
        "AO_EN_ATTENTE est rechargée du stockage local : une pièce fuirait "
        "d'une consultation à l'autre")
    assert "ao-en-attente" not in JS, (
        "une clé de stockage local pour la file d'attente est apparue")
