"""LE BANDEAU DE CHIFFRES — CE QUI L'EMPÊCHE DE VIEILLIR EN SILENCE.

LE DÉFAUT PROPRE AUX BANDEAUX DE CHIFFRES, et il ne se voit jamais. « 88 % »
reste parfaitement lisible et parfaitement convaincant trois ans après
l'enquête qui l'a produit : rien dans sa typographie ne dit qu'il a vieilli.
Un lien mort se voit ; un pourcentage périmé se cite.

LA DÉMONSTRATION EST DANS LE MODULE LUI-MÊME. Le chiffre transmis pour ce
bandeau annonçait 9 400 serveurs au registre public MCP. Le comptage du
registre en a trouvé plus du triple le même jour. C'est le seul des six qui se
recompte — et c'est justement celui qui avait le plus dérivé.

CE QUE CES RÈGLES ÉPROUVENT :
  1. aucun chiffre ne circule sans source ni date ;
  2. un chiffre dont la référence n'est pas établie le DÉCLARE, au lieu de se
     taire — une incertitude qui ne se voit nulle part se lit comme une
     certitude ;
  3. l'âge se compte depuis la MESURE, jamais depuis la dernière relecture :
     sinon il suffirait de rouvrir un rapport pour le rajeunir ;
  4. un chiffre passé sa péremption change d'état, et la péremption dépend de
     la NATURE du chiffre — un décompte de registre et une enquête annuelle
     ne vieillissent pas au même rythme ;
  5. le décompte du registre n'est jamais inventé : absent, il se dit absent ;
  6. la page ne recopie AUCUNE valeur ;
  7. et le bandeau est en tête, avant l'instrument qu'il justifie.
"""
import gzip
import io
import json
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import chiffres_securite_ia as ch  # noqa: E402

JOUR = "2026-09-19"


def _lire(nom):
    with io.open(os.path.join(ICI, nom), encoding="utf-8") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════════════════
#  1. AUCUN CHIFFRE SANS SOURCE, NI SANS DATE
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cle", [c["cle"] for c in ch.CHIFFRES])
def test_chaque_chiffre_NOMME_sa_source(cle):
    c = ch.CHIFFRES_PAR_CLE[cle]
    assert str(c.get("source") or "").strip(), (
        "le chiffre « %s » circule sans source : il sera repris tel quel, et "
        "c'est la page entière qui répondra de lui" % cle)
    assert str(c.get("dit") or "").strip(), (
        "le chiffre « %s » ne dit pas ce qu'il mesure" % cle)


def test_un_chiffre_fige_porte_la_DATE_de_ce_qu_il_mesure():
    """SEUL LE DÉCOMPTE DU REGISTRE FAIT EXCEPTION, et pour une raison : sa
    date lui vient du comptage, pas de la table."""
    sans = [c["cle"] for c in ch.CHIFFRES
            if c["cle"] != "mcp" and ch._jour(c.get("mesure_le")) is None]
    assert not sans, "chiffre(s) sans date de mesure : %s" % sans
    assert ch.CHIFFRES_PAR_CLE["mcp"]["mesure_le"] is None, (
        "le décompte du registre porte une date écrite à la main : elle "
        "survivrait au comptage suivant")


def test_une_reference_NON_ETABLIE_se_declare():
    """UNE INCERTITUDE QUI NE SE VOIT NULLE PART SE LIT COMME UNE CERTITUDE.

    Un chiffre sans lien vérifiable et sans réserve déclarée arrive au comité
    avec l'autorité des autres — et c'est là qu'on découvre qu'on ne sait pas
    d'où il sort.
    """
    muets = [c["cle"] for c in ch.CHIFFRES
             if c["cle"] != "mcp" and not c.get("lien")
             and not str(c.get("a_confirmer") or "").strip()]
    assert not muets, (
        "chiffre(s) sans lien ET sans réserve déclarée : %s" % muets)


def test_le_bandeau_COMPTE_les_sources_a_confirmer_au_lieu_de_les_taire():
    b = ch.bandeau(aujourdhui=JOUR)
    attendu = sorted(c["cle"] for c in ch.CHIFFRES if c.get("a_confirmer"))
    assert sorted(b["sources_a_confirmer"]) == attendu, (
        "le bandeau ne rend pas la liste réelle des sources à confirmer")
    assert str(len(attendu)) in b["reserve"] or not attendu, (
        "la réserve ne dit pas COMBIEN de sources attendent leur référence")


