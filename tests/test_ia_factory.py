"""L'étude de faisabilité IA Factory : un chiffrage sans prix inventé, des
sources obtenues et comptées comme telles, un planning qui sépare ce qui glisse
de ce qui ne glisse pas — et une page fermée par construction.

CE QUE CES RÈGLES GARDENT, ET POURQUOI CE SONT DES PROPRIÉTÉS.

  — AUCUN PRIX NE VIT DANS LE MODULE. Un chiffrage sur des entrées vides ne
    chiffre RIEN : chaque poste ressort non chiffré, avec la liste de ce qui
    manque, et le total est None. Un zéro muet ferait croire que le poste
    n'est pas dû.
  — CHAQUE FORMULE NOMME CE QU'ELLE CONSOMME. Le texte de la formule et le
    calcul sont deux exemplaires ; la règle exige que chaque clé consommée
    figure dans le texte, sinon c'est le texte qu'on lirait et le calcul qui
    s'appliquerait.
  — CHAQUE SOURCE DIT QU'ELLE N'A PAS ÉTÉ LUE. Le proxy refusait les sites :
    les chiffres viennent d'extraits de recherche. Une source qui prétendrait
    « lue » ferait plus de mal qu'une absence de source.
  — LES JALONS RÉGLEMENTAIRES NE SONT PAS DES PHASES. Ils portent une nature
    distincte et une date fixe ; les phases portent une incertitude déclarée.
  — LA PAGE EST FERMÉE SANS QU'ON AIT EU À LA FERMER. C'est la liste blanche
    qui le garantit ; la règle vérifie que la garantie tient.
"""
import io
import json
import os
import re
import sys
from datetime import date

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import acces                                                       # noqa: E402
import ia_factory as F                                             # noqa: E402
import perimetre                                                   # noqa: E402

URL = "/ingenierie-ia-factory"


