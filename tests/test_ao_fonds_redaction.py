# -*- coding: utf-8 -*-
"""LE MÉMOIRE TECHNIQUE SE RÉDIGE EN CROISANT TROIS SOURCES — ET PAS DEUX.

CE QUI ÉTAIT EN CAUSE, MESURÉ. Le brouillon d'un mémoire technique croisait
les relevés de la consultation (5 champs) et les extraits du dossier déposé
(697 caractères, 2 pièces). Du CABINET, il ne voyait que la FICHE : seize
champs scalaires — raison sociale, SIRET, chiffres d'affaires. AUCUN document.
Ni mémoire technique passé, ni référence, ni CV, ni organigramme, ni
certification.

Or c'est la source la plus utile de toutes pour cette pièce-là : ce qu'on sait
faire s'écrit à partir de ce qu'on a déjà fait. `chercher_socle` interrogeait
bien la base, mais sur un thème de DOCTRINE ; la famille « CONSEILPREV —
pièces du cabinet » et ses dix thèmes n'étaient jamais ouverts.

L'ARBITRAGE QUI REND CE TOUR DÉLICAT, ET QUE CES RÈGLES TIENNENT. Un brouillon
RECOPIE ses extraits et part dans le dossier d'un acheteur. `ao_extraction`
lit la même famille avec `public_only=False` — et sa raison est écrite : rien
ne part, on lit un SIRET pour NOTRE formulaire. Recopier ce réglage ici aurait
fait sortir l'architecture confidentielle d'un client A dans le mémoire remis
au client B.

LA FAMILLE SE SÉPARE DONC EN DEUX, sur la question « qui ce document
décrit-il ? » :

  · CEUX QUI NOUS DÉCRIVENT — CV, organigramme, moyens, QSE. Aucun tiers n'y
    figure. Lus sans filtre de publication, car c'est précisément ce qu'on
    range en interne et qu'on remet pourtant à chaque candidature.

  · CEUX QUI PEUVENT DÉCRIRE UN TIERS — mémoires passés, références clientes.
    Lus SEULEMENT s'ils sont marqués publiables.

  · LES QUATRE AUTRES — identité, assurances, fiscal et social, comptes,
    pouvoirs — ne sont JAMAIS lus ici. Ce sont des pièces de candidature qui se
    joignent telles quelles ; elles n'ont rien à faire dans un mémoire.

ET LE PIÈGE QUI ARRIVE AVEC LA SOURCE. La pièce nomme elle-même son danger :
« rédiger un mémoire générique qui décrit l'entreprise au lieu de répondre aux
critères ». C'est EXACTEMENT ce que des mémoires passés provoquent — ils sont
bien écrits, ils sont à nous, et ils répondent à une autre consultation. La
consigne a donc été durcie dans le même tour, et une règle le tient.
"""
import io
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc                                                     # noqa: E402
import ao_redaction as R                                         # noqa: E402
import rag_store                                                 # noqa: E402

import pytest                                                    # noqa: E402