# ══════════════════════════════════════════════════════════════════════════
#  2. L'ÂGE, ET LA PÉREMPTION
# ══════════════════════════════════════════════════════════════════════════

def test_l_age_se_compte_depuis_la_MESURE_et_non_depuis_la_relecture():
    """SINON IL SUFFIRAIT DE ROUVRIR UN RAPPORT POUR LE RAJEUNIR.

    Relire une enquête de 2024 aujourd'hui met à jour ce qu'on sait d'elle,
    pas ce qu'elle mesure. Un âge compté depuis la vérification rendrait tout
    éternellement frais, ce qui est la façon la plus sûre de n'alerter jamais.
    """
    c = dict(ch.CHIFFRES_PAR_CLE["incidents"])
    mesure = ch.fraicheur(c, JOUR)["age_jours"]
    # LA RELECTURE AVANCE, LA MESURE NE BOUGE PAS : l'âge ne doit pas bouger.
    c["verifie_le"] = "2026-09-19"
    assert ch.fraicheur(c, JOUR)["age_jours"] == mesure
    # LA MESURE RECULE D'UN AN : l'âge prend un an.
    c["mesure_le"] = "2024-12-31"
    assert ch.fraicheur(c, JOUR)["age_jours"] == mesure + 365


@pytest.mark.parametrize("nature,dedans,dehors", [
    ("registre", 10, 90),
    ("enquete", 300, 900),
    ("prevision", 400, 1300),
])
def test_la_peremption_depend_de_la_NATURE_du_chiffre(nature, dedans, dehors):
    """UN SEUIL UNIQUE AURAIT FAIT CLIGNOTER EN PERMANENCE UNE ENQUÊTE VALIDE.

    Et un signal qui s'allume toujours est un signal qu'on apprend à ignorer —
    ce qui coûte plus cher que de ne pas l'avoir mis.
    """
    import datetime
    base = datetime.date(2026, 9, 19)
    faux = {"cle": "essai", "nature": nature}
    faux["mesure_le"] = (base - datetime.timedelta(days=dedans)).isoformat()
    assert ch.fraicheur(faux, base)["etat"] == "frais", (nature, dedans)
    faux["mesure_le"] = (base - datetime.timedelta(days=dehors)).isoformat()
    assert ch.fraicheur(faux, base)["etat"] == "perime", (nature, dehors)


def test_les_trois_seuils_sont_REELLEMENT_differents():
    """SANS CELA, LA RÈGLE D'AU-DESSUS PASSERAIT SUR TROIS SEUILS ÉGAUX."""
    assert len(set(ch.PEREMPTION.values())) == len(ch.PEREMPTION), (
        "deux natures partagent le même seuil : la distinction ne sert à rien")
    assert ch.PEREMPTION["registre"] < ch.PEREMPTION["enquete"], (
        "un décompte de registre vieillit plus vite qu'une enquête annuelle")


def test_un_chiffre_qui_vieillit_CHANGE_d_etat_sur_la_page():
    """LE POINT QUI DÉCIDE DE TOUT : le bandeau doit se dénoncer lui-même."""
    frais = ch.bandeau(aujourdhui="2026-09-19")
    vieux = ch.bandeau(aujourdhui="2028-09-19")
    assert frais["a_revoir"] == [], frais["a_revoir"]
    assert vieux["a_revoir"], (
        "deux ans plus tard, aucun chiffre ne se signale : le bandeau "
        "vieillit sans le dire")
    assert len(vieux["a_revoir"]) >= 5


# ══════════════════════════════════════════════════════════════════════════
#  3. LE DÉCOMPTE DU REGISTRE N'EST JAMAIS INVENTÉ
# ══════════════════════════════════════════════════════════════════════════

