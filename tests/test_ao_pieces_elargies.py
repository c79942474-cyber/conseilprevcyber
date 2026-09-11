# -*- coding: utf-8 -*-
"""Les cinq types de pièces ajoutés au relevé — mesurés sur leur APPORT.

CE QUI A DÉCLENCHÉ CE FICHIER. Un dossier réel déposé avec un « PROGRAMME
FONCTIONNEL » ressortait « 1 fichier n'a pas été reconnu », et les quatre
pièces essentielles étaient portées absentes. Le module ne connaissait que dix
types ; le programme fonctionnel — pièce la plus dense d'un dossier de maîtrise
d'œuvre, celle qui FONDE le CCTP — n'en faisait pas partie. Rien en aval ne
pouvait s'en servir.

LE PIÈGE QUE CES RÈGLES ÉVITENT, ET QU'ON A FAILLI Y TOMBER. Ajouter un type
suffit à faire disparaître le « non reconnu » : la carte s'allume, le dossier
paraît complet. Mais `relever()` ne cherche que dans les pièces que chaque
relevé DÉSIGNE — une pièce reconnue que personne ne lit n'apporte toujours
rien, et l'écran dit le contraire. La règle décisive de ce fichier ne mesure
donc pas la reconnaissance : elle mesure ce que la pièce VERSE au remplissage.

LE TÉMOIN NÉGATIF COMPTE AUTANT. Les marqueurs neufs sont larges — « rapport »,
« calendrier », « programme » sont des mots courants. S'ils cannibalisaient le
RC ou le CCTP, on aurait gagné cinq types et perdu les quatre qui décident de
l'admission du pli.
"""
import pytest

import ao_dc as A

AJOUTES = ("programme", "aapc", "planning", "rapport", "notice")

#: Des noms de fichiers tels qu'ils arrivent vraiment des plateformes acheteur.
CAS = [
    ("programme", "PROGRAMME FONCTIONNEL - Sophia - 25feb2026 2.docx",
     "Le present programme fonctionnel decrit l'expression des besoins."),
    ("aapc", "AAPC_publication_BOAMP.pdf",
     "Avis d'appel public a la concurrence. Section I : pouvoir adjudicateur."),
    ("planning", "Calendrier previsionnel operation.xlsx",
     "Calendrier previsionnel des phases d'etudes."),
    ("rapport", "Rapport etude geotechnique G2 AVP.pdf",
     "Rapport de mission geotechnique G2."),
    ("notice", "Notice de securite ERP.pdf", "Notice de securite incendie."),
]

#: LE TÉMOIN NÉGATIF : les dix types d'origine, qui ne doivent pas bouger.
TEMOINS = [
    ("rc", "RC - reglement de consultation.pdf",
     "Reglement de la consultation. Criteres de jugement."),
    ("cctp", "CCTP lot 3.pdf", "Cahier des clauses techniques particulieres."),
    ("ccap", "CCAP.pdf", "Cahier des clauses administratives particulieres."),
    ("ae", "Acte d engagement.pdf", "Acte d'engagement. Apres avoir pris connaissance."),
    ("ccag", "CCAG-MOE.pdf", "Cahier des clauses administratives generales."),
]


def _code(nom, texte):
    a = A.analyser([{"nom": nom, "texte": texte}])
    return a["pieces"][0]["code"] if a["pieces"] else None


@pytest.mark.parametrize("code,nom,texte", CAS, ids=[c[0] for c in CAS])
def test_les_cinq_types_ajoutes_sont_reconnus(code, nom, texte):
    assert _code(nom, texte) == code, (
        "« %s » n'est pas rangé en %s" % (nom, code))


def test_le_programme_fonctionnel_du_dossier_reel_ne_ressort_plus_inconnu():
    """LE CAS EXACT QUI A ÉTÉ SIGNALÉ, nommé ici pour qu'il ne revienne pas."""
    a = A.analyser([{"nom": "PROGRAMME FONCTIONNEL - Sophia - 25feb2026 2.docx",
                     "texte": "Le present programme fonctionnel."}])
    assert not a["inconnues"], "le programme fonctionnel est encore « non reconnu »"