# ── LE FONDS D'ESSAI : nos pièces, et une pièce d'un client ────────────────
# CHAQUE LIGNE EST UN CAS DE LA BARRIÈRE, pas un décor. Le mémoire « client A »
# est la raison d'être de tout l'arbitrage : il est à nous, il est excellent,
# et il ne doit pas partir chez un autre acheteur.
FONDS = [
    ("Cabinet / Moyens humains, CV & organigramme", False,
     "Organigramme CONSEILPREV",
     u"L'equipe compte 14 ingenieurs dont 4 architectes systemes."),
    ("Cabinet / Moyens matériels & techniques", False,
     "Moyens materiels",
     u"Analyseurs de reseau, camera thermique, banc d'essai CVC."),
    ("Cabinet / Qualifications, certifications & QSE", False,
     "Certifications QSE",
     u"ISO 9001 depuis 2019, ISO 27001 depuis 2022, OPQIBI 1201."),
    ("Cabinet / Mémoires techniques & notes méthodologiques", True,
     "Note methodologique publiable",
     u"Notre methodologie procede en quatre phases : releve, "
     u"dimensionnement, redondance, mise en service."),
    ("Cabinet / Mémoires techniques & notes méthodologiques", False,
     "Memoire technique client A",
     u"L'architecture retenue chez le client A repose sur douze salles."),
    ("Cabinet / Références & attestations de bonne exécution", True,
     "References publiables",
     u"Maitrise d'oeuvre pour trois centres de donnees de 5 a 15 MW."),
    ("Cabinet / Identité & existence légale", False,
     "Extrait Kbis",
     u"Immatriculation au registre du commerce, capital social."),
    ("Cabinet / Comptes, bilans & chiffre d'affaires", False,
     "Bilans 2023-2025",
     u"Resultat net et capitaux propres des trois derniers exercices."),
    ("Data center / Appels d'offres & CCTP", True,
     "CCTP d'une autre consultation",
     u"Le titulaire fournit un PUE inferieur a 1,3 et un plan de reprise."),
]


class Magasin(object):
    """Un magasin qui répond vraiment, et qui JOURNALISE ce qu'on lui demande.

    C'est le journal qui rend la barrière mesurable : sans lui, on ne saurait
    pas SOUS QUELLE RÈGLE chaque moitié de la famille a été interrogée, et une
    règle qui ne regarde que le résultat passerait sur un module qui interroge
    tout avec `public_only=False` et se trouve chanceux sur son échantillon.
    """

    def __init__(self, fonds=None):
        self.appels = []
        self.fonds = FONDS if fonds is None else fonds

    def search(self, query, k=5, public_only=True, theme=None, doc_ids=None):
        self.appels.append({"public_only": public_only,
                            "themes": sorted(theme or [])})
        th = set(theme or [])
        out = []
        for t, pub, titre, texte in self.fonds:
            if th and t not in th:
                continue
            if public_only and not pub:
                continue
            out.append({"title": titre, "theme": t, "text": texte,
                        "content": texte, "date_source": "2026", "score": 1.0})
        return out[:k]


def _piece(cle="memoire_technique"):
    r = ao_dc.remplir(fiche={"raison_sociale": "CONSEILPREV"}, analyse=None)
    return next(p for p in R.pieces_redigeables(r) if p["cle"] == cle)


def _titres(f):
    return {s["titre"] for s in f["sources"]}


# ══════════════════════════════════════════════════════════════════════════
#  1. LE TROISIÈME SOCLE APPORTE VRAIMENT
# ══════════════════════════════════════════════════════════════════════════

def test_le_fonds_du_cabinet_entre_dans_le_brouillon():
    """L'APPORT SE MESURE, il ne se constate pas : sans magasin le brouillon
    voyait zéro document du cabinet, et c'est le zéro qu'il faut battre."""
    p = _piece()
    sans = R.chercher_au_fonds_cabinet(p, None)
    avec = R.chercher_au_fonds_cabinet(p, Magasin())
    assert sans["bloc"] == "" and sans["absent"] == "magasin_non_joint"
    assert len(avec["bloc"]) > 500, len(avec["bloc"])
    assert len(avec["sources"]) >= 4, avec["sources"]


def test_il_arrive_jusqu_au_CONTEXTE_qui_part_au_modele():
    """LE BRANCHEMENT SE MESURE AU BOUT, pas au milieu. Une fonction juste que
    `contexte()` n'appelle pas est du code mort qui rend une règle verte."""
    p = _piece()
    ctx = R.contexte({}, None, p, fonds=R.chercher_au_fonds_cabinet(p, Magasin()))
    assert ctx["fonds_cabinet"], "le contexte ne porte pas le fonds"
    assert ctx["fonds_sources"] and ctx["fonds_absent"] == ""


