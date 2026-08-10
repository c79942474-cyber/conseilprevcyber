"""À quel titre la pièce est écrite — et pourquoi ce n'est pas un détail.

CE QUI MANQUAIT. Le cadrage de la rédaction disait qui porte le projet, ce que
le centre héberge et ce qui est au marché. Il ne disait jamais à quel titre
NOUS intervenons. Faute de poser la question, la réponse était donnée quand
même : la consigne système annonçait « un ingénieur de maîtrise d'œuvre », pour
toutes les missions, y compris celles où le cabinet ne conçoit rien.

POURQUOI C'EST UN ENGAGEMENT ET PAS UN MOT. Le registre des pièces le dit déjà :
la maîtrise d'œuvre prescrit et vise, elle ne rédige pas à la place de
l'entreprise. Une note rédigée au nom de la maîtrise d'œuvre alors que la
mission est une assistance à maîtrise d'ouvrage PRESCRIT donc au nom d'un rôle
que le contrat ne confie pas. Si le dossier part ainsi, c'est une responsabilité
de conception que personne n'a vendue, et que rien n'assure.

CE QUE CES TESTS VERROUILLENT :

  1. la mission est un CHOIX offert, et la maîtrise d'œuvre en fait partie ;
  2. chaque option dit ce qu'elle change dans le document — sans quoi une liste
     ne vaut pas mieux qu'un champ libre ;
  3. la posture par défaut est ASSUMÉE ET ANNONCÉE, jamais subie en silence ;
  4. la consigne système ne contredit plus la mission demandée — c'était le
     défaut réel : deux ordres opposés, et c'est le système qui l'emporte ;
  5. la mission ne se dit qu'UNE fois dans la demande.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ingenierie_dc as I  # noqa: E402

PROFIL = {"puissance_it_kw": 5000, "pays": "FR"}


def une_piece():
    pcs = I.pieces("APD")
    assert pcs, "il faut au moins une pièce d'avant-projet détaillé"
    return pcs[0]["code"]


# ── 1. Le choix existe, et il est complet ──────────────────────────────────

def test_la_maitrise_d_oeuvre_est_un_choix_offert():
    """Le point demandé : elle était supposée, elle est maintenant proposée."""
    assert "moe" in I.MISSIONS
    assert "maîtrise d'œuvre" in I.MISSIONS["moe"]["nom"].lower()


def test_la_mission_figure_dans_le_cadrage_de_la_redaction():
    ids = [c["id"] for c in I.IDENTIFICATION]
    assert "mission" in ids, ids
    # En tête : elle dit QUI PARLE, ce qui se lit avant ce que le projet impose.
    assert ids[0] == "mission", ids


def test_les_deux_cotes_de_la_table_sont_representes():
    """Une liste qui n'offrirait que des postures de concepteur ramènerait au
    défaut d'origine sous une autre forme."""
    assert "amo" in I.MISSIONS, "l'assistance à maîtrise d'ouvrage doit exister"
    assert "audit" in I.MISSIONS, "la revue d'une conception tierce aussi"


@pytest.mark.parametrize("cle", sorted(I.MISSIONS))
def test_chaque_mission_dit_ce_qu_elle_change(cle):
    """Une option dont l'implication est vague ne change rien au document : elle
    coûte un clic et ne vaut pas mieux qu'un champ libre."""
    o = I.MISSIONS[cle]
    assert o["nom"].strip()
    imp = o["implique"].strip()
    assert len(imp) >= 140, (cle, len(imp))
    assert imp.endswith("."), cle


@pytest.mark.parametrize("cle", sorted(I.MISSIONS))
def test_chaque_mission_dit_ce_que_la_piece_engage_ou_n_engage_pas(cle):
    """Le seul critère qui compte ici : la portée. Une implication qui décrit
    l'ambiance de la mission sans dire ce qu'elle permet d'écrire n'aide pas le
    rédacteur à choisir entre prescrire, exiger et constater."""
    imp = I.MISSIONS[cle]["implique"].lower()
    portee = ("prescri", "engage", "opposable", "exiger", "constat",
              "responsabilité", "couvre")
    assert any(m in imp for m in portee), (cle, imp[:120])


# ── 2. Le défaut est assumé, pas subi ──────────────────────────────────────

def test_sans_choix_la_mission_est_la_maitrise_d_oeuvre_ET_se_declare():
    m = I.mission({})
    assert m["cle"] == I.MISSION_DEFAUT == "moe"
    assert m["choisie"] is False
    assert m.get("reserve"), "un défaut muet est un défaut invisible"


def test_une_mission_choisie_est_marquee_comme_telle():
    m = I.mission({"mission": "amo"})
    assert m["choisie"] is True
    assert "reserve" not in m


def test_une_mission_inventee_ne_passe_pas_pour_un_choix():
    """Une clé inconnue retombe sur le défaut — mais elle ne doit surtout pas
    être présentée comme un choix du lecteur, sinon la réserve disparaît et
    plus rien ne signale que personne n'a tranché."""
    m = I.mission({"mission": "maitrise_doeuvre_globale"})
    assert m["cle"] == "moe"
    assert m["choisie"] is False
    assert m.get("reserve")


