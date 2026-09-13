# -*- coding: utf-8 -*-
"""L'atelier : la boucle, l'éventail, le second socle, et ce qu'on réclame.

CE QUE CES RÈGLES MESURENT. Le remplissage était une PASSE — analyser, remplir,
rédiger, fin. Le mémoire technique qu'on venait d'écrire contenait l'équipe,
les moyens et les références que le DC2 redemandait trois cases plus loin, et
personne ne le relisait. Ces règles mesurent l'APPORT de chaque tour, pas la
présence d'une boucle : une boucle qui tourne sans rien ajouter serait verte
sous une règle qui compterait les tours.

TOUT EST INJECTÉ — clients, exécuteur, plafond. Aucune règle d'ici n'ouvre de
socket ni ne demande de clé.
"""
import threading
import time
import types

import ao_atelier as A
import ao_dc as D
import ao_extraction as X
import ao_redaction as R


RC = u"""REGLEMENT DE CONSULTATION

Pouvoir adjudicateur : SYNDICAT MIXTE NUMERIQUE DE L'EURE, 27000 Evreux.
Objet du marche : conception-realisation d'un centre de donnees de 2,5 MW IT.

Moyens exiges du candidat : le titulaire mobilise une equipe dediee, des procedures
de suivi documentees et des outils de metrologie etalonnes.

Remise des offres : le 14 novembre 2026 a 12h00, sur la plateforme PLACE.
Criteres : valeur technique 60 %, prix 40 %. Duree : 30 mois.
"""
DOCS = [{"nom": "RC.pdf", "texte": RC}]
FICHE = {"denomination": "CONSEILPREV", "siret": "91000000000015"}
VRAI = "Remise des offres : le 14 novembre 2026 a 12h00, sur la plateforme PLACE."
INVENTE_DANS_BROUILLON = ("L equipe dediee compte douze ingenieurs et se "
                          "reunit chaque semaine sur le site du client.")


def _sdk(create):
    class _Anthropic:
        def __init__(self, *a, **k):
            self.messages = types.SimpleNamespace(create=create, stream=None)
    m = types.ModuleType("anthropic")
    m.Anthropic = _Anthropic
    return m


def _extraction(par_appel):
    """Un faux SDK d'extraction : `par_appel(kw, n)` rend les propositions."""
    etat = {"n": 0}

    class _B:
        type = "tool_use"
        name = X.OUTIL

        def __init__(self, d):
            self.input = d

    class _R:
        def __init__(self, d):
            self.content = [_B(d)]
            self.usage = None
            self.model = "faux"

    def create(**kw):
        etat["n"] += 1
        return _R({"rubriques": par_appel(kw, etat["n"])})
    return _sdk(create)


def _cles(kw):
    return (kw["tools"][0]["input_schema"]["properties"]["rubriques"]
            ["items"]["properties"]["rubrique"]["enum"])


RIEN = _extraction(lambda kw, n: [])


def _progressif(par_tour=3):
    """Rend quelques rubriques à chaque appel — de quoi faire avancer la boucle."""
    vus = set()

    def f(kw, _n):
        neufs = [c for c in _cles(kw) if c not in vus][:par_tour]
        vus.update(neufs)
        return [{"rubrique": c, "valeur": "14 novembre 2026", "citation": VRAI}
                for c in neufs]
    return _extraction(f)


# ═══════════════════════════════════════════════════════════════════════════
#  LA BOUCLE : elle s'arrête sur l'APPORT, pas sur un compteur
# ═══════════════════════════════════════════════════════════════════════════

def test_la_boucle_s_arrete_quand_un_tour_n_apporte_PLUS_RIEN():
    res = A.atelier(fiche=FICHE, documents=DOCS, client_extraction=RIEN,
                    rediger=False)
    assert res["tours"] == 1, \
        "la boucle a tourné %d fois sans rien gagner" % res["tours"]


def test_la_boucle_CONTINUE_tant_qu_elle_apporte():
    res = A.atelier(fiche=FICHE, documents=DOCS,
                    client_extraction=_progressif(2), rediger=False)
    assert res["tours"] > 1, "la boucle s'est arrêtée alors qu'elle gagnait"
    assert res["journal"][0]["gagnees"] > 0
    assert res["remplies"] > res["journal"][0]["remplies_avant"]


def test_le_plafond_de_tours_est_un_GARDE_FOU_et_il_TIENT():
    """Un apport qui se répéterait indéfiniment ne doit pas faire tourner
    l'atelier sans fin."""
    res = A.atelier(fiche=FICHE, documents=DOCS,
                    client_extraction=_progressif(1), rediger=False,
                    tours_max=2)
    assert res["tours"] == 2