def test_sans_fonds_le_contexte_le_DIT_au_lieu_de_se_taire():
    """UN CONTEXTE QUI TAIT UNE SOURCE ENTIÈRE laisse le modèle rédiger comme
    s'il l'avait consultée — et c'est invisible à la relecture, ce qui en fait
    le pire des deux défauts."""
    assert R.contexte({}, None, _piece())["fonds_absent"] == "fonds_non_joint"


def test_un_fonds_vide_se_nomme_et_n_est_pas_une_panne():
    """« RIEN TROUVÉ » ET « BASE ABSENTE » NE SE SOIGNENT PAS PAREIL : l'un
    demande de ranger ses mémoires dans la famille, l'autre de joindre le
    magasin. L'écran doit pouvoir nommer le bon remède."""
    f = R.chercher_au_fonds_cabinet(_piece(), Magasin(fonds=[]))
    assert f["absent"] == "aucun_extrait" and f["sources"] == []


# ══════════════════════════════════════════════════════════════════════════
#  2. LA BARRIÈRE — CE QUI NE DOIT PAS PARTIR CHEZ L'ACHETEUR
# ══════════════════════════════════════════════════════════════════════════

def test_un_memoire_INTERNE_ecrit_pour_un_autre_client_ne_part_PAS():
    """LA RÈGLE QUI JUSTIFIE TOUT L'ARBITRAGE. Un mémoire écrit pour l'acheteur
    A porte son architecture ; le recopier dans le mémoire remis à l'acheteur B
    n'est pas une commodité, c'est une fuite."""
    f = R.chercher_au_fonds_cabinet(_piece(), Magasin())
    assert "Memoire technique client A" not in _titres(f)
    assert "client A" not in f["bloc"]


def test_une_reference_ou_un_memoire_PUBLIABLE_part_bien():
    """LE TÉMOIN POSITIF DE LA BARRIÈRE. Sans lui, une règle qui constate une
    exclusion passerait aussi bien sur un module qui n'ouvre jamais ces deux
    thèmes — et l'apport serait nul sans que rien ne tombe."""
    t = _titres(R.chercher_au_fonds_cabinet(_piece(), Magasin()))
    assert "Note methodologique publiable" in t
    assert "References publiables" in t


def test_nos_propres_moyens_partent_MEME_non_publies():
    """C'EST PRÉCISÉMENT CE QU'ON RANGE EN INTERNE et qu'on remet pourtant à
    chaque candidature : un organigramme, une liste d'outils, une
    certification. Exiger `public_only` les aurait rendus illisibles, et la
    règle serait restée verte avec un apport nul."""
    t = _titres(R.chercher_au_fonds_cabinet(_piece(), Magasin()))
    for titre in ("Organigramme CONSEILPREV", "Moyens materiels",
                  "Certifications QSE"):
        assert titre in t, titre


def test_les_pieces_de_CANDIDATURE_ne_sont_jamais_lues_ici():
    """UN KBIS ET DES BILANS N'ONT RIEN À FAIRE DANS UN MÉMOIRE TECHNIQUE. Ce
    ne sont pas des choses qu'on raconte : ce sont des pièces qu'on joint."""
    t = _titres(R.chercher_au_fonds_cabinet(_piece(), Magasin()))
    assert "Extrait Kbis" not in t and "Bilans 2023-2025" not in t


def test_le_fonds_HORS_famille_ne_passe_pas_par_cette_porte():
    """LA DOCTRINE A DÉJÀ SA PORTE — `chercher_socle`. Laisser un CCTP d'une
    autre consultation entrer par celle-ci le ferait présenter au modèle comme
    « un document du cabinet », donc comme un fait sur NOS moyens."""
    t = _titres(R.chercher_au_fonds_cabinet(_piece(), Magasin()))
    assert "CCTP d'une autre consultation" not in t


