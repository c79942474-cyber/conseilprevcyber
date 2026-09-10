# -*- coding: utf-8 -*-
"""L'aiguillage de la base RAG « Centres de données » vers les livrables
d'ingénierie — jusqu'au stade de maîtrise d'œuvre.

CE QUI EXISTAIT, ET CE QUE CECI AJOUTE. Les livrables d'ingénierie étaient déjà
ancrés sur la base : recherche large, re-classement par un juge, puis la
famille « Centres de données » devant, puis le sous-dossier de la DISCIPLINE de
la pièce. Mais 108 des 460 pièces n'ont AUCUNE discipline — ce sont les pièces
transversales de chaque étape, la maîtrise d'œuvre elle-même — et retombaient
sur la famille ENTIÈRE. L'aiguillage par STADE (loi MOP ESQ→AOR, cycle EPC
FAISA→CSU) les range enfin.

CES RÈGLES MESURENT LE RÉSULTAT : la couverture qui monte, et — tout aussi
important — la précision déjà acquise qui ne bouge pas.
"""
import io
import os

import ingenierie_dc as ig
import rag_store

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = io.open(os.path.join(ICI, "app.py"), encoding="utf-8").read()
CODES_PHASE = [p["code"] if isinstance(p, dict) else p for p in ig.PHASES]


def _toutes_les_pieces():
    for cp in CODES_PHASE:
        for p in ig.pieces(cp):
            yield cp, p


def test_l_aiguillage_par_etape_comble_TOUTES_les_pieces_transversales():
    """L'ÉCART MESURÉ, AVEC TÉMOIN. Sans la phase, des pièces restent sans
    sous-dossier (elles retombent sur la famille entière) ; avec la phase,
    aucune. On mesure les deux — sinon la règle passerait même si l'aiguillage
    ne servait à rien."""
    sans = sum(1 for cp, p in _toutes_les_pieces()
               if not ig.sous_dossiers(p.get("code"), p.get("discipline")))
    avec = sum(1 for cp, p in _toutes_les_pieces()
               if not ig.sous_dossiers(p.get("code"), p.get("discipline"),
                                       phase=cp))
    assert sans > 0, ("le témoin est vide : sans l'aiguillage de stade, aucune "
                      "pièce n'était orpheline — la règle ne mesure plus rien")
    assert avec == 0, (
        "%d pièce(s) d'ingénierie n'ont TOUJOURS pas de sous-dossier une fois "
        "la phase prise en compte : elles interrogent la famille entière au "
        "lieu du stade" % avec)


def test_la_phase_ne_DILUE_pas_une_piece_deja_rangee():
    """LA PRÉCISION ACQUISE NE BOUGE PAS. Une pièce déjà rangée par sa
    discipline ou son exception doit rendre EXACTEMENT le même aiguillage avec
    ou sans la phase — le stade ne sert qu'aux orphelines, il ne se rajoute
    pas devant un lot mieux ciblé."""
    deja = 0
    for cp, p in _toutes_les_pieces():
        base = ig.sous_dossiers(p.get("code"), p.get("discipline"))
        if not base:
            continue
        deja += 1
        avec = ig.sous_dossiers(p.get("code"), p.get("discipline"), phase=cp)
        assert avec == base, (
            "la phase %s a modifié l'aiguillage d'une pièce déjà rangée "
            "(%s) : %r → %r" % (cp, p.get("code"), base, avec))
    assert deja > 100, "trop peu de pièces déjà rangées : la règle ne mesure rien"


def test_chaque_etape_a_son_aiguillage_et_ses_themes_EXISTENT():
    """Toute phase de la page est couverte, et chaque thème est un vrai
    sous-dossier de la base — un intitulé de travers ne remonterait aucun
    document, sans erreur."""
    connus = set(rag_store.THEMES)
    for c in set(CODES_PHASE):
        assert c in ig.SOUS_DOSSIERS_PHASE, (
            "la phase %s n'a pas d'aiguillage documentaire : ses pièces "
            "transversales retombent sur la famille entière" % c)
    for ph, ts in ig.SOUS_DOSSIERS_PHASE.items():
        assert ts, "phase %s sans thème" % ph
        for t in ts:
            assert t in connus, (
                "thème inconnu de la base pour %s : %r" % (ph, t))
            assert t.startswith("Data center"), (
                "un thème hors famille « Centres de données » s'est glissé "
                "dans %s : %r" % (ph, t))


def test_l_aiguillage_route_par_le_SUJET_du_stade_pas_au_hasard():
    """NON-VIDE NE SUFFIT PAS : le stade doit router vers SON sujet. Un dossier
    de consultation va aux pièces de marché, une réception aux essais, une
    esquisse à la conception. Une règle qui n'exigerait que « non vide »
    laisserait passer n'importe quel thème."""
    attendus = {
        "DCE": "Data center / Appels d'offres & CCTP",
        "ACT": "Data center / Appels d'offres & CCTP",
        "AOR": "Data center / Mise en service & essais",
        "CSU": "Data center / Mise en service & essais",
        "ESQ": "Data center / Conception & architecture",
        "DET": "Data center / Réalisation & gouvernance de projet",
    }
    for ph, theme in attendus.items():
        tete = ig.SOUS_DOSSIERS_PHASE[ph][0]
        assert tete == theme, (
            "le stade %s ne route pas d'abord vers son sujet : %r au lieu de "
            "%r" % (ph, tete, theme))


def test_LES_DEUX_chemins_de_generation_PASSENT_la_phase_a_l_aiguillage():
    """SANS CE BRANCHEMENT, LA CARTE NE SERT À RIEN — ET IL Y A DEUX CHEMINS.
    Le livrable rédigé par un modèle ET la trame sans modèle appellent tous
    deux `sous_dossiers`. Les deux doivent transmettre la phase, sinon selon
    qu'un modèle est configuré ou non, la trame dirait autre chose que le
    livrable. On exige donc que CHAQUE appel sur une pièce porte `phase=`."""
    ancre = "ingenierie_dc.sous_dossiers(pc0["
    debut, sites = 0, []
    while True:
        i = APP.find(ancre, debut)
        if i < 0:
            break
        sites.append(APP[i:i + 220])
        debut = i + 1
    assert len(sites) >= 2, (
        "on attend au moins deux chemins de génération appelant sous_dossiers "
        "sur une pièce ; %d trouvé(s)" % len(sites))
    for a in sites:
        # `phase=` doit apparaître AVANT la fermeture logique de l'appel, que
        # signale le `if sous:` qui suit — sinon la phase serait passée à une
        # autre fonction, pas à l'aiguillage.
        avant_if = a.split("if sous", 1)[0]
        assert "phase=" in avant_if, (
            "un chemin de génération appelle sous_dossiers SANS la phase : "
            "l'aiguillage de stade y est mort. %r" % avant_if)


def test_une_phase_inconnue_retombe_sur_la_famille_SANS_planter():
    """LE REPLI RESTE SÛR. Une phase que la carte ne connaît pas rend une liste
    vide — l'appelant retombe sur la famille entière, exactement comme avant —
    et n'émet aucune erreur."""
    assert ig.sous_dossiers("PIECE-QUI-NEXISTE-PAS", None,
                            phase="PHASE-INCONNUE") == []
    assert ig.sous_dossiers("PIECE-QUI-NEXISTE-PAS", None, phase="") == []