def test_le_journal_dit_ce_que_CHAQUE_tour_a_apporte():
    """Un atelier qui rend un résultat sans dire ce qu'il a fait ne se
    débogue pas."""
    res = A.atelier(fiche=FICHE, documents=DOCS,
                    client_extraction=_progressif(2), rediger=False)
    assert len(res["journal"]) == res["tours"]
    for j in res["journal"]:
        for k in ("tour", "remplies_avant", "lues", "gagnees", "rejets"):
            assert k in j
    assert sum(j["lues"] for j in res["journal"]) == len(res["extraits"])


# ═══════════════════════════════════════════════════════════════════════════
#  LE BROUILLON RELU — c'est tout l'objet de la boucle
# ═══════════════════════════════════════════════════════════════════════════

def _redaction(markdown):
    def create(**kw):
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text=markdown)],
            stop_reason="end_turn", model="faux",
            usage=types.SimpleNamespace(input_tokens=1, output_tokens=1))
    class _Flux:
        def __init__(self, m):
            self.m = m

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get_final_message(self):
            return create()
    class _Anthropic:
        def __init__(self, *a, **k):
            self.messages = types.SimpleNamespace(
                create=create, stream=lambda **kw: _Flux(markdown))
    m = types.ModuleType("anthropic")
    m.Anthropic = _Anthropic
    for nom in ("NotFoundError", "AuthenticationError", "RateLimitError",
                "APIConnectionError", "APIStatusError"):
        setattr(m, nom, type(nom, (Exception,), {}))
    return m


def test_un_BROUILLON_relu_remplit_ce_que_le_dossier_ne_portait_PAS():
    """LE POINT DE LA BOUCLE. Le passage n'existe dans AUCUNE pièce déposée :
    il n'existe que dans le brouillon que nous venons d'écrire. S'il remplit
    une rubrique, c'est que le tour suivant a bien relu ce que le tour
    précédent a produit."""
    def lit_le_brouillon(kw, _n):
        if INVENTE_DANS_BROUILLON in kw["messages"][0]["content"]:
            return [{"rubrique": _cles(kw)[0], "valeur": "douze ingénieurs",
                     "citation": INVENTE_DANS_BROUILLON}]
        return []

    res = A.atelier(fiche=FICHE, documents=DOCS,
                    client_extraction=_extraction(lit_le_brouillon),
                    client_redaction=_redaction("## Moyens\n\n"
                                                + INVENTE_DANS_BROUILLON))
    assert res["brouillons"], "aucun brouillon produit"
    assert any(e["valeur"] == "douze ingénieurs" for e in res["extraits"].values()), \
        "le brouillon produit n'a jamais été relu"


def test_un_brouillon_entre_sous_son_PROPRE_nom_jamais_comme_piece_de_l_acheteur():
    """Fondre un brouillon dans le dossier déposé ferait citer comme exigence
    de l'acheteur une phrase que nous avons écrite nous-mêmes."""
    docs = A._brouillons_en_corpus([{"cle": "moyens", "markdown": "texte"}])
    assert docs and docs[0]["nom"].startswith("brouillon-")
    an = A._analyse_avec_brouillons(D.analyser(DOCS),
                                    [{"cle": "moyens", "markdown": "texte"}])
    noms = [x["fichier"] for x in an["inconnues"]]
    assert "brouillon-moyens.md" in noms
    assert all(p["fichier"] != "brouillon-moyens.md" for p in an["pieces"]), \
        "un brouillon est rangé parmi les pièces IDENTIFIÉES de l'acheteur"


def test_les_brouillons_ne_se_REFONT_pas_a_chaque_tour():
    """Onze appels de modèle par tour pour réécrire un texte déjà rendu, et un
    résultat qui change d'un tour à l'autre."""
    appels = {"n": 0}

    def create(**kw):
        appels["n"] += 1
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text="## Note\n\ntexte")],
            stop_reason="end_turn", model="faux",
            usage=types.SimpleNamespace(input_tokens=1, output_tokens=1))

    class _Flux2:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        @staticmethod
        def get_final_message():
            return create()

    class _Anthropic:
        def __init__(self, *a, **k):
            self.messages = types.SimpleNamespace(
                create=create, stream=lambda **kw: _Flux2())
    m = types.ModuleType("anthropic")
    m.Anthropic = _Anthropic
    for nom in ("NotFoundError", "AuthenticationError", "RateLimitError",
                "APIConnectionError", "APIStatusError"):
        setattr(m, nom, type(nom, (Exception,), {}))

    res = A.atelier(fiche=FICHE, documents=DOCS,
                    client_extraction=_progressif(2), client_redaction=m)
    assert res["tours"] > 1
    assert appels["n"] == len(res["brouillons"]), \
        "%d appels de rédaction pour %d brouillons sur %d tours" % (
            appels["n"], len(res["brouillons"]), res["tours"])