def test_les_deux_moitiés_sont_interrogees_sous_DEUX_regles_distinctes():
    """ON REGARDE LES APPELS, PAS SEULEMENT LE RÉSULTAT. Un module qui
    interrogerait toute la famille avec `public_only=False` rendrait le même
    résultat sur un échantillon où rien d'interne n'est pertinent — et
    laisserait fuir au premier dossier réel.

    LA FAMILLE COMPTE MAINTENANT TROIS LOTS ET NON DEUX, et ce qu'on mesure
    ici n'a pas changé : que le lot qui peut décrire un CLIENT — mémoires
    passés, références — ne soit lu QUE s'il est publiable. Le troisième lot,
    la documentation, se lit sans filtre et c'est assumé : le risque qu'il
    porte est le droit d'auteur d'un tiers, contre quoi un régime de
    publication ne peut rien. Sa règle propre est dans
    `test_ao_documentation_cabinet.py`.
    """
    mag = Magasin()
    R.chercher_au_fonds_cabinet(_piece(), mag)
    assert len(mag.appels) == 3, mag.appels
    # UN SEUL APPEL EXIGE « PUBLIABLE », et c'est celui du lot des tiers.
    publiables = [a["themes"] for a in mag.appels if a["public_only"]]
    assert len(publiables) == 1, mag.appels
    assert set(publiables[0]) == set(R.FONDS_TIERS)
    sans_filtre = set()
    for a in mag.appels:
        if not a["public_only"]:
            sans_filtre |= set(a["themes"])
    assert sans_filtre == set(R.FONDS_NOUS) | set(R.FONDS_DOCUMENTATION), \
        sans_filtre


def test_les_deux_tiers_sont_DISJOINTS_et_tous_de_la_famille():
    """UN THÈME DANS LES DEUX LISTES SERAIT LU DEUX FOIS, dont une sans filtre
    — la barrière serait contournée par sa propre table."""
    assert not set(R.FONDS_NOUS) & set(R.FONDS_TIERS)
    famille = set(rag_store.themes_famille(rag_store.FAMILLE_CABINET))
    assert set(R.FONDS_NOUS) <= famille
    assert set(R.FONDS_TIERS) <= famille


def test_un_theme_renomme_dans_rag_store_se_VOIT():
    """UNE CHAÎNE MORTE NE RAMÈNE RIEN, EN SILENCE. Le brouillon perdrait une
    source entière sans que personne le sache : `_fonds_themes_connus`
    confronte les deux tables, et cette règle mesure qu'elle le fait."""
    nous, tiers, doc = R._fonds_themes_connus()
    assert len(nous) == len(R.FONDS_NOUS)
    assert len(tiers) == len(R.FONDS_TIERS)
    assert len(doc) == len(R.FONDS_DOCUMENTATION)

    import rag_store as RS
    garde = RS.THEME_FAMILLES
    try:
        RS.THEME_FAMILLES = tuple(
            (f, tuple(t for t in ts if t not in R.FONDS_TIERS))
            for f, ts in garde)
        n2, t2, _d2 = R._fonds_themes_connus()
        assert t2 == [], "un thème disparu de rag_store est encore interrogé"
        assert n2 == list(R.FONDS_NOUS)
        assert R.chercher_au_fonds_cabinet(
            _piece(), Magasin(fonds=[]))["absent"] == "aucun_extrait"
    finally:
        RS.THEME_FAMILLES = garde


# ══════════════════════════════════════════════════════════════════════════
#  3. LA CONSIGNE DIT LAQUELLE DES TROIS SOURCES COMMANDE
# ══════════════════════════════════════════════════════════════════════════

def _brief(avec_fonds=True):
    p = _piece()
    f = R.chercher_au_fonds_cabinet(p, Magasin()) if avec_fonds else None
    return R.brief(R.contexte({}, None, p, fonds=f))