def test_le_decompte_du_registre_ABSENT_se_dit_absent():
    """AFFICHER « 0 » AURAIT INVENTÉ LE CHIFFRE, dans le sens rassurant, sur
    la page d'un cabinet qui explique qu'il faut inventorier ces serveurs."""
    garde = ch.etat_mcp()
    try:
        with ch._VERROU:
            ch._ETAT_MCP.update({"valeur": None, "le": None, "motif": None})
        liste = ch.chiffres(aujourdhui=JOUR)
        mcp = [c for c in liste if c["cle"] == "mcp"][0]
        assert mcp["valeur"] is None and mcp["affiche"] is None
        assert mcp["servi"] is False, (
            "un décompte absent est servi comme s'il existait")
        assert ch.bandeau(aujourdhui=JOUR)["servis"] == len(ch.CHIFFRES) - 1
    finally:
        ch.poser_mcp(garde["valeur"], garde["le"])


def test_un_registre_INJOIGNABLE_ne_remplace_pas_le_compte_precedent():
    """ÉCRASER UN CHIFFRE DATÉ PAR UN ÉCHEC L'AURAIT FAIT DISPARAÎTRE.

    Le garder avec SA date le fait simplement vieillir — ce qui est
    exactement ce qui s'est passé.
    """
    garde = ch.etat_mcp()
    try:
        ch.poser_mcp(33089, "2026-09-19")

        def tombe(_u):
            raise OSError("registre injoignable")

        r = ch.rafraichir_mcp(aujourdhui="2026-10-01", ouvrir=tombe)
        assert r["ok"] is False and r["motif"] == "registre_injoignable"
        e = ch.etat_mcp()
        assert e["valeur"] == 33089, "le compte précédent a été effacé"
        assert e["le"] == "2026-09-19", (
            "le compte précédent a été redaté : il paraîtrait frais alors que "
            "personne n'a pu le recompter")
        assert e["motif"] == "registre_injoignable"
    finally:
        ch.poser_mcp(garde["valeur"], garde["le"])


def test_le_comptage_DEDOUBLONNE_et_ne_retient_que_les_actifs():
    """TROIS COMPTES SORTENT DU MÊME REGISTRE, et ils diffèrent de dizaines de
    milliers : les entrées (une par version), les noms distincts, et les noms
    distincts encore actifs. Annoncer « des serveurs » sans dire lequel des
    trois on compte, c'est publier un nombre que personne ne peut reproduire.
    """
    pages = [
        {"servers": [
            {"server": {"name": "a/x"}, "_meta": {"io.modelcontextprotocol.registry/official": {"status": "active"}}},
            {"server": {"name": "a/x"}, "_meta": {"io.modelcontextprotocol.registry/official": {"status": "active"}}},
            {"server": {"name": "b/y"}, "_meta": {"io.modelcontextprotocol.registry/official": {"status": "deleted"}}},
        ], "metadata": {"nextCursor": "p2"}},
        {"servers": [
            {"server": {"name": "c/z"}, "_meta": {"io.modelcontextprotocol.registry/official": {"status": "active"}}},
        ], "metadata": {}},
    ]
    vues = {"n": 0}

    class Faux:
        def __init__(self, d): self.d = d
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps(self.d).encode("utf-8")

    def ouvrir(_u):
        d = pages[min(vues["n"], len(pages) - 1)]
        vues["n"] += 1
        return Faux(d)

    r = ch.compter_mcp(ouvrir=ouvrir)
    assert r["ok"] and r["valeur"] == 2, (
        "attendu 2 noms distincts actifs (a/x dédoublonné, b/y inactif, "
        "c/z actif) ; obtenu %r" % r)


def test_le_separateur_de_milliers_est_pose():
    assert ch._milliers(33089) == "33 089"
    assert ch._milliers(940) == "940"


# ══════════════════════════════════════════════════════════════════════════
#  4. LA PAGE
# ══════════════════════════════════════════════════════════════════════════