def _src(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


# ═══════════════════════════════════════════════════════════════════════════
#  1. AUCUN PRIX INVENTÉ
# ═══════════════════════════════════════════════════════════════════════════

def test_un_chiffrage_sans_entrees_ne_chiffre_rien():
    c = F.chiffrer({}, {})
    assert c["n_non_chiffres"] == c["n_postes"] == len(F.POSTES)
    assert c["sous_total"] == 0.0 and c["total"] is None, (
        "sans prix, il ne peut y avoir de total : %r" % c["total"])
    assert all(l["statut"] == "non_chiffre" and l["manque"] for l in c["lignes"]), (
        "chaque poste non chiffré doit dire CE QUI manque")
    assert any("sous-total" in a for a in c["alertes"])


def test_chaque_poste_consomme_au_moins_un_prix_du_client():
    """Un poste qui se chiffrerait sans prix unitaire porterait un prix caché."""
    for p in F.POSTES:
        assert any(k in F.PRIX for k in p["besoin"]), (
            "le poste %s se chiffre sans aucun prix du client : %s" % (p["cle"], p["besoin"]))


def test_chaque_formule_nomme_ce_qu_elle_consomme():
    for p in F.POSTES:
        for k in p["besoin"]:
            assert k in p["formule"] or k == "duree_mois" and "années" in p["formule"], (
                "le poste %s consomme %s sans le nommer dans sa formule « %s »"
                % (p["cle"], k, p["formule"]))


def test_chaque_cle_consommee_existe_et_a_une_provenance():
    """Une entrée qu'on ne sait pas où chercher est une entrée qui sera inventée."""
    for p in F.POSTES:
        for k in p["besoin"]:
            assert k in F.QUANTITES or k in F.PRIX, (p["cle"], k)
    for d in (F.QUANTITES, F.PRIX):
        for k, v in d.items():
            assert v.get("ou", "").strip(), "%s ne dit pas où le client trouve la valeur" % k


def test_un_chiffrage_complet_additionne_et_ne_perd_rien():
    Q = dict(effectif=1000, n_metiers=4, n_cas_usage=10, n_cas_haut_risque=2, etp_par_cas=1,
             n_si_source=1, n_interfaces=20, part_formes=0.5, heures_formation=4, duree_mois=24,
             tokens_mois=100, jours_cadrage=50, jours_pmo_mois=10, jours_par_cas=60,
             jours_recette_interface=3)
    P = dict(tjm_conseil=1000, tjm_interne=500, cout_etp_ia=100000, cout_etp_plateforme=90000,
             cout_infra_an=1e6, cout_outillage_an=2e5, cout_securite_an=1e5, prix_M_jetons=1.0,
             cout_heure_formation=40, cout_interface=10000, cout_audit_cas=50000)
    c = F.chiffrer(Q, P, 0.1)
    assert c["n_non_chiffres"] == 0 and c["part_non_chiffree"] == 0.0
    somme = sum(l["montant"] for l in c["lignes"])
    assert abs(somme - c["sous_total"]) < 0.01
    assert abs(c["total"] - (c["sous_total"] + c["provision"])) < 0.01
    assert abs(sum(g["chiffre"] for g in c["par_groupe"].values()) - c["sous_total"]) < 0.01


def test_les_interfaces_sont_comptees_deux_fois_pendant_une_migration():
    """LE POSTE QUE LE NEUF NE CONNAÎT PAS. Pendant une migration de cœur, chaque
    interface existe vers l'ancien socle ET vers le nouveau."""
    Q = dict(n_interfaces=10, duree_mois=12)
    P = dict(cout_interface=1000)
    un = [l for l in F.chiffrer(dict(Q, n_si_source=1), P)["lignes"] if l["cle"] == "interfaces"][0]
    deux = [l for l in F.chiffrer(dict(Q, n_si_source=2), P)["lignes"] if l["cle"] == "interfaces"][0]
    assert un["montant"] == 10000 and deux["montant"] == 20000, (un, deux)


def test_la_provision_est_comparee_au_depassement_documente_et_jamais_proposee():
    Q = dict(n_interfaces=1, n_si_source=2)
    P = dict(cout_interface=100)
    dep = [a for a in F.ANCRAGES if a["cle"] == "migration_depassement"][0]["min"]
    bas = F.chiffrer(Q, P, dep - 0.1)
    haut = F.chiffrer(Q, P, dep)
    assert any("inférieure au dépassement" in a for a in bas["alertes"])
    assert not any("inférieure au dépassement" in a for a in haut["alertes"])
    # Sans migration, la comparaison n'a pas lieu d'être : l'aléa n'est pas le même.
    seul = F.chiffrer(dict(Q, n_si_source=1), P, dep - 0.1)
    assert not any("inférieure au dépassement" in a for a in seul["alertes"])
    # Et sans provision saisie, on le DIT — on n'en pose pas une.
    assert F.chiffrer(Q, P)["provision"] is None


# ═══════════════════════════════════════════════════════════════════════════
#  2. LES ANCRAGES ET LES SOURCES — obtenus, pas lus, et comptés comme tels
# ═══════════════════════════════════════════════════════════════════════════

def test_chaque_ancrage_a_une_source_declaree_une_fourchette_et_une_limite():
    for a in F.ANCRAGES:
        assert a["source"] in F.SOURCES, (a["cle"], a["source"])
        assert a["min"] <= a["max"], a["cle"]
        assert a["ne_dit_pas"].strip(), "l'ancrage %s ne dit pas ce qu'il ne dit pas" % a["cle"]


def test_aucune_source_ne_pretend_avoir_ete_lue():
    """LE PROXY REFUSAIT LES SITES. Prétendre le contraire serait la pire des
    mentions : une source « lue » qu'on n'a pas ouverte."""
    assert all(s.get("lu") is False for s in F.SOURCES.values())
    c = F.couverture_sources()
    assert c["lues"] == 0 and "ouverte" in c["limite"]


def test_chaque_source_a_une_adresse_ou_une_reserve_ecrite():
    for cle, s in F.SOURCES.items():
        assert s.get("url") or s.get("reserve", "").strip(), (
            "la source %s n'a ni adresse ni réserve : c'est une intention, pas une source" % cle)
        assert s["nature"] in ("officiel", "presse", "analyste", "fournisseur", "juridique"), cle
    # Une adresse de fournisseur parlant de son offre porte la réserve qui convient.
    for cle, s in F.SOURCES.items():
        if s["nature"] == "fournisseur":
            assert s["reserve"].strip(), "source fournisseur %s sans réserve" % cle


def test_la_couverture_compte_par_nature_et_ne_lisse_pas():
    c = F.couverture_sources()
    assert sum(c["par_nature"].values()) == c["total"] == len(F.SOURCES)
    assert c["avec_adresse"] <= c["total"]
    sans = [k for k, s in F.SOURCES.items() if not s.get("url")]
    assert c["total"] - c["avec_adresse"] == len(sans)


# ═══════════════════════════════════════════════════════════════════════════
#  3. LE PLANNING — ce qui glisse et ce qui ne glisse pas
# ═══════════════════════════════════════════════════════════════════════════

def test_les_phases_se_suivent_sans_trou_ni_chevauchement():
    pl = F.planning({}, "2026-10-01")
    ph = pl["phases"]
    assert ph[0]["debut_tot"] == "2026-10-01"
    for a, b in zip(ph, ph[1:]):
        assert b["debut_tot"] == a["fin_tot"], (a["cle"], b["cle"])
    assert pl["fin_projet"]["tot"] == ph[-1]["fin_tot"]
    assert pl["fin_projet"]["tard"] == ph[-1]["fin_tard"]
    assert all(p["nature"] == "propre" and "±" in p["incertitude"] for p in ph), (
        "une durée d'usage doit se déclarer comme telle, avec son incertitude")


def test_les_jalons_reglementaires_sont_dates_tries_et_distincts_des_phases():
    pl = F.planning({}, "2026-09-02")
    j = pl["jalons_reglementaires"]
    dates = [x["date"] for x in j]
    assert dates == sorted(dates)
    assert all(x["nature"] == "reglementaire" and x["source"] in F.SOURCES for x in j)
    # Au 2 septembre 2026, l'article 50 est passé ; l'annexe III ne l'est pas.
    par = {x["date"]: x for x in j}
    assert par["2026-08-02"]["passe"] is True
    assert par["2027-12-02"]["passe"] is False
    # Un projet de 27 à 52 mois depuis septembre 2026 englobe la date de l'annexe III.
    assert par["2027-12-02"]["avant_fin_projet"] is True


def test_la_migration_n_apparait_que_s_il_y_a_deux_systemes():
    assert F.planning({"n_si_source": 1}, "2026-10-01")["migration"] is None
    m = F.planning({"n_si_source": 2}, "2026-10-01")["migration"]
    assert m and m["source"] in F.SOURCES and m["mois_min"] < m["mois_max"]


# ═══════════════════════════════════════════════════════════════════════════
#  4. LE DIMENSIONNEMENT — refusé sans entrées, dérivé des ratios sourcés
# ═══════════════════════════════════════════════════════════════════════════

def test_le_dimensionnement_refuse_de_poser_une_equipe_par_defaut():
    d = F.dimensionnement({})
    assert d["instruit"] is False and set(d["manque"]) == {"n_cas_usage", "etp_par_cas"}


def test_le_dimensionnement_suit_les_ratios_sources():
    d = F.dimensionnement({"n_cas_usage": 12, "etp_par_cas": 2})
    assert d["instruit"] and d["roles"]["constructeurs"]["max"] == 24
    r_pl = [a for a in F.ANCRAGES if a["cle"] == "ratio_plateforme"][0]
    r_da = [a for a in F.ANCRAGES if a["cle"] == "ratio_data"][0]
    assert abs(d["roles"]["plateforme"]["max"] - 24 * (r_pl["max"] + r_da["max"])) < 1e-9
    assert d["roles"]["plateforme"]["min"] < d["roles"]["plateforme"]["max"]
    assert d["total"]["min"] < d["total"]["max"]


# ═══════════════════════════════════════════════════════════════════════════
#  5. CE QUI EST SERVI, ET À QUI
# ═══════════════════════════════════════════════════════════════════════════

def test_le_referentiel_se_serialise_et_ne_porte_aucun_calcul():
    r = F.referentiel()
    json.dumps(r, ensure_ascii=False)
    assert all("calc" not in p for p in r["postes"])
    assert r["couverture_sources"]["lues"] == 0


def test_la_page_est_fermee_par_construction():
    """La liste blanche laisse fermée toute page qu'on n'a pas décidé d'ouvrir.
    C'est la garantie ; la règle vérifie qu'elle tient pour celle-ci."""
    assert URL not in acces.DIRECT
    assert acces.ouvert(URL) is False
    assert acces.statut(URL) != "direct"


def test_la_page_entre_dans_ce_qui_est_vendu_par_lecture_du_menu():
    """Le périmètre vendu se LIT sur le menu croisé avec la politique : la
    nouvelle rubrique doit y paraître sans qu'on l'ait écrite nulle part."""
    rub = perimetre.rubriques()
    assert rub, "menu illisible"
    mienne = [r for r in rub if any(p["chemin"] == URL for p in r["pages"])]
    assert mienne, "la page n'est pas au menu"
    assert mienne[0]["rubrique"] in perimetre.ce_qui_est_vendu()
    # ET ELLE VIENT JUSTE APRÈS L'INGÉNIERIE DATA CENTER, comme demandé.
    titres = [r["rubrique"] for r in rub]
    i_dc = [i for i, t in enumerate(titres) if "Data Center" in t][0]
    assert titres[i_dc + 1] == mienne[0]["rubrique"], titres[i_dc:i_dc + 2]


def test_le_parcours_guide_pose_un_cadenas_sur_la_page():
    js = _src("parcours.js")
    bloc = js[js.index("var RESERVE = {"):js.index("};", js.index("var RESERVE = {"))]
    assert '"%s": 1' % URL in bloc, "la page vendue n'a pas son cadenas dans le parcours"


def test_le_script_de_page_est_versionne_et_ne_contourne_pas_le_delai():
    app_src = _src("app.py")
    bloc = app_src[app_src.index("_ASSETS_VERSIONNES = ("):]
    bloc = bloc[:bloc.index(")")]
    assert '"ia-factory.js"' in bloc
    js = _src("ia-factory.js")
    assert js.count("function demander(") == 1
    corps = js[js.index("function demander("):]
    corps = corps[corps.index("\n}") + 2:]          # tout ce qui suit la définition
    assert "fetch(" not in corps, "une requête contourne demander() et son délai"
    # AUCUN PRIX DANS LA PAGE NON PLUS : elle affiche ce que le serveur chiffre.
    assert not re.search(r"(tjm|cout_|prix_)\w*\s*[:=]\s*\d", js), (
        "le script porte un prix par défaut")


# L'EN-TÊTE MAISON QUI DIT « MÊME ORIGINE ». Un POST sans « Origin » ni
# « Referer » est refusé en 403 par la garde anti-CSRF AVANT que l'on regarde
# qui le fait — c'est l'ordre voulu, et il n'a rien à voir avec ce module. Le
# client des essais le porte donc, comme le navigateur le ferait.
_MEME_ORIGINE = {"X-CP-Same-Origin": "1"}


def test_les_routes_refusent_l_anonyme(anonyme):
    r = anonyme.get(URL)
    assert r.status_code in (301, 302) and "/connexion" in r.headers.get("Location", "")
    assert anonyme.get("/api/ia-factory").status_code == 401
    # Sans origine : 403 (anti-CSRF, avant tout). Avec l'origine mais sans
    # session : 401. Les deux sont des refus ; la règle exige les deux.
    assert anonyme.post("/api/ia-factory/chiffrer", json={}).status_code == 403
    assert anonyme.post("/api/ia-factory/chiffrer", json={},
                        headers=_MEME_ORIGINE).status_code == 401


def test_les_routes_servent_le_referentiel_et_le_chiffrage(connecte):
    j = connecte.get("/api/ia-factory").get_json()
    assert j["ok"] and j["referentiel"]["couverture_sources"]["lues"] == 0
    r = connecte.post("/api/ia-factory/chiffrer", headers=_MEME_ORIGINE,
                      json={"quantites": {}, "prix": {}, "debut": "2026-10-01"}).get_json()
    assert r["ok"] and r["chiffrage"]["total"] is None
    assert r["planning"]["phases"][0]["debut_tot"] == "2026-10-01"


def test_chaque_identifiant_que_le_script_vise_existe_dans_la_page(connecte):
    """DEUX EXEMPLAIRES DES IDENTIFIANTS : ceux que le script cherche, ceux que la
    page porte. Un identifiant renommé d'un seul côté ne lève rien — la zone
    reste simplement vide, et c'est le lecteur qui découvre le trou."""
    js = _src("ia-factory.js")
    vises = set(re.findall(r'\$\("([a-z0-9-]+)"\)', js))
    page = connecte.get(URL).get_data(as_text=True)
    portes = set(re.findall(r'id="([^"]+)"', page))
    assert vises, "le script ne vise aucun identifiant ?"
    manquants = sorted(vises - portes)
    assert not manquants, "le script vise des identifiants absents de la page : %s" % manquants