@pytest.mark.parametrize("code,nom,texte", TEMOINS, ids=[c[0] for c in TEMOINS])
def test_les_types_d_origine_ne_sont_pas_cannibalises(code, nom, texte):
    """LES DIX TYPES D'ORIGINE SE RECONNAISSENT ENCORE EUX-MÊMES.

    CE QUE CETTE RÈGLE GARDE VRAIMENT, après vérification par mutation. On
    l'a écrite en croyant garder la CANNIBALISATION : « rapport »,
    « calendrier », « programme » sont des mots courants, et un marqueur trop
    large volerait le RC. La mutation a montré que non — les marqueurs ajoutés
    sont évalués EN DERNIER et le premier match l'emporte, si bien qu'un
    marqueur neuf, même très large, ne peut pas prendre la place d'un ancien.

    Ce qu'elle garde réellement est plus simple et vaut d'être gardé : que les
    dix types d'origine continuent de se reconnaître. Elle tombe si l'un perd
    ses marqueurs — et elle tomberait aussi le jour où l'ordre d'évaluation
    changerait, ce qui rendrait la cannibalisation possible."""
    assert _code(nom, texte) == code, (
        "« %s » n'est plus rangé en %s : un marqueur ajouté l'a capté" % (nom, code))


@pytest.mark.parametrize("code", AJOUTES)
def test_aucun_type_ajoute_n_est_declare_obligatoire(code):
    """Les porter obligatoires ferait crier au dossier incomplet sur des
    consultations parfaitement régulières : un DCE sans avis publié joint, ou
    sans diagnostic, reste un DCE."""
    assert A.PIECES_MARCHE[code]["obligatoire_dce"] is False


@pytest.mark.parametrize("code", AJOUTES)
def test_chaque_type_ajoute_a_ses_marqueurs(code):
    """Une fiche sans marqueur ne se reconnaît jamais : elle grossit la liste
    des pièces « absentes » sans pouvoir être trouvée."""
    assert code in A._MARQUEURS
    m = A._MARQUEURS[code]
    assert m.get("nom"), "aucun marqueur de nom pour %s" % code


# ══════════════════════════════════════════════════════════════════════════
# LA RÈGLE DÉCISIVE : la pièce reconnue APPORTE quelque chose
# ══════════════════════════════════════════════════════════════════════════
def test_une_piece_ajoutee_verse_vraiment_au_remplissage():
    """CE QUE LA RECONNAISSANCE SEULE NE PROUVE PAS. `relever()` ne cherche que
    dans les pièces que chaque relevé DÉSIGNE. Sans câblage, le programme est
    reconnu, la carte s'allume — et l'acheteur comme l'objet restent vides.
    On mesure donc ce qui est RELEVÉ, pas ce qui est affiché."""
    txt = ("PROGRAMME FONCTIONNEL\n"
           "Maitre d'ouvrage : Communaute d'agglomeration de Sophia\n"
           "Objet : construction d'un centre de donnees de 2 MW\n")
    a = A.analyser([{"nom": "PROGRAMME FONCTIONNEL.docx", "texte": txt}])
    releves = a["pieces"][0]["releves"]
    trouves = {r["cle"] for r in releves if r["trouve"]}
    assert "acheteur" in trouves, (
        "le programme est reconnu mais ne verse pas l'acheteur : il n'apporte "
        "rien au remplissage")
    assert "objet" in trouves, (
        "le programme est reconnu mais ne verse pas l'objet")


def test_l_avis_publie_verse_la_date_limite():
    """L'AAPC porte la date limite, parfois avant que le RC ne soit ouvert.
    C'est sa raison d'être dans le relevé."""
    txt = ("AVIS D'APPEL PUBLIC A LA CONCURRENCE\n"
           "Date limite de reception des offres : 12 mars 2026 a 12h00\n")
    a = A.analyser([{"nom": "AAPC.pdf", "texte": txt}])
    trouves = {r["cle"] for r in a["pieces"][0]["releves"] if r["trouve"]}
    assert "date_limite" in trouves, "l'avis publié ne verse pas la date limite"


def test_les_apports_ne_visent_que_des_releves_et_des_pieces_reels():
    """Une clé mal orthographiée ne lèverait rien : elle ne s'appliquerait
    simplement jamais. La garde de chargement le refuse — on l'éprouve ici."""
    cles = {r["cle"] for r in A.RELEVES}
    assert set(A._APPORTS_PIECES_AJOUTEES) <= cles
    pieces = {c for v in A._APPORTS_PIECES_AJOUTEES.values() for c in v}
    assert pieces <= set(A.PIECES_MARCHE)