# ── 3. La demande porte la mission, une seule fois ─────────────────────────

def test_la_demande_annonce_le_titre_auquel_on_ecrit():
    _, user, _ = I.prompts_piece(PROFIL, "APD", une_piece(), {"mission": "amo"})
    assert "À QUEL TITRE TU ÉCRIS" in user
    assert "Assistance à maîtrise d'ouvrage" in user
    assert "NE CONCEVONS PAS" in user


def test_le_defaut_est_annonce_dans_la_demande_ET_dans_la_piece():
    """DÉFAUT CORRIGÉ. Sans cela, le relecteur lit une pièce rédigée en maîtrise
    d'œuvre sans pouvoir savoir que personne ne l'a décidé — il croit lire un
    choix là où il n'y a qu'une valeur par défaut, et ne le conteste pas."""
    _, user, _ = I.prompts_piece(PROFIL, "APD", une_piece(), {})
    assert "n'a PAS été choisie" in user
    assert "posture par défaut, à confirmer" in user, (
        "la mention doit être portée dans le document produit, pas seulement "
        "connue du rédacteur")


def test_la_mission_ne_se_dit_qu_une_fois():
    """Elle est énoncée en tête ; la répéter dans la liste des cadrages la
    noierait au milieu de choix qui ne se lisent pas comme elle."""
    _, user, _ = I.prompts_piece(PROFIL, "APD", une_piece(), {"mission": "bet"})
    assert user.count("À quel titre nous intervenons") == 0
    assert user.count("À QUEL TITRE TU ÉCRIS") == 1


def test_les_autres_cadrages_restent_transmis():
    """En excluant la mission de la liste, on ne devait pas emporter le reste."""
    _, user, _ = I.prompts_piece(PROFIL, "APD", une_piece(),
                                 {"mission": "moe", "perimetre": "retrofit"})
    assert "Reprise ou rénovation d'un existant" in user
    assert "diagnostic de l'existant" in user


# ── 4. La consigne système ne contredit plus la demande ────────────────────

def test_la_consigne_systeme_n_impose_plus_un_role():
    """LE DÉFAUT RÉEL, ET LE PLUS DIFFICILE À VOIR. La consigne système
    annonçait « un ingénieur de maîtrise d'œuvre ». Avec une mission d'AMO, le
    rédacteur recevait deux ordres opposés — et c'est la consigne système qui
    l'emporte. La pièce prescrivait donc au nom du mauvais rôle, sans que rien
    dans la demande ne le laisse deviner."""
    s = I.SYSTEM_PIECE
    assert "ingénieur de maîtrise d'œuvre" not in s, (
        "la consigne système fige un rôle et écrase la mission demandée")
    assert "LE TITRE AUQUEL TU ÉCRIS" in s, (
        "à défaut d'imposer un rôle, elle doit dire où le lire")


def test_la_consigne_systeme_dit_pourquoi_le_titre_compte():
    s = I.SYSTEM_PIECE.lower()
    assert "prescri" in s and "engage" in s


@pytest.mark.parametrize("cle,interdit", [
    ("amo", "prescription technique signée"),
    ("audit", "réécrit pas la conception"),
])
def test_les_missions_sans_conception_le_disent_explicitement(cle, interdit):
    """Ce sont les deux cas où écrire en maîtrise d'œuvre serait le plus
    coûteux : ils doivent porter l'interdit en toutes lettres, pas le suggérer."""
    assert interdit in I.MISSIONS[cle]["implique"], cle


# ── 5. Le référentiel servi à la page reste cohérent ───────────────────────

def test_le_referentiel_publie_la_mission_avec_ses_options():
    ref = I.referentiel()
    ident = {c["id"]: c for c in ref["identification"]}
    assert "mission" in ident, sorted(ident)
    opts = ident["mission"]["options"]
    cles = {o["cle"] if isinstance(o, dict) and "cle" in o else o
            for o in (opts if isinstance(opts, list) else opts.keys())}
    assert "moe" in cles and "amo" in cles, cles


def test_la_mission_n_entre_dans_aucun_calcul():
    """La promesse faite au lecteur : ces choix cadrent la rédaction, rien de
    plus. Si la mission bougeait un chiffre, la note de calcul dépendrait du
    contrat, ce qui serait indéfendable."""
    import datacenter as D
    a = D.etude(dict(PROFIL))
    b = D.etude(dict(PROFIL, mission="audit"))
    # `etude` renvoie le profil d'entrée en écho : il diffère forcément, puisque
    # c'est là qu'on vient d'ajouter la mission. Ce qu'on éprouve, ce sont les
    # GRANDEURS — comparer les deux réponses en bloc ferait échouer le test sur
    # l'écho, c'est-à-dire sur tout autre chose que ce qu'il prétend vérifier.
    grandeurs = lambda r: {k: v for k, v in r.items() if k != "profil"}  # noqa: E731
    assert grandeurs(a) == grandeurs(b), (
        "la mission ne doit toucher aucune grandeur calculée")
    assert set(a) == set(b), "et elle ne doit ajouter ni retirer aucune rubrique"