def test_le_brief_NOMME_les_documents_du_cabinet_et_les_situe():
    b = _brief()
    assert "DOCUMENTS DU CABINET" in b
    assert "Organigramme CONSEILPREV" in b
    assert "MATIÈRE" in b and "MODÈLE" in b


def test_le_brief_INTERDIT_de_reprendre_le_plan_d_un_memoire_passe():
    """LE PIÈGE ARRIVE AVEC LA SOURCE, et il fallait durcir la consigne dans le
    même tour. La pièce le nomme elle-même : « rédiger un mémoire générique qui
    décrit l'entreprise au lieu de répondre aux critères ». Un mémoire passé
    est le chemin le plus court vers exactement cela."""
    b = _brief()
    assert "NE RECOPIEZ AUCUN PLAN" in b
    assert "critères de jugement de CETTE" in b and "LEUR ordre" in b


def test_le_brief_autorise_le_FAIT_et_interdit_le_moyen_invente():
    """UN MOYEN AFFIRMÉ ET FAUX SE DÉCOUVRE À L'EXÉCUTION DU MARCHÉ : c'est la
    faute la plus coûteuse que ce module puisse provoquer."""
    b = _brief()
    assert "À COMPLÉTER" in b
    assert "ne s'invente pas" in b


def test_sans_fonds_le_brief_INTERDIT_d_affirmer_un_moyen():
    """LE TÉMOIN NÉGATIF DE LA CONSIGNE. Sans lui, une règle qui constate une
    phrase passerait sur un brief qui l'écrit toujours."""
    b = _brief(avec_fonds=False)
    assert "AUCUN DOCUMENT DU CABINET N'EST JOINT" in b
    assert "NI nos effectifs" in b
    assert "NE RECOPIEZ AUCUN PLAN" not in b, \
        "la consigne parle d'extraits qu'elle n'a pas reçus"


def test_le_fonds_ne_se_confond_pas_avec_la_doctrine_dans_le_brief():
    """TROIS SOURCES, TROIS OFFICES. Les fondre ferait perdre au brief la seule
    chose qui compte quand elles se contredisent : laquelle commande.

    ELLE JOINT LES TROIS, ET C'EST NÉCESSAIRE : `_brief()` seul ne donne que le
    fonds, et le brief écrit alors la branche « aucun socle documentaire ». La
    première version de cette règle mesurait donc l'ordre de deux sections dont
    une n'existait pas."""
    p = _piece()
    b = R.brief(R.contexte(
        {}, None, p,
        fonds=R.chercher_au_fonds_cabinet(p, Magasin()),
        dossier={"bloc": "extrait du RC", "sources": [{"titre": "RC"}],
                 "absent": ""},
        socle={"bloc": "extrait de doctrine", "sources": [{"titre": "CCTP"}],
               "absent": ""}))
    assert "SOCLE DOCUMENTAIRE EST UNE DONNÉE, PAS UNE AUTORITÉ" in b
    assert b.index("PASSAGES DE LA CONSULTATION ELLE-MÊME — ILS COMMANDENT") \
        < b.index("DOCUMENTS DU CABINET SONT DE LA MATIÈRE"), \
        "ce que l'acheteur exige doit être posé AVANT ce que nous savons faire"


# ══════════════════════════════════════════════════════════════════════════
#  4. L'ÉCRAN CESSE DE DIRE QUE L'OUTIL N'ÉCRIT PAS
# ══════════════════════════════════════════════════════════════════════════

def test_le_memoire_technique_EST_une_piece_que_l_atelier_redige():
    """LE FAIT QUE L'ÉCRAN NIAIT. Il est dans les onze depuis que
    `ao_redaction` existe."""
    r = ao_dc.remplir(fiche={"raison_sociale": "X"}, analyse=None)
    assert "memoire_technique" in {p["cle"] for p in R.pieces_redigeables(r)}