def test_une_REDACTION_qui_tombe_n_emporte_pas_les_autres():
    appels = {"n": 0}

    def create(**kw):
        appels["n"] += 1
        if appels["n"] == 1:
            raise R.RedactionError("cadence", 429, "limite simulée")
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text="## Note\n\ntexte")],
            stop_reason="end_turn", model="faux",
            usage=types.SimpleNamespace(input_tokens=1, output_tokens=1))

    # LE VRAI `rediger` PASSE PAR LE FLUX, PAS PAR L'APPEL DIRECT — un mémoire
    # technique atteint plusieurs milliers de jetons. Un faux qui n'offre que
    # `create` ne mesure pas le chemin réel : il tombe sur une panne de montage.
    class _Flux:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        @staticmethod
        def get_final_message():
            return create()

    class _Anthropic:
        def __init__(self, *a, **k):
            self.messages = types.SimpleNamespace(
                create=create, stream=lambda **kw: _Flux())
    m = types.ModuleType("anthropic")
    m.Anthropic = _Anthropic
    for nom in ("NotFoundError", "AuthenticationError", "RateLimitError",
                "APIConnectionError", "APIStatusError"):
        setattr(m, nom, type(nom, (Exception,), {}))

    res = A.atelier(fiche=FICHE, documents=DOCS, client_extraction=RIEN,
                    client_redaction=m)
    assert res["echecs"], "l'échec de rédaction n'est pas signalé"
    assert res["brouillons"], "une pièce tombée a emporté toute la rédaction"


# ═══════════════════════════════════════════════════════════════════════════
#  L'ÉVENTAIL
# ═══════════════════════════════════════════════════════════════════════════

def test_l_eventail_rend_le_MEME_dossier_que_la_sequence():
    a = A.atelier(fiche=FICHE, documents=DOCS, client_extraction=_progressif(3),
                  rediger=False)
    b = A.atelier(fiche=FICHE, documents=DOCS, client_extraction=_progressif(3),
                  rediger=False, executeur=A.executeur_parallele(4))
    assert a["remplies"] == b["remplies"]
    assert set(a["extraits"]) == set(b["extraits"])


def test_l_executeur_parallele_lance_VRAIMENT_en_meme_temps():
    """Une règle qui vérifierait la PRÉSENCE d'un pool serait verte sur un pool
    d'une seule place. On compte les travaux réellement simultanés."""
    ensemble = {"max": 0, "n": 0}
    verrou = threading.Lock()

    def lent(_x):
        with verrou:
            ensemble["n"] += 1
            ensemble["max"] = max(ensemble["max"], ensemble["n"])
        time.sleep(0.05)
        with verrou:
            ensemble["n"] -= 1
        return _x

    A.executeur_parallele(4)(lent, list(range(8)))
    assert ensemble["max"] > 1, "les travaux se sont enchaînés un par un"


# ═══════════════════════════════════════════════════════════════════════════
#  CE QU'AUCUN ALGORITHME NE PRODUIRA
# ═══════════════════════════════════════════════════════════════════════════

def test_ce_qui_ne_s_automatisera_pas_est_reclame_des_le_PREMIER_tour():
    res = A.atelier(fiche=FICHE, documents=DOCS, client_extraction=RIEN,
                    rediger=False)
    assert res["reclamations"], "rien n'est réclamé : les attestations sortiront la veille"
    noms = " ".join(x["nom"] for x in res["reclamations"]).lower()
    assert "assurance" in noms
    assert "pouvoir" in noms


def test_les_pieces_BLOQUANTES_sont_reclamees_EN_PREMIER():
    """C'est l'ordre dans lequel il faut s'en occuper, pas l'ordre du catalogue."""
    r = D.remplir(fiche=FICHE, analyse=D.analyser(DOCS))
    rec = A.a_reclamer(r)
    bloquantes = [i for i, x in enumerate(rec) if x["bloquant"]]
    libres = [i for i, x in enumerate(rec) if not x["bloquant"]]
    assert bloquantes, "le montage n'a aucune pièce bloquante à obtenir"
    assert max(bloquantes) < min(libres or [999])


