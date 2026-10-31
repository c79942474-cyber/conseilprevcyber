"""L'ACCOMPAGNEMENT DE /securite-ia — cadrage, progression, encadrés,
info-bulles, aide à la décision.

CE QUI L'A FAIT NAÎTRE. La page tenait ses instruments mais laissait le
client seul devant eux, et sa restitution EBIOS rendait des « vraisemblances
sans risques » : la route savait recevoir la gravité, la page ne la demandait
jamais.

CE QUI EST MESURÉ ICI :
  · chaque phase a son ancre dans la page, ses textes et SES sources, et
    chaque source renvoie à une table existante ;
  · la page ne recopie aucun texte d'accompagnement ni aucune définition ;
  · la grille est monotone, et la décision d'ensemble est commandée par le
    pire maillon — jamais par une proportion ;
  · sans gravité, aucun niveau n'est inventé ;
  · la page envoie le cadrage au calcul ET à l'export, et la barre n'avance
    que sur constat.

CE QUE CE FICHIER NE MESURE PAS : l'écran peint, les clics, la barre qui
avance — `outils/recette_securite_ia_accompagnement.js` le fait dans un vrai
navigateur.
"""
import io
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import accompagnement_securite_ia as A  # noqa: E402
import chaine_autonomie as CA  # noqa: E402

ORIGINE = {"Origin": "http://localhost"}