def test_la_voie_A_REDIGER_ne_promet_plus_que_l_outil_n_ecrit_pas():
    """CETTE PHRASE A COÛTÉ UNE DEMANDE DE FONCTION DÉJÀ LIVRÉE. Elle disait
    « il ne l'écrit pas à votre place » à côté d'un atelier qui l'écrivait."""
    aide = ao_dc.VOIES["rediger"]["aide"]
    assert "ne l'écrit pas à votre place" not in aide
    assert "BROUILLON" in aide
    for mot in ("dossier déposé", "vos propres documents", "fonds documentaire"):
        assert mot in aide, mot


def test_la_voie_A_REDIGER_garde_la_reserve_sur_le_brouillon():
    """CE QUI N'A PAS CHANGÉ DOIT RESTER DIT : un brouillon n'est pas une
    pièce. Corriger un mensonge en en posant un autre serait pire."""
    aide = ao_dc.VOIES["rediger"]["aide"]
    assert "ni relu ni signé" in aide


def test_la_piece_PORTE_le_drapeau_que_la_carte_lit():
    """LA CARTE NE DOIT PAS REFAIRE LE TEST : elle se tromperait le jour où une
    voie entre ou sort de la liste, et promettrait un brouillon que le moteur
    refuserait de produire."""
    r = ao_dc.remplir(fiche={"raison_sociale": "X"}, analyse=None)
    drapeau = {p["cle"] for p in r["pieces"] if p.get("redigeable")}
    atelier = {p["cle"] for p in R.pieces_redigeables(r)}
    assert drapeau == atelier and len(drapeau) == 11


def test_la_liste_des_voies_redigeables_est_DECLAREE_une_seule_fois():
    """TROIS ENDROITS EN DÉPENDENT. Trois copies du même couple de chaînes
    auraient divergé, et la divergence se serait vue comme un bouton qui
    n'écrit rien."""
    assert ao_dc.VOIES_REDIGEABLES == ("rediger", "completer")
    src = io.open(os.path.join(ICI, "ao_redaction.py"), encoding="utf-8").read()
    assert '("rediger", "completer")' not in src, \
        "ao_redaction recopie la liste au lieu de la lire"
    assert "ao_dc.VOIES_REDIGEABLES" in src


def test_la_carte_ne_dit_plus_qu_une_piece_redigeable_s_ecrit_AILLEURS():
    """SUR UN MÉMOIRE TECHNIQUE — bloquant, et rédigé par l'atelier — la carte
    annonçait qu'il fallait l'écrire hors de l'outil, à côté d'un atelier qui
    l'écrivait. Le geste « je l'ai fournie » reste offert : l'avoir écrite
    soi-même est légitime. Ce qui change, c'est qu'on ne prétend plus que
    c'est le seul chemin."""
    js = io.open(os.path.join(ICI, "ingenierie-dc.js"), encoding="utf-8").read()
    i = js.index("Elle ne se remplit pas ici")
    bloc = js[max(0, i - 700):i + 300]
    assert "p.redigeable" in bloc, \
        "la phrase est servie sans distinguer les pièces que l'atelier rédige"
    assert "L'atelier en rédige un brouillon" in bloc


# ══════════════════════════════════════════════════════════════════════════
#  5. LE BILAN DES TROIS SOCLES SORT AVEC LE BROUILLON
# ══════════════════════════════════════════════════════════════════════════

