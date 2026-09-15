# -*- coding: utf-8 -*-
"""Remplir au maximum : la fiche entre dans la recherche, sans rouvrir le piège.

CE QUI ÉTAIT MESURÉ. Sur quatre-vingt-treize rubriques, l'extraction n'en
cherchait que QUARANTE-DEUX. Les cinquante et une autres :

  · 6 déclarations — jamais, et c'est la doctrine ;
  · 45 rubriques de source « fiche », dont VINGT-HUIT restées vides (« à
    saisir » ou « invalide »).

Ces vingt-huit — forme juridique, ville d'immatriculation au RCS, capital,
chiffres d'affaires — sont précisément celles que portent un Kbis ou un bilan.
Depuis que le dépôt prend vos propres documents, le module les LISAIT sans
jamais s'en servir pour elles.

POURQUOI C'ÉTAIT INTERDIT, ET POURQUOI ÇA NE L'EST PLUS. Une règle maison le
défendait, avec une raison juste : « Le SIRET du candidat n'est pas dans le
règlement de l'acheteur. L'y chercher ferait remonter le SIRET DE L'ACHETEUR —
et il serait recopié. » Le garde-fou habituel ne protège pas de ce défaut-là :
le SIRET de l'acheteur EST cité, exactement, dans son propre règlement. La
citation existe et la valeur est fausse.

Ce qui a changé, c'est que le dépôt a deux côtés. Une rubrique qui décrit LE
CANDIDAT ne se cherche désormais que dans les documents QUE NOUS AVONS
DÉPOSÉS. Le règlement de l'acheteur n'entre pas dans ce corpus-là.
"""
import collections
import os

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import ao_dc as A                                                # noqa: E402
import ao_extraction as X                                        # noqa: E402

FICHE = {"raison_sociale": "CONSEILPREV"}
RC = "Le pouvoir adjudicateur, SIRET 21750001600019, demande le DC1 et le DC2."
KBIS = "Extrait Kbis. CONSEILPREV SARL au capital de 50 000 euros, RCS Paris."


def _analyse(avec_cabinet=True):
    docs = [{"nom": "01_RC.pdf", "extension": "pdf", "cote": "consultation",
             "texte": RC}]
    if avec_cabinet:
        docs.append({"nom": "KBIS.pdf", "extension": "pdf", "cote": "cabinet",
                     "texte": KBIS})
    return A.analyser(docs)


def _cibles(avec_cabinet=True):
    return X.cibles(A.remplir(fiche=FICHE, analyse=_analyse(avec_cabinet)))


def test_la_fiche_entre_dans_la_recherche():
    """Le gain, compté. Vingt-huit rubriques de plus, sur quatre-vingt-treize.
    Le chiffre exact importe moins que le fait qu'il ne soit plus zéro — mais
    un compte qui retomberait à zéro voudrait dire que l'ouverture a été
    défaite."""
    par = collections.Counter(r["source"] for c in _cibles()
                              for r in c["rubriques"])
    assert par.get("fiche"), (
        "aucune rubrique de la fiche n'est cherchée : les documents que vous "
        "déposez ne servent toujours à rien pour elles")
    assert par.get("consultation") and par.get("saisie"), par
    assert not par.get("declaration"), (
        "une déclaration sur l'honneur est cherchée : la pré-remplir serait "
        "signer à la place de quelqu'un")
    assert not par.get("calcul"), (
        "un calcul se dérive, il ne se lit pas ailleurs")


def test_une_rubrique_du_candidat_ne_voit_QUE_nos_documents():
    """LE PIÈGE, MESURÉ SUR LE CORPUS RÉELLEMENT SERVI. Le règlement porte le
    SIRET de l'acheteur ; il ne doit pas être atteignable depuis une rubrique
    qui décrit le candidat."""
    docs = [{"nom": "01_RC.pdf", "texte": RC},
            {"nom": "KBIS.pdf", "texte": KBIS}]
    corp = X.corpus(docs, _analyse())
    for c in _cibles():
        vu = X.corpus_du_cote(corp, c.get("corpus_cote"))
        textes = " ".join(x["texte"] for x in vu["pieces"])
        if any(r["source"] == "fiche" for r in c["rubriques"]):
            assert "21750001600019" not in textes, (
                "le SIRET de l'acheteur est servi à une rubrique du candidat")
            assert [x["fichier"] for x in vu["pieces"]] == ["KBIS.pdf"]