def test_aucune_VALEUR_n_est_ecrite_dans_la_page():
    """UN POURCENTAGE RECOPIÉ SURVIT À L'ENQUÊTE QUI L'A PRODUIT.

    Et il y survit en silence, y compris posé dans un commentaire : la règle
    ne ménage donc aucune exception, et les commentaires du fichier ont été
    écrits pour n'en avoir pas besoin.
    """
    page = _lire("securite-ia.html")
    fautes = [c["affiche"] for c in ch.CHIFFRES
              if c.get("affiche") and c["affiche"] in page]
    assert not fautes, (
        "valeur(s) recopiée(s) dans la page : %s" % fautes)
    # ET LA RÉCIPROQUE : sans appel, la règle ci-dessus serait vraie d'une
    # page qui n'affiche aucun chiffre.
    # L'APPEL, ET NON LE CHEMIN. Le commentaire en tête du script cite la
    # route pour dire d'où viennent les valeurs : une règle qui cherche le
    # chemin restait verte sur une page dont le `fetch` visait ailleurs.
    assert 'fetch("/api/securite-ia/chiffres"' in page, (
        "la page n'appelle pas la route des chiffres")


def test_aucun_LIBELLE_de_chiffre_n_est_ecrit_dans_la_page():
    page = _lire("securite-ia.html")
    fautes = [c["cle"] for c in ch.CHIFFRES if c["dit"][:40] in page]
    assert not fautes, "libellé(s) recopié(s) : %s" % fautes


def test_le_bandeau_est_EN_TETE_avant_l_instrument():
    """DES CHIFFRES PLACÉS APRÈS L'INSTRUMENT SERVENT DE CONCLUSION À QUI EST
    ALLÉ JUSQU'AU BOUT — c'est-à-dire à personne, puisque c'est précisément ce
    qu'ils doivent donner envie de faire."""
    page = _lire("securite-ia.html")
    assert page.index('id="chiffres"') < page.index('id="parc"'), (
        "le bandeau de chiffres est placé après l'instrument")


def test_la_route_est_ouverte_et_sert_les_six_chiffres():
    import acces
    assert "/api/securite-ia/chiffres" in acces.API_OUVERTES

    import app as application
    entetes = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept-Language": "fr-FR,fr;q=0.9", "Accept-Encoding": "gzip, deflate"}
    c = application.app.test_client()
    # LA DATE DEMANDÉE N'EST PAS CELLE DU JOUR, ET C'EST TOUT L'OBJET.
    # Demander la date du jour rendait cette règle verte quoi qu'il arrive :
    # une route qui IGNORE le paramètre et lit l'horloge rend exactement la
    # même valeur. La règle passait alors pour une raison sans rapport avec
    # ce qu'elle prétend éprouver — jusqu'au lendemain, où elle serait tombée
    # sans qu'on comprenne pourquoi.
    AILLEURS = "2025-03-04"
    r = c.get("/api/securite-ia/chiffres?date=" + AILLEURS, headers=entetes)
    assert r.status_code == 200
    brut = (gzip.decompress(r.data)
            if r.headers.get("Content-Encoding") == "gzip" else r.data)
    d = json.loads(brut)
    assert len(d["chiffres"]) == len(ch.CHIFFRES)
    assert d["aujourdhui"] == AILLEURS, (
        "la route ignore la date reçue et lit son horloge : deux lecteurs "
        "sous deux fuseaux liraient deux âges pour le même chiffre")
    for x in d["chiffres"]:
        assert x["source"], x["cle"]
        assert "fraicheur" in x and "etat" in x["fraicheur"], x["cle"]


def test_la_route_n_est_PAS_figee_au_demarrage():
    """`_json_fige` NE RAPPELLE JAMAIS SON CONSTRUCTEUR.

    Mémoïsée, cette route aurait servi pour toujours le décompte du premier
    jour, et le fil qui recompte le registre n'aurait rien changé à l'écran.
    """
    src = _lire("app.py")
    d = src.index("def api_securite_ia_chiffres")
    corps = src[d:src.index("\n@app.route", d)]
    # ON LIT LE CODE, PAS LA DOCSTRING. Celle de la route explique justement
    # pourquoi elle n'est PAS mémoïsée : une règle qui ne fait pas la
    # différence interdirait d'écrire l'explication, et la prochaine personne
    # la retirerait sans savoir ce qu'elle protégeait.
    corps = re.sub(r'"""!?.*?"""', " ", corps, flags=re.S)
    assert "_json_fige(" not in corps, (
        "la route des chiffres est mémoïsée : le décompte n'évoluerait plus")