def test_le_rendu_compte_les_trois_socles_et_nomme_les_manquants():
    """DEUX CHEMINS ÉCRIVENT, ET LEURS BROUILLONS SE LISENT PAREIL. L'atelier
    joint les trois sources ; `/marche/rediger` n'a pas les documents du marché
    dans sa charge. Sans ce bilan, rien ne distingue un brouillon nourri d'un
    brouillon maigre — et c'est le maigre qu'on relirait le moins, puisqu'il a
    l'air fini.

    ON MESURE LA COMPOSITION DU BILAN SANS APPELER LE MODÈLE : `rediger` n'est
    pas joignable sans clé, mais le bilan se construit sur `contexte`, qui est
    pure. La règle le reconstruit à l'identique et vérifie les deux sens."""
    p = _piece()
    maigre = R.contexte({}, None, p)
    nourri = R.contexte({}, None, p,
                        fonds=R.chercher_au_fonds_cabinet(p, Magasin()),
                        dossier={"bloc": "x", "sources": [{"titre": "RC"}],
                                 "absent": ""},
                        socle={"bloc": "y", "sources": [{"titre": "D"}],
                               "absent": ""})
    assert len(nourri["fonds_sources"]) >= 4
    assert len(nourri["dossier_sources"]) == 1
    assert len(nourri["socle_sources"]) == 1
    manques = [m for m in (maigre["dossier_absent"], maigre["fonds_absent"],
                           maigre["socle_absent"]) if m]
    assert len(manques) == 3, manques
    assert [m for m in (nourri["dossier_absent"], nourri["fonds_absent"],
                        nourri["socle_absent"]) if m] == []


# ── UN FAUX FOURNISSEUR, POUR EXÉCUTER `rediger()` SANS CLÉ ───────────────
#
# POURQUOI IL FALLAIT EN VENIR LÀ. Sans lui, aucune règle n'exécutait
# `rediger()` : elles mesuraient `chercher_au_fonds_cabinet`, `contexte` et
# `brief` — toutes justes — pendant que la LIGNE QUI LES RELIE n'était mesurée
# nulle part. Une mutation remplaçant `fonds=chercher_au_fonds_cabinet(...)`
# par `fonds=None` a survécu : trois fonctions correctes et un fil coupé.
#
# CE N'EST PAS UNE SIMULATION DU MODÈLE. On ne mesure rien de ce qu'il écrit :
# on mesure ce que `rediger` LUI DONNE et ce qu'il RAPPORTE. `ao_atelier`
# emprunte déjà ce chemin — il remplace `_client` pour partager une connexion
# — et la règle emprunte le même.
class _Usage(object):
    input_tokens = 100
    output_tokens = 50
    cache_creation_input_tokens = 0
    cache_read_input_tokens = 0


class _Reponse(object):
    stop_reason = "end_turn"
    model = "faux-modele"
    usage = _Usage()

    def __init__(self, texte):
        bloc = type("B", (), {"type": "text", "text": texte})()
        self.content = [bloc]


class _Flux(object):
    def __init__(self, journal, kw):
        self.journal, self.kw = journal, kw

    def __enter__(self):
        self.journal.append(self.kw)
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return _Reponse("## Brouillon\n\nUn texte de %d signes." % 42)


class _FauxAnthropic(object):
    """Le module `anthropic`, réduit à ce que `rediger` en touche."""

    class NotFoundError(Exception):
        pass

    class AuthenticationError(Exception):
        pass

    class RateLimitError(Exception):
        pass

    class APIStatusError(Exception):
        pass

    class APIConnectionError(Exception):
        pass

    def __init__(self):
        self.journal = []
        faux = self

        class Messages(object):
            def stream(self, **kw):
                return _Flux(faux.journal, kw)

        class Client(object):
            messages = Messages()

        self.Anthropic = Client


def _rediger_sous_double(rag, monkeypatch, corpus_dossier=None):
    """`rediger()` exécutée pour de vrai, avec un faux fournisseur."""
    faux = _FauxAnthropic()
    monkeypatch.setattr(R, "_client", lambda: faux)
    r = ao_dc.remplir(fiche={"raison_sociale": "CONSEILPREV"}, analyse=None)
    return R.rediger("memoire_technique", r, analyse=None, rag=rag,
                     corpus_dossier=corpus_dossier), faux