def _lire(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


PAGE = _lire("securite-ia.html")
JS = _lire("securite-ia-accompagnement.js")


def _sys(nom, aut, mai):
    return {"nom": nom, "autonomie": aut, "maitrise": mai}


# ── LE MODULE ────────────────────────────────────────────────────────────

def test_chaque_phase_a_son_ANCRE_dans_la_page_et_ses_SOURCES():
    for p in A.PHASES:
        assert 'id="%s"' % p["ancre"] in PAGE, "la phase %s n'a pas de section" % p["cle"]
        assert p["sources"], p["cle"]
        for c in p["sources"]:
            assert A._source(c), "phase %s : source « %s » introuvable" % (p["cle"], c)
    assert len({p["ancre"] for p in A.PHASES}) == len(A.PHASES)


def test_chaque_terme_a_sa_source_et_chaque_bulle_de_la_page_son_terme():
    cles = {t["cle"] for t in A.GLOSSAIRE}
    for t in A.GLOSSAIRE:
        assert A._source(t["source"]), t["cle"]
    appeles = set(re.findall(r'data-terme="(\w+)"', PAGE + JS))
    appeles |= set(re.findall(r'bulle\("(\w+)"\)', PAGE))
    assert appeles, "aucune info-bulle dans la page"
    assert appeles <= cles, "info-bulles sans définition : %s" % sorted(appeles - cles)


def test_la_page_ne_RECOPIE_aucun_texte_d_accompagnement():
    """Un texte écrit dans le gabarit divergerait du module au premier
    remaniement : l'encadré dirait une chose, la route une autre."""
    fuites = []
    for p in A.PHASES:
        for champ in ("objectif", "comment_lire", "piege", "decision"):
            if p[champ][:50] in PAGE or p[champ][:50] in JS:
                fuites.append("%s.%s" % (p["cle"], champ))
    for t in A.GLOSSAIRE:
        if t["definition"][:45] in PAGE or t["definition"][:45] in JS:
            fuites.append("glossaire.%s" % t["cle"])
    for g in A.GRAVITES:
        if g["dit"][:40] in PAGE or g["dit"][:40] in JS:
            fuites.append("gravité %d" % g["niveau"])
    assert not fuites, "recopiés au lieu d'être servis : %s" % fuites


def test_la_grille_est_MONOTONE_dans_les_deux_sens():
    for g in (1, 2, 3, 4):
        for e in (1, 2, 3):
            assert A.niveau(e, g)["rang"] <= A.niveau(e + 1, g)["rang"], (g, e)
    for e in (1, 2, 3, 4):
        for g in (1, 2, 3):
            assert A.niveau(e, g)["rang"] <= A.niveau(e, g + 1)["rang"], (g, e)
    assert A.niveau(4, 4)["cle"] == "inacceptable"
    assert A.niveau(1, 1)["cle"] == "acceptable"


def test_une_gravite_CRITIQUE_ne_tolere_pas_deux_degres_d_ecart():
    """CE QUE LE MODULE ANNONCE, ET QUE LA SEULE MONOTONIE NE TIENT PAS : une
    grille plus indulgente resterait monotone. À gravité critique, deux
    degrés d'écart suffisent pour « inacceptable » ; à gravité mineure,
    deux degrés restent acceptables."""
    assert [A.niveau(e, 4)["cle"] for e in (1, 2, 3, 4)] == [
        "tolerable", "inacceptable", "inacceptable", "inacceptable"]
    assert [A.niveau(e, 1)["cle"] for e in (1, 2)] == ["acceptable", "acceptable"]


def test_sans_gravite_AUCUN_niveau_n_est_invente():
    d = A.aide_a_la_decision([_sys("Agent", {"action": 4}, {"action": 0})])
    assert d["ok"] and d["gravite"] is None
    assert d["lignes"][0]["niveau"] is None and d["lignes"][0]["decision"] is None
    assert "gravité" in d["ensemble"]
    assert A.niveau(2, None) is None and A.niveau(2, 7) is None


def test_le_PIRE_maillon_commande_la_decision_jamais_la_proportion():
    """Un maillon inacceptable parmi dix acceptables : la décision reste
    « ne pas étendre ». Une proportion dirait que tout va plutôt bien."""
    parc = [_sys("S%d" % i, {"perception": 1}, {"perception": 0}) for i in range(10)]
    parc.append(_sys("Agent", {"action": 4}, {"action": 0}))
    d = A.aide_a_la_decision(parc, gravite=2)
    assert d["compte"]["inacceptable"] == 1 and d["compte"]["acceptable"] == 10
    assert d["ensemble"].startswith("Ne pas étendre")
    assert d["lignes"][0]["systeme"] == "Agent", "le pire doit venir en tête"


def test_les_deux_LEVIERS_nomment_les_bons_degres():
    d = A.aide_a_la_decision([_sys("A", {"action": 3}, {"action": 1})], gravite=3)
    dits = [r["dit"] for r in d["lignes"][0]["refermer"]]
    aut = {x["degre"]: x["nom"] for x in CA.AUTONOMIE}
    mai = {x["degre"]: x["nom"] for x in CA.MAITRISE}
    assert dits[0] == "Ramener l'autonomie de « %s » à « %s »." % (aut[3], aut[1])
    assert dits[1] == "Faire passer la maîtrise de « %s » à « %s »." % (mai[1], mai[3])


def test_la_decision_dit_qu_elle_doit_etre_VALIDEE_et_ce_que_NIS2_change():
    d = A.aide_a_la_decision([_sys("A", {"action": 2}, {"action": 1})], gravite=1,
                             statut_nis2="importante")
    assert "validée par la direction" in d["validation"]
    assert d["nis2"] and "Entité importante" in d["nis2"]
    assert A.aide_a_la_decision([_sys("A", {"action": 2}, {"action": 1})],
                                gravite=1, statut_nis2="hors")["nis2"] is None


# ── LES ROUTES ───────────────────────────────────────────────────────────

def test_la_route_sert_TOUT_ce_que_la_page_dresse(anonyme):
    j = anonyme.get("/api/securite-ia/accompagnement").get_json()
    assert j and j["ok"]
    a = j["accompagnement"]
    assert [p["cle"] for p in a["phases"]] == [p["cle"] for p in A.PHASES]
    assert all(p["sources"] and all(s["titre"] for s in p["sources"]) for p in a["phases"])
    assert len(a["glossaire"]) == len(A.GLOSSAIRE) and len(a["gravites"]) == 4
    assert a["secteurs"] and a["statuts_nis2"] and a["validation"]


def test_l_evaluation_rend_l_aide_a_la_decision_avec_la_GRAVITE(anonyme):
    r = anonyme.post("/api/securite-ia/evaluer", headers=ORIGINE, json={
        "systemes": [_sys("Agent", {"action": 4}, {"action": 0})],
        "valeur_metier": "Continuité", "gravite": 3, "statut_nis2": "essentielle"})
    j = r.get_json()
    assert r.status_code == 200 and j["gravite"] == 3 and not j["manque"]
    assert j["decision"]["lignes"][0]["niveau"] == "inacceptable"
    assert j["decision"]["nis2"]


# ── LA PAGE ──────────────────────────────────────────────────────────────

def test_la_page_ENVOIE_le_cadrage_au_calcul_et_a_l_export():
    """LE DÉFAUT QUI A OUVERT CE CHANTIER : la gravité n'était jamais
    envoyée, et la restitution restait sans risques."""
    assert PAGE.count("gravite: cad.gravite || null") == 2, (
        "le calcul et l'export doivent tous deux porter la gravité")
    assert "valeur_metier: cad.valeur_metier" in PAGE
    assert "statut_nis2: cad.statut_nis2" in PAGE
    assert '<script src="/securite-ia-accompagnement.js" defer></script>' in PAGE
    for champ in ("sia-secteur", "sia-nis2", "sia-valeur", "sia-gravite", "sia-perimetre"):
        assert 'id="%s"' % champ in PAGE, champ


def test_la_barre_n_avance_que_sur_CONSTAT():
    """Aucune case à cocher : chaque étape passe à « faite » parce que la
    page constate ce qui la clôt."""
    i = PAGE.index('id="sia-prog"')
    barre = PAGE[i:PAGE.index("</nav>", i)]
    assert 'type="checkbox"' not in barre and 'role="progressbar"' in barre
    for attendu in ('marquer("parc", d.declares > 0)', 'marquer("chaine", d.cotes > 0)',
                    'marquer("ebios", !!(j && j.decision && j.decision.ok && j.decision.gravite))',
                    "FAIT.cadrage = !!(c.valeur_metier && c.gravite)"):
        assert attendu in JS, attendu
    assert 'annoncer("sia:parc"' in PAGE and 'annoncer("sia:evalue", j)' in PAGE


def test_la_route_et_le_script_sont_SERVIS(anonyme):
    r = anonyme.get("/securite-ia-accompagnement.js")
    assert r.status_code == 200 and "javascript" in r.headers["Content-Type"]