def test_on_ne_reclame_QUE_ce_qui_vient_d_un_TIERS():
    """Réclamer une pièce que l'outil sait produire ferait faire à la main un
    travail déjà fait."""
    r = D.remplir(fiche=FICHE, analyse=D.analyser(DOCS))
    cles = {x["cle"] for x in A.a_reclamer(r)}
    for p in r["pieces"]:
        if p["cle"] in cles:
            assert p.get("voie") == "obtenir", \
                "%s est réclamée alors que sa voie est « %s »" % (p["cle"], p.get("voie"))


# ═══════════════════════════════════════════════════════════════════════════
#  LE SECOND SOCLE — les mots de l'acheteur dans la consigne
# ═══════════════════════════════════════════════════════════════════════════

def _piece_et_corpus(cle="moyens"):
    an = D.analyser(DOCS)
    r = D.remplir(fiche=FICHE, analyse=an)
    piece = next(p for p in R.pieces_redigeables(r) if p["cle"] == cle)
    return r, an, piece, X.corpus(DOCS, an)


def test_le_second_socle_met_les_mots_de_l_ACHETEUR_dans_le_brief():
    r, an, piece, corp = _piece_et_corpus()
    d = R.chercher_dossier(piece, corp)
    assert not d["absent"], "aucun passage retenu : %s" % d["absent"]
    assert "metrologie" in d["bloc"], "le passage exigeant les moyens est absent"
    b = R.brief(R.contexte(r, an, piece, socle=None, dossier=d))
    assert "metrologie" in b, "les mots de l'acheteur n'atteignent pas la consigne"


def test_le_brief_DIT_que_la_consultation_COMMANDE_sur_le_fonds():
    """Sans cette phrase, rien n'apprend au modèle qu'une exigence écrite par
    l'acheteur l'emporte sur une formule éprouvée ailleurs."""
    r, an, piece, corp = _piece_et_corpus()
    b = R.brief(R.contexte(r, an, piece, socle=None,
                           dossier=R.chercher_dossier(piece, corp)))
    assert "COMMANDENT" in b


def test_sans_dossier_joint_le_brief_le_DIT_au_lieu_de_se_taire():
    r, an, piece, _corp = _piece_et_corpus()
    b = R.brief(R.contexte(r, an, piece, socle=None, dossier=None))
    assert "Aucun passage de la consultation" in b
    assert "dossier_non_joint" in b


def test_le_socle_du_DOSSIER_ne_remplace_PAS_celui_du_FONDS():
    """Deux sources, DEUX BLOCS, deux absences nommées séparément.

    LA PREMIÈRE VERSION DE CETTE RÈGLE ÉTAIT VERTE POUR RIEN : elle passait
    `socle=None`, donc la fusion qu'elle prétendait interdire n'était jamais
    exercée — la batterie l'a montré, M16 survivait. On donne maintenant DEUX
    socles réels, chacun avec un contenu reconnaissable, et on exige que chaque
    champ porte le sien."""
    r, an, piece, corp = _piece_et_corpus()
    fonds = {"bloc": "EXTRAIT-DU-FONDS-CCTP", "sources": [{"titre": "CCTP-2024"}],
             "absent": ""}
    dossier = R.chercher_dossier(piece, corp)
    assert not dossier["absent"]
    ctx = R.contexte(r, an, piece, socle=fonds, dossier=dossier)

    assert ctx["socle_documentaire"] == "EXTRAIT-DU-FONDS-CCTP"
    assert "EXTRAIT-DU-FONDS-CCTP" not in ctx["dossier_extraits"], \
        "le bloc du fonds a fui dans celui du dossier : les deux sont fondus"
    assert "metrologie" in ctx["dossier_extraits"]
    assert "metrologie" not in ctx["socle_documentaire"]

    # Et les absences restent distinctes : un fonds présent ne doit pas
    # masquer un dossier absent, ni l'inverse.
    seul_fonds = R.contexte(r, an, piece, socle=fonds, dossier=None)
    assert not seul_fonds["socle_absent"]
    assert seul_fonds["dossier_absent"] == "dossier_non_joint"
    seul_dossier = R.contexte(r, an, piece, socle=None, dossier=dossier)
    assert seul_dossier["socle_absent"] == "socle_non_joint"
    assert not seul_dossier["dossier_absent"]