def test_rediger_OUVRE_vraiment_le_fonds_du_cabinet(monkeypatch):
    """LE FIL ENTIER, EXÉCUTÉ. Les trois fonctions peuvent être justes et la
    ligne qui les relie manquer : c'est ce qu'une mutation a montré."""
    rap, faux = _rediger_sous_double(Magasin(), monkeypatch)
    assert rap["socles"]["cabinet"] >= 4, rap["socles"]
    assert rap["fonds_absent"] == ""
    assert {s["titre"] for s in rap["fonds_sources"]} >= {
        "Organigramme CONSEILPREV", "Certifications QSE"}
    # ET CE QUI PART VRAIMENT AU MODÈLE porte bien les extraits.
    consigne = faux.journal[0]["system"][0]["text"]
    assert "DOCUMENTS DU CABINET" in consigne
    assert "Organigramme CONSEILPREV" in consigne


def test_rediger_SANS_magasin_ne_fait_pas_semblant(monkeypatch):
    """LE TÉMOIN NÉGATIF DU FIL. Sans lui, la règle ci-dessus passerait sur un
    module qui compte toujours quatre sources."""
    rap, faux = _rediger_sous_double(None, monkeypatch)
    assert rap["socles"]["cabinet"] == 0
    assert rap["fonds_absent"] == "magasin_non_joint"
    assert "AUCUN DOCUMENT DU CABINET N'EST JOINT" in \
        faux.journal[0]["system"][0]["text"]


def test_le_memoire_du_client_A_n_atteint_JAMAIS_le_fournisseur(monkeypatch):
    """LA BARRIÈRE, MESURÉE AU DERNIER POINT OÙ ELLE COMPTE : ce qui sort de
    la machine. Toutes les règles précédentes regardent des dictionnaires ;
    celle-ci regarde l'appel."""
    _rap, faux = _rediger_sous_double(Magasin(), monkeypatch)
    envoye = (faux.journal[0]["system"][0]["text"]
              + str(faux.journal[0]["messages"]))
    assert "client A" not in envoye
    assert "Extrait Kbis" not in envoye and "Bilans" not in envoye


def test_le_fonds_est_BORNÉ_pour_ne_pas_noyer_la_consultation():
    """SANS BORNE, UN MÉMOIRE PASSÉ DE TRENTE PAGES ÉCRASE LES RELEVÉS de la
    consultation dans le brief — et le brouillon devient fidèle à ce qu'on a
    écrit ailleurs, distrait du dossier auquel il répond. C'est exactement le
    piège que la pièce elle-même nomme.

    LA RÈGLE PRÉCÉDENTE NE LE VOYAIT PAS : elle exigeait « plus de 500
    caractères », ce qu'un plafond dix mille fois trop grand satisfait aussi."""
    gros = [("Cabinet / Moyens humains, CV & organigramme", False,
             "Pavé %d" % i, u"ligne de remplissage. " * 400)
            for i in range(30)]
    f = R.chercher_au_fonds_cabinet(_piece(), Magasin(fonds=gros))
    assert f["bloc"], "rien n'est ressorti : la règle ne mesure pas la borne"
    assert len(f["bloc"]) <= R.FONDS_CARACTERES * 1.5, \
        "le fonds déborde sa borne : %d caractères pour un plafond de %d" \
        % (len(f["bloc"]), R.FONDS_CARACTERES)


def test_le_bilan_est_bien_POSE_dans_le_rendu_de_rediger():
    """LA RÈGLE PRÉCÉDENTE MESURE LA MATIÈRE DU BILAN ; celle-ci mesure qu'il
    est effectivement rendu. Sans elle, le bilan pourrait être juste et
    n'atteindre jamais la page."""
    src = io.open(os.path.join(ICI, "ao_redaction.py"), encoding="utf-8").read()
    i = src.index('"markdown": texte,')
    bloc = src[i:i + 1400]
    for cle in ('"socles"', '"consultation"', '"cabinet"', '"doctrine"',
                '"manques"', '"fonds_sources"', '"fonds_absent"'):
        assert cle in bloc, cle