def test_une_piece_qui_mele_les_deux_donne_DEUX_cibles():
    """Fondre les deux en une seule entrée avec un corpus élargi rouvrirait la
    porte : c'est la raison d'être de la séparation."""
    cotes = collections.Counter(c.get("corpus_cote") for c in _cibles()
                                if c["cle"] == "dc1")
    assert cotes.get("cabinet") == 1 and cotes.get(None) == 1, cotes


def test_sans_document_du_cabinet_aucune_recherche_ne_part_pour_la_fiche():
    """Le repli doit être le SILENCE, pas le corpus entier. Rendre tout faute
    de mieux annulerait la protection exactement quand elle est le plus
    nécessaire — quand nous n'avons rien déposé."""
    corp = X.corpus([{"nom": "01_RC.pdf", "texte": RC}], _analyse(False))
    for c in _cibles(False):
        if any(r["source"] == "fiche" for r in c["rubriques"]):
            assert not X.corpus_du_cote(corp, c["corpus_cote"])["pieces"]


def test_une_cible_sans_corpus_n_est_pas_un_echec(monkeypatch):
    """Lancer l'appel pour récolter un « sans_dossier » par pièce remplirait
    le bilan d'échecs qui ne disent rien, en consommant des jetons pour
    rien."""
    appels = {"n": 0}

    def client(**_kw):
        appels["n"] += 1
        raise AssertionError("aucun appel ne doit partir")

    res = X.lire_le_dossier(
        A.remplir(fiche=FICHE, analyse=_analyse(False)),
        [{"nom": "01_RC.pdf", "texte": ""}], _analyse(False), client=client)
    assert res["echecs"] == [], res["echecs"]
    assert appels["n"] == 0


def test_une_valeur_deja_juste_n_est_pas_remise_en_jeu():
    """On ne recherche pas ce qui est déjà là : relancer une valeur sûre
    contre une valeur lue ne gagne rien et risque de l'écraser."""
    pleine = {"raison_sociale": "CONSEILPREV", "siret": "49453015700038",
              "forme_juridique": "SARL", "adresse": "19 rue X, 75015 Paris"}
    rap = A.remplir(fiche=pleine, analyse=_analyse())
    remplies = {(p["cle"], l["cle"]) for p in rap["pieces"]
                for l in (p.get("rubriques") or []) if l["statut"] == "rempli"}
    vises = {(c["cle"], r["cle"]) for c in X.cibles(rap)
             for r in c["rubriques"]}
    assert remplies, "le témoin est vide"
    assert not (remplies & vises), sorted(remplies & vises)[:6]


def test_une_valeur_INVALIDE_est_elle_remise_en_jeu():
    """Une rubrique invalide porte une valeur que le contrôle refuse — un
    SIRET à treize chiffres. Elle n'est pas « remplie » : elle est fausse, et
    le document sortirait avec."""
    faux = {"raison_sociale": "CONSEILPREV", "siret": "1234567890123"}
    rap = A.remplir(fiche=faux, analyse=_analyse())
    invalides = {(p["cle"], l["cle"]) for p in rap["pieces"]
                 for l in (p.get("rubriques") or [])
                 if l["statut"] == "invalide"}
    assert invalides, "aucune rubrique invalide : la règle est vide"
    vises = {(c["cle"], r["cle"]) for c in X.cibles(rap)
             for r in c["rubriques"]}
    assert invalides <= vises, sorted(invalides - vises)[:6]


def test_les_documents_du_cabinet_ont_un_rang_et_un_nom():
    """LA SÉPARATION DES DEUX CÔTÉS LES AVAIT FAIT RETOMBER SUR LE DÉFAUT :
    lus en dernier — donc les premiers tronqués — et marqués « non
    identifié », ce qui fait ressortir chaque valeur qu'ils portent avec « à
    confirmer ». Une attestation déposée exprès et nommée sans ambiguïté était
    lue comme un fichier anonyme de dernier recours."""
    corp = X.corpus([{"nom": "01_RC.pdf", "texte": RC},
                     {"nom": "KBIS.pdf", "texte": KBIS}], _analyse())
    par = {x["fichier"]: x for x in corp["pieces"]}
    assert par["KBIS.pdf"]["non_identifie"] is False
    assert par["KBIS.pdf"]["sigle"], "le document du cabinet n'a pas de nom"
    # ET L'ORDRE EST CELUI DU RISQUE : l'acheteur commande, nous venons après.
    assert par["01_RC.pdf"]["rang"] < par["KBIS.pdf"]["rang"] < 900


def test_l_atelier_recoit_les_pieces_affirmees_et_le_perimetre():
    """DÉFAUT DE MA MAIN. La page les envoie depuis que l'atelier a cessé de
    repartir de zéro ; la route les ignorait, si bien que l'appel le plus cher
    du module travaillait encore sur les vingt-trois pièces du catalogue quand
    la consultation n'en demande que douze."""
    import io
    src = io.open(os.path.join(ICI, "app.py"), encoding="utf-8").read()
    i = src.index("def api_datacenter_marche_atelier")
    bloc = src[i:src.index("\n@app.route", i)]
    code = "\n".join(l for l in bloc.splitlines()
                     if not l.lstrip().startswith("#"))
    appel = code[code.index("ao_atelier.atelier("):]
    for champ in ("fiche=", "documents=", "analyse=", "saisies=", "rag=",
                  "fournies=", "perimetre="):
        assert champ in appel, (
            "l'atelier est appelé sans « %s » : il travaille sur autre chose "
            "que l'écran" % champ)


def test_l_INTERDIT_des_declarations_tient_SEUL(monkeypatch):
    """LA PROTECTION QUI NE TENAIT QUE PAR COÏNCIDENCE — DEUX FOIS.

    `ao_extraction` écrit pourquoi `SOURCES_INTERDITES` existe : « la mutation
    qui ajoutait "declaration" aux sources SURVIVAIT, parce que le filtre
    d'état la rattrapait ». L'interdit a été écrit — mais rien ne le mesurait
    à part, et le supprimer ne faisait toujours rien tomber. Une batterie
    vient de le remontrer.

    DEUX BARRIÈRES LE DOUBLAIENT, ET IL FAUT LES DEUX POUR L'ÉPROUVER SEUL :
    l'état (`a_declarer` n'appelle aucune recherche) ET la liste positive
    (`declaration` n'est pas dans `SOURCES_CIBLES`). On les neutralise toutes
    les deux ici — l'état sur les lignes, la liste par substitution — pour que
    ce qui reste debout soit l'interdit, et rien d'autre.

    CE QUE ÇA GARANTIT : rendre une déclaration sur l'honneur remplissable par
    un programme demande DEUX retouches délibérées, jamais une distraction.
    """
    monkeypatch.setattr(X, "SOURCES_CIBLES",
                        tuple(X.SOURCES_CIBLES) + ("declaration",))
    rap = A.remplir(fiche=FICHE, analyse=_analyse())
    n = 0
    for p in rap["pieces"]:
        for l in p.get("rubriques") or []:
            if l["source"] == "declaration":
                l["statut"] = X.STATUTS_CIBLES[0]
                n += 1
    assert n, "aucune déclaration au catalogue : la règle est vide"
    vus = {r["source"] for c in X.cibles(rap) for r in c["rubriques"]}
    assert "declaration" not in vus, (
        "les deux autres barrières levées, l'interdit ne retient plus rien : "
        "une déclaration sur l'honneur redevient remplissable par un "
        "programme, et la pré-cocher serait signer à la place de quelqu'un")
