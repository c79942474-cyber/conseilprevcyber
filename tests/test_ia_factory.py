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
import html
import io
import json
import os
import re
import subprocess
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


def test_chaque_script_de_la_page_est_REELLEMENT_SERVI(connecte):
    """LA RÈGLE QUI MANQUAIT, ET LE DÉFAUT QU'ELLE AURAIT PRIS.

    La version précédente vérifiait que « ia-factory.js » figurait dans
    `_ASSETS_VERSIONNES` — la liste qui VERSIONNE les URL. Elle était verte
    pendant que le script rendait 404 : aucune route ne le servait, chaque
    script de ce site ayant la sienne, explicite. La page se servait
    parfaitement ; le navigateur, lui, ne chargeait rien. Ni secteurs, ni
    champs, ni parcours guidé — et RIEN côté serveur ne le signalait, parce
    qu'une page qui référence un script absent est une page valide.

    La propriété est donc : CHAQUE script que la page référence répond 200
    avec un type JavaScript. Elle se moque de savoir dans quelle liste il est
    inscrit ; elle demande au serveur.
    """
    page = connecte.get(URL).get_data(as_text=True)
    scripts = re.findall(r'<script src="(/[^"?]+\.js)', page)
    assert scripts, "la page ne référence aucun script ?"
    fautes = []
    for src in scripts:
        r = connecte.get(src)
        t = (r.headers.get("Content-Type") or "").lower()
        if r.status_code != 200 or "javascript" not in t:
            fautes.append("%s → %d, type %r" % (src, r.status_code, t))
    assert not fautes, (
        "des scripts référencés par la page ne sont pas servis :\n  %s"
        % "\n  ".join(fautes))


def test_le_script_de_page_ne_contourne_pas_le_delai():
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


# ═══════════════════════════════════════════════════════════════════════════
#  6. AUCUNE ENTREPRISE, AUCUNE PERSONNE
# ═══════════════════════════════════════════════════════════════════════════
#
# LA DEMANDE, ET LA SEULE FAÇON DE LA TENIR. « Ne citer aucun nom d'entreprise
# ou de personne dans le module, les supprimer. » Une relecture ne tient pas
# une telle règle : le premier ancrage ajouté demain la rompra sans bruit.
#
# CE QUI EST CONTRÔLÉ, ET CE QUI NE PEUT PAS L'ÊTRE. On vérifie que les noms
# effectivement présents avant cette demande ont disparu de tout ce que le
# module REND — titres, éditeurs, réserves, ancrages, secteurs, parcours — et
# des textes de la page, du script et du menu. On ne peut pas prouver
# l'absence de TOUT nom propre concevable ; on prouve l'absence de ceux qu'on
# a retirés, ce qui est la propriété demandée.
#
# LES ADRESSES SONT HORS DE LA RÈGLE, ET C'EST UN ARBITRAGE ÉCRIT. Une source
# qu'on ne peut pas rouvrir est une intention, pas une source : anonymiser les
# URL les rendrait inutilisables. Le module le dit dans sa limite publiée.

_NOMS_INTERDITS = (
    # entreprises et groupes
    "BPCE", "Banque Populaire", "Banques Populaires", "Caisse d'Épargne", "Caisses d'Épargne",
    "Equinoxe", "MySys", "Orion", "BCG", "Boston Consulting", "Wavestone", "Very Up",
    "Crédit Agricole", "Société Générale", "BNP Paribas", "BNP", "JPMorgan", "Crédit Mutuel",
    "La Banque Postale", "TSB", "Slaughter and May", "McKinsey", "Gartner", "Stanford",
    "NVIDIA", "Nvidia", "DGX", "SuperPOD", "Mistral", "OpenAI", "Anthropic", "Google",
    "DeepMind", "Microsoft", "Adobe", "KORE1", "White & Case", "Skadden", "Deloitte",
    "InfoQ", "Consultor", "Arcep", "ANSSI", "Legiscope",
    # personnes citées dans le cas fourni
    "Tyrode", "Réquillart", "Requillart",
)


def _textes_rendus():
    """Toutes les chaînes que le module REND, sauf les adresses.

    On descend récursivement : une chaîne enfouie dans un secteur ou un
    parcours est aussi lue par un client que celle du premier niveau."""
    out = []

    def descendre(x, cle=None):
        if isinstance(x, str):
            if cle != "url":
                out.append(x)
        elif isinstance(x, dict):
            for k, v in x.items():
                descendre(k)
                descendre(v, k)
        elif isinstance(x, (list, tuple)):
            for v in x:
                descendre(v, cle)
    descendre(F.referentiel())
    return out


def test_le_module_ne_nomme_aucune_entreprise_ni_personne():
    fautes = []
    for t in _textes_rendus():
        for nom in _NOMS_INTERDITS:
            if nom in t:
                fautes.append("« %s » dans : %s" % (nom, t[:110]))
    assert not fautes, ("le module rend des noms qu'il ne doit plus porter :\n  %s"
                        % "\n  ".join(sorted(set(fautes))[:12]))


def test_la_page_le_script_et_le_menu_ne_nomment_personne_non_plus():
    """Le module peut être propre et la page porter encore les noms : ce sont
    deux exemplaires, et c'est celui qu'on oublie qui reste."""
    fautes = []
    for nom_fichier in ("ingenierie-ia-factory.html", "ia-factory.js"):
        src = _src(nom_fichier)
        # Les adresses sont hors règle, ici aussi : on retire les attributs href
        # et les chaînes d'URL avant de chercher.
        sans_url = re.sub(r'href="[^"]*"', "", src)
        sans_url = re.sub(r'https?://\S+', "", sans_url)
        for nom in _NOMS_INTERDITS:
            if nom in sans_url:
                fautes.append("%s : « %s »" % (nom_fichier, nom))
    # Le menu et le parcours : uniquement les entrées de CETTE page.
    for nom_fichier, motif in (("nav.js", r'[^\n]*ingenierie-ia-factory[^\n]*'),
                               ("parcours.js", r'[^\n]*ingenierie-ia-factory[^\n]*')):
        for ligne in re.findall(motif, _src(nom_fichier)):
            for nom in _NOMS_INTERDITS:
                if nom in ligne:
                    fautes.append("%s : « %s » dans %s" % (nom_fichier, nom, ligne[:70]))
    assert not fautes, "des noms subsistent hors du module :\n  %s" % "\n  ".join(sorted(set(fautes)))


def test_les_adresses_restent_joignables_et_l_arbitrage_est_ecrit():
    """LA CONTREPARTIE DE L'ANONYMAT, ET ELLE DOIT ÊTRE DITE. Anonymiser les
    adresses rendrait les sources invérifiables. La règle exige donc que les
    adresses subsistent ET que le module écrive pourquoi."""
    assert F.couverture_sources()["avec_adresse"] >= 30, "trop peu d'adresses conservées"
    lim = F.referentiel()["limite"] + F.couverture_sources()["limite"]
    assert "adresse" in lim and ("nomme" in lim or "nature" in lim), (
        "l'arbitrage entre anonymat des éditeurs et adresses joignables n'est pas écrit")


# ═══════════════════════════════════════════════════════════════════════════
#  7. LES SECTEURS
# ═══════════════════════════════════════════════════════════════════════════

def test_les_quatre_secteurs_demandes_existent_et_sont_instruits():
    assert set(F.SECTEURS) == {"banque", "assurance", "marches", "nis2"}
    for cle, s in F.SECTEURS.items():
        assert s["resume"].strip() and s["autorites"].strip() and s["propre"].strip(), cle
        assert s["textes"], cle
        for t in s["textes"]:
            assert t in F.SOURCES, (cle, t)
        assert s["cas_usage"], cle
        for c in s["cas_usage"]:
            assert c["classe"] in F.CLASSES_CAS, (cle, c["classe"])
            assert c["pourquoi"].strip(), (cle, c["nom"])
        for j in s["jalons"]:
            assert j["source"] in F.SOURCES, (cle, j["source"])


def test_choisir_un_secteur_ajoute_des_postes_et_des_quantites():
    """UN SECTEUR QUI N'AJOUTERAIT RIEN NE SERAIT QU'UNE ÉTIQUETTE."""
    base = F.chiffrer({}, {}, None, None)["n_postes"]
    for cle in F.SECTEURS:
        n = F.chiffrer({}, {}, None, cle)["n_postes"]
        assert n > base, "le secteur %s n'ajoute aucun poste" % cle
        q = F.quantites_pour(cle)
        assert len(q) > len(F.QUANTITES), "le secteur %s n'ajoute aucune quantité" % cle


def test_sans_secteur_l_etude_se_declare_incomplete():
    c = F.chiffrer({}, {}, None, None)
    assert c["secteur"] is None
    assert any("Aucun secteur" in a for a in c["alertes"])
    # Un secteur inconnu ne fait pas tomber : il est ignoré ET signalé.
    inc = F.chiffrer({}, {}, None, "poterie")
    assert inc["secteur"] is None and any("Aucun secteur" in a for a in inc["alertes"])


def test_chaque_poste_sectoriel_consomme_un_prix_du_client():
    for p in F.POSTES_SECTEUR:
        assert any(k in F.PRIX for k in p["besoin"]), p["cle"]
        assert p["secteurs"] and all(x in F.SECTEURS for x in p["secteurs"]), p["cle"]
        assert p.get("couvre", "").strip() and p.get("exclut", "").strip(), (
            "le poste sectoriel %s ne dit pas ce qu'il couvre ET ce qu'il exclut" % p["cle"])


def test_chaque_poste_dit_ce_qu_il_couvre_et_ce_qu_il_exclut():
    """« Exclut » est la ligne qui empêche de compter deux fois ou d'oublier."""
    for p in F.POSTES:
        assert p.get("couvre", "").strip(), p["cle"]
        assert p.get("exclut", "").strip(), p["cle"]


def test_les_jalons_d_un_secteur_se_fondent_et_se_trient():
    for cle, s in F.SECTEURS.items():
        j = F.jalons_pour(cle)
        assert len(j) == len(F.JALONS_REGLEMENTAIRES) + len(s["jalons"]), cle
        assert [x["date"] for x in j] == sorted(x["date"] for x in j), cle
    # L'assurance porte Solvabilité II révisée ; la banque non.
    assert any(x["date"] == "2027-01-30" for x in F.jalons_pour("assurance"))
    assert not any(x["date"] == "2027-01-30" for x in F.jalons_pour("banque"))
    # NIS 2 porte ses deux dates de 2024 en tête.
    assert [x["date"] for x in F.jalons_pour("nis2")][:2] == ["2024-10-17", "2024-10-18"]


# ═══════════════════════════════════════════════════════════════════════════
#  8. LE PARCOURS GUIDÉ ET LES PHASES DÉTAILLÉES
# ═══════════════════════════════════════════════════════════════════════════

def test_chaque_role_du_parcours_vise_des_sections_qui_existent(connecte):
    page = connecte.get(URL).get_data(as_text=True)
    sections = set(re.findall(r'id="(s-[a-z-]+)"', page))
    assert sections, "la page ne porte aucune section"
    for r in F.PARCOURS:
        assert len(r["etapes"]) >= 3, "le rôle %s n'a que %d étape(s)" % (r["id"], len(r["etapes"]))
        assert r["nom"].strip() and r["vient_pour"].strip(), r["id"]
        for e in r["etapes"]:
            assert e["section"] in sections, (
                "le rôle %s vise la section %s, absente de la page" % (r["id"], e["section"]))
            assert e["faire"].strip() and e["obtenir"].strip(), (r["id"], e["section"])


def test_le_parcours_couvre_les_sections_qui_portent_une_decision():
    """UN PARCOURS QUI IGNORE UNE SECTION LA REND INVISIBLE à qui s'y fie."""
    vises = {e["section"] for r in F.PARCOURS for e in r["etapes"]}
    for attendue in ("s-secteur", "s-saisie", "s-chiffrage", "s-planning",
                     "s-changement", "s-migration", "s-conformite", "s-sources"):
        assert attendue in vises, "aucun rôle ne mène à %s" % attendue


def test_le_script_ne_recopie_ni_les_roles_ni_les_secteurs():
    js = _src("ia-factory.js")
    for r in F.PARCOURS:
        assert r["nom"] not in js, "le script recopie le rôle « %s »" % r["nom"]
    for cle, s in F.SECTEURS.items():
        assert s["nom"] not in js, "le script recopie le secteur « %s »" % s["nom"]
    assert "REF.parcours" in js and "REF.secteurs" in js, (
        "le script doit LIRE les rôles et les secteurs servis par l'API")


def test_chaque_phase_dit_son_entree_ses_activites_et_sa_sortie():
    for ph in F.PHASES:
        for champ in ("entree", "sortie"):
            assert ph[champ].strip(), (ph["cle"], champ)
        assert len(ph["activites"]) >= 3, ph["cle"]
        assert ph["livrables"] and ph["jalon"].strip(), ph["cle"]
    pl = F.planning({}, "2026-10-01")
    assert all(p["entree"] and p["sortie"] and p["activites"] for p in pl["phases"])


# ═══════════════════════════════════════════════════════════════════════════
#  9. LE CENTRAGE — lu dans la feuille, pas affirmé
# ═══════════════════════════════════════════════════════════════════════════

def test_les_sections_sont_centrees_et_le_texte_suivi_reste_aligne():
    """CE QUI EST CENTRÉ, ET CE QUI NE L'EST PAS. Le bloc est centré dans la
    colonne ; le TEXTE des paragraphes reste aligné à gauche. Centrer les
    lignes d'un paragraphe de dix lignes déplace le point de retour de l'œil à
    chaque ligne — c'est un effet connu, pas une préférence. La règle tient
    les deux moitiés de cet arbitrage : sans la seconde, « centrer » serait
    compris comme « centrer le texte », et la lecture suivie en pâtirait."""
    css = _src("ingenierie-ia-factory.html")
    bloc = re.search(r"\.iaf-sec\{([^}]*)\}", css)
    assert bloc and "margin:34px auto" in bloc.group(1), (
        "les sections ne sont pas centrées dans la colonne")
    para = re.search(r"\.iaf-sec p\{([^}]*)\}", css)
    assert para and "margin-inline:auto" in para.group(1), (
        "les paragraphes ne sont pas centrés dans leur section")
    assert "text-align:center" not in (para.group(1) if para else ""), (
        "le TEXTE des paragraphes ne doit pas être centré : la lecture suivie en pâtit")
    titre = re.search(r"\.iaf-sec h2\{([^}]*)\}", css)
    assert titre and "text-align:center" in titre.group(1), (
        "les titres, eux, doivent être centrés")
    # LE DÉFAUT QUE CETTE RÈGLE AVAIT LAISSÉ PASSER, ET QU'UNE CAPTURE A
    # MONTRÉ. Les cartes de tête vivent dans `.iaf-tete`, qui centre : elles
    # HÉRITAIENT du centrage sur des paragraphes de plusieurs lignes — le
    # défaut même que la règle prétendait interdire, à un endroit qu'elle ne
    # regardait pas. Elle regarde maintenant le corps des cartes.
    # LA CASCADE, PAS LA PREMIÈRE OCCURRENCE — la même faute que j'ai déjà
    # commise ailleurs. `.iaf-these div` paraît DEUX fois : d'abord pour la
    # bordure et le fond, ensuite pour l'alignement. Lire la première rendait
    # la règle rouge en accusant la feuille d'un manque qui n'existait pas —
    # et pire, toutes les mutations semblaient alors « tomber », sur une règle
    # déjà en échec. À spécificité égale, c'est la DERNIÈRE qui s'applique.
    blocs = re.findall(r"\.iaf-these div\{([^}]*)\}", css)
    carte = blocs[-1] if blocs else None
    assert carte and "text-align:left" in carte, (
        "le corps des cartes de tête hérite du centrage de `.iaf-tete` : il "
        "doit revenir à gauche, comme tout texte de plusieurs lignes ; "
        "dernière déclaration lue : %r" % carte)


def test_les_cartes_de_tete_restent_breves():
    """UNE CARTE N'EST PAS UN PARAGRAPHE. Trois cartes côte à côte se lisent
    d'un coup d'œil ou ne se lisent pas : au-delà d'environ deux cent cinquante
    signes, elles deviennent trois colonnes de prose que le lecteur saute.
    Le plancher n'est pas une esthétique — c'est ce qui décide si le lecteur
    reçoit la thèse de la page ou l'ignore.

    La règle borne un PLAFOND, pas une longueur : elle laisse écrire plus
    court, et elle n'interdit pas d'ajouter une quatrième carte."""
    page = _src("ingenierie-ia-factory.html")
    bloc = page[page.index('<div class="iaf-these">'):]
    bloc = bloc[:bloc.index("<!-- LE PARCOURS")]
    cartes = re.findall(r"<div><b>(.*?)</b>(.*?)</div>", bloc, re.S)
    assert len(cartes) >= 3, "moins de trois cartes de tête : %d" % len(cartes)
    longues = []
    for titre, corps in cartes:
        t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", corps)).strip()
        if len(t) > 250:
            longues.append("« %s » : %d signes" % (re.sub(r"<[^>]+>", "", titre), len(t)))
    assert not longues, (
        "des cartes de tête sont trop longues pour être lues d'un coup d'œil :\n  %s"
        % "\n  ".join(longues))


def test_la_page_charge_le_script_qui_la_PILOTE(connecte):
    """LE TROU QU'UNE MUTATION A OUVERT, ET QUE LES DEUX RÈGLES PRÉCÉDENTES
    NE VOYAIENT PAS. Elles vérifient que les scripts RÉFÉRENCÉS sont servis :
    retirer la balise `<script>` les laisse toutes deux vertes, et la page est
    aussi morte que lorsque la route manquait.

    La règle ne nomme pas de fichier — un nom figé interdirait de renommer le
    script. Elle vérifie la RELATION : parmi les scripts que la page charge,
    au moins un doit piloter les identifiants de CETTE page. Un script qui ne
    les touche pas est du décor partagé, pas le moteur.
    """
    page = connecte.get(URL).get_data(as_text=True)
    ids = set(re.findall(r'id="(iaf-[a-z-]+)"', page))
    assert ids, "la page ne porte aucun identifiant `iaf-` à piloter"
    pilotes = []
    for src in re.findall(r'<script src="(/[^"?]+\.js)', page):
        corps = connecte.get(src).get_data(as_text=True)
        touches = {i for i in ids if ('"%s"' % i) in corps}
        if len(touches) >= 3:
            pilotes.append((src, len(touches)))
    assert pilotes, (
        "aucun script chargé par la page ne pilote ses identifiants (%s) : la "
        "page s'affiche mais ne fait rien" % ", ".join(sorted(ids)[:5]))


# ═══════════════════════════════════════════════════════════════════════════
#  10. LES DIX BLOCS — bleu tant que c'est à faire, vert quand c'est fait
# ═══════════════════════════════════════════════════════════════════════════

def test_les_dix_blocs_sont_declares_numerotes_et_correspondent_a_la_page(connecte):
    page = connecte.get(URL).get_data(as_text=True)
    ids = re.findall(r'id="(s-[a-z-]+)"', page)
    assert [s["id"] for s in F.SECTIONS] == ids, (
        "les blocs déclarés ne sont pas ceux de la page, dans le même ordre")
    assert [s["numero"] for s in F.SECTIONS] == list(range(1, len(ids) + 1)), (
        "la numérotation n'est pas continue de 1 à %d" % len(ids))
    for s in F.SECTIONS:
        assert s["nature"] in ("mesure", "lecture"), s["id"]
        assert s["critere"].strip(), "le bloc %s ne dit pas ce qui le valide" % s["id"]
        assert s["aide"].strip(), "le bloc %s n'a pas d'infobulle" % s["id"]


def test_un_bloc_MESURE_ne_verdit_pas_sans_son_fait():
    """LE MENSONGE VISUEL QU'IL FAUT INTERDIRE. Un indicateur d'avancement qui
    passe au vert sans que rien ne se soit passé est pire qu'aucun indicateur :
    il est crédible. Chaque bloc « mesure » est donc éprouvé DEUX FOIS — sans
    son fait, puis avec — et il doit changer d'état entre les deux."""
    vide = F.etat_blocs({}, {}, None, None)
    mesures = [s for s in F.SECTIONS if s["nature"] == "mesure"]
    assert mesures, "aucun bloc mesuré ?"
    for s in mesures:
        assert vide[s["id"]]["valide"] is False, (
            "le bloc %s est vert alors que rien n'a été fait" % s["id"])
        assert vide[s["id"]]["dit"].strip(), (
            "le bloc %s ne dit pas ce qui lui manque" % s["id"])
    # Le secteur seul valide le bloc 1, et lui seul.
    sect = F.etat_blocs({}, {}, "banque", None)
    assert sect["s-secteur"]["valide"] is True
    assert sect["s-saisie"]["valide"] is False and sect["s-chiffrage"]["valide"] is False
    # Toutes les entrées renseignées valident la saisie, pas le chiffrage.
    Q = {k: 1 for k in F.quantites_pour("banque")}
    P = {k: 1 for k in F.PRIX}
    plein = F.etat_blocs(Q, P, "banque", None)
    assert plein["s-saisie"]["valide"] is True
    assert plein["s-chiffrage"]["valide"] is False, (
        "le chiffrage ne peut pas être vert avant d'avoir été lancé")
    # Un chiffrage complet valide le chiffrage ET le planning.
    ch = F.chiffrer(Q, P, 0.2, "banque")
    fini = F.etat_blocs(Q, P, "banque", ch)
    assert fini["s-chiffrage"]["valide"] is True and fini["s-planning"]["valide"] is True
    # Et un chiffrage QUI LAISSE UN POSTE NON CHIFFRÉ ne valide pas.
    partiel = F.chiffrer(Q, dict(P, cout_interface=None), 0.2, "banque")
    assert partiel["n_non_chiffres"] > 0
    assert F.etat_blocs(Q, dict(P, cout_interface=None), "banque",
                        partiel)["s-chiffrage"]["valide"] is False


def test_un_bloc_LECTURE_ne_pretend_pas_etre_mesure():
    """PERSONNE NE PEUT CONSTATER UNE LECTURE. Le serveur rend `valide: None`
    pour ces blocs — ni vrai ni faux — et dit que c'est une déclaration. Rendre
    `False` laisserait croire à une mesure qui aurait échoué ; rendre `True`
    serait un mensonge pur."""
    e = F.etat_blocs({}, {}, "banque", None)
    lectures = [s for s in F.SECTIONS if s["nature"] == "lecture"]
    assert len(lectures) >= 4, "trop peu de blocs de lecture pour que la règle mesure"
    for s in lectures:
        assert e[s["id"]]["valide"] is None, (
            "le bloc %s prétend être mesuré alors qu'il ne peut pas l'être" % s["id"])
        assert "déclar" in e[s["id"]]["dit"].lower(), (
            "le bloc %s ne dit pas que son vert est une déclaration" % s["id"])
    js = _src("ia-factory.js")
    assert "J’ai lu" in js or "J'ai lu" in js, (
        "la case de lecture doit dire « J'ai lu » — pas « validé », qui ferait "
        "croire à une vérification")


def _champs_rendus(dict_champs, exemples=None):
    """LE HTML RÉELLEMENT PRODUIT, en exécutant `champs()` TELLE QU'ELLE EST
    SERVIE. Chercher « <select » dans le fichier serait vert pour un select
    mort dans un commentaire, ou pour du code que la page n'atteint jamais.
    On extrait la fermeture du script, on l'évalue, on appelle la fonction, et
    on lit ce qu'elle rend — comme le navigateur.

    Rendu : {clé: fragment HTML de ce champ}."""
    src = _src("ia-factory.js")
    ancre = "\n(function () {\n"           # en colonne 0 : la fermeture de page
    corps = src[src.index(ancre) + len(ancre):src.index("\n  function lire(")]
    prog = corps + ("\nconst d = JSON.parse(process.env.IAF_CHAMPS);"
                    "\nprocess.stdout.write(champs(d.c, 'q', d.e));\n")
    # LES EXEMPLES VIENNENT DU RÉFÉRENTIEL, PAS DU DICTIONNAIRE DU MODULE.
    # C'est ce que la PAGE reçoit. Lus directement dans `F.EXEMPLES`, toutes
    # les règles d'exemples restaient vertes quand `referentiel()` cessait de
    # les publier : le module les avait, la page n'en voyait aucun, et rien ne
    # tombait. Mutation vérifiée.
    env = dict(os.environ, IAF_CHAMPS=json.dumps(
        {"c": dict_champs,
         "e": F.referentiel()["exemples"] if exemples is None else exemples}))
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60, env=env)
    assert out.returncode == 0, out.stderr
    morceaux = out.stdout.split('<label class="iaf-champ">')[1:]
    assert len(morceaux) == len(dict_champs), (
        "champs() n'a pas rendu un champ par entrée : %d pour %d"
        % (len(morceaux), len(dict_champs)))
    return dict(zip(dict_champs.keys(), morceaux))


def test_les_listes_deroulantes_n_inventent_aucune_norme():
    """LA LIGNE À NE PAS FRANCHIR. Une liste de choix sur un PRIX, ou sur une
    charge (« 1,5 ETP par cas »), installerait une norme inventée — exactement
    ce que ce module refuse partout ailleurs. Les choix ne sont admis que sur
    des énumérations STRUCTURELLES ou purement conventionnelles : un ou deux
    systèmes à unifier, un horizon en années, une fraction d'effectif."""
    for cle, v in F.PRIX.items():
        assert not v.get("choix"), (
            "le prix « %s » propose des valeurs : ce module ne propose aucun prix" % cle)
    # LES QUANTITÉS SECTORIELLES SONT SOUMISES À LA MÊME LOI. Elles passent
    # par la même fonction de rendu ; les oublier ici laissait une porte par
    # laquelle une norme inventée pouvait entrer sans que rien ne le dise.
    for cle, v in F.QUANTITES_SECTEUR.items():
        assert not v.get("choix"), (
            "la quantité sectorielle « %s » propose des valeurs : aucune "
            "énumération structurelle n'a été décidée pour elle" % cle)
    autorises = {"n_si_source", "duree_mois", "part_formes", "part_appels_ia"}
    avec = {k for k, v in F.QUANTITES.items() if v.get("choix")}
    # L'ÉGALITÉ, ET NON L'INCLUSION. Avec « <= », retirer les choix d'UNE des
    # quatre quantités survivait à la batterie : il restait des listes, la
    # règle se taisait, et une commande promise avait disparu sans bruit. Les
    # quatre énumérations sont une décision écrite ; elle se garde dans les
    # deux sens.
    assert avec == autorises, (
        "les quantités à liste ne sont plus les quatre énumérations "
        "structurelles décidées : en trop %s, manquantes %s"
        % (sorted(avec - autorises) or "—", sorted(autorises - avec) or "—"))
    for k in avec:
        for val, libelle in F.QUANTITES[k]["choix"]:
            assert isinstance(val, (int, float)) and str(libelle).strip(), (k, val)


def test_une_liste_declaree_est_une_liste_QU_ON_VOIT():
    """CE QUE CETTE RÈGLE A COÛTÉ. La première version posait un `datalist` sur
    l'`<input type="number">`. Les quatre listes étaient bien dans le document,
    et AUCUN navigateur courant n'affiche d'indicateur de liste sur un champ
    numérique : l'utilisateur ne voyait rien, et l'a dit. Ma règle, elle, était
    verte — parce qu'elle vérifiait que le module DÉCLARE des choix, jamais
    qu'on en VOIE un. Une règle qui passe pour une raison sans rapport avec ce
    qu'elle prétend.

    Elle éprouve donc quatre propriétés du HTML RÉELLEMENT RENDU :
      1. un champ à choix rend un `select` — un élément que le navigateur
         dessine de lui-même, et non une suggestion facultative ;
      2. il rend UNE option par choix, plus le vide, plus une SORTIE LIBRE :
         sans cette porte, la liste cesserait de suggérer pour contraindre, et
         le client ne pourrait plus dire sa valeur exacte ;
      3. le champ numérique est alors CACHÉ : deux commandes visibles pour une
         seule valeur, c'est celle qu'on oublie qui part au serveur ;
      4. un champ sans choix ne rend AUCUNE liste et reste, lui, visible."""
    # TOUT CE QUE LA PAGE PEUT RENDRE, quantités sectorielles comprises :
    # elles passent par la même fonction, elles obéissent à la même loi.
    echantillon = dict(F.QUANTITES)
    echantillon.update(F.QUANTITES_SECTEUR)
    rendus = _champs_rendus(echantillon)
    assert "datalist" not in "".join(rendus.values()), (
        "un datalist est revenu : sur un champ numérique, il ne se voit pas")

    avec = sorted(k for k, v in echantillon.items() if v.get("choix"))
    sans = sorted(k for k, v in echantillon.items() if not v.get("choix"))
    assert avec and sans, "l'échantillon ne permet pas de comparer"

    for k in avec:
        h = rendus[k]
        assert "<select" in h and "</select>" in h, (
            "le champ « %s » déclare des choix et ne rend pas de liste visible" % k)
        options = re.findall(r"<option value=\"([^\"]*)\"[^>]*>([^<]*)</option>", h)
        assert len(options) == len(echantillon[k]["choix"]) + 2, (
            "« %s » : %d options pour %d choix + le vide + la sortie libre"
            % (k, len(options), len(echantillon[k]["choix"])))
        valeurs = [v for v, _ in options]
        assert valeurs[0] == "", "la liste de « %s » n'offre pas de retour au vide" % k
        libre = [t for v, t in options if v and not re.match(r"^-?[\d.]+$", v)]
        assert libre, (
            "« %s » : la liste n'offre aucune SORTIE LIBRE — elle contraindrait "
            "le client à une valeur ronde au lieu de la sienne" % k)
        for val, libelle in echantillon[k]["choix"]:
            chiffrees = [x for x, _ in options if re.match(r"^-?[\d.]+$", x or "")]
            assert any(float(x) == float(val) for x in chiffrees), (
                "« %s » : le choix %r du module n'est pas dans la liste" % (k, val))
            textes = [t for _, t in options if libelle in t]
            assert textes, (
                "« %s » : le choix %r est rendu sans son libellé — une valeur "
                "nue ne dit pas ce qu'elle signifie" % (k, val))
            # ET LA VALEUR EN CHIFFRES, DANS L'UNITÉ DU CHAMP. Le champ
            # numérique est MASQUÉ dès qu'on choisit : l'option est alors le
            # seul endroit où le client peut voir que « un quart » vaut 25 %.
            # Un libellé seul survivait à la mutation ; il ne survit plus.
            unite = echantillon[k]["unite"]
            motif = r"([\d\s.,\u202f\u00a0]+)\s*%s" % ("%" if unite == "part"
                                                        else re.escape(unite))
            m = re.search(motif, textes[0])
            assert m, ("« %s » : l'option %r ne dit pas la valeur dans son unité "
                       "(%s)" % (k, textes[0], unite))
            lu = float(re.sub(r"[\s\u202f\u00a0]", "", m.group(1)).replace(",", "."))
            attendu = float(val) * (100 if unite == "part" else 1)
            assert abs(lu - attendu) < 1e-6, (
                "« %s » : l'option affiche %s et le chiffrage recevra %r"
                % (k, m.group(0).strip(), val))
        entree = re.search(r"<input[^>]*data-cle=\"%s\"[^>]*>" % re.escape(k), h)
        assert entree and " hidden" in entree.group(0), (
            "« %s » : la liste ET le champ sont visibles ensemble — deux "
            "commandes pour une valeur" % k)

    for k in sans:
        h = rendus[k]
        # AUCUNE LISTE FERMÉE — c'est le mécanisme `choix`, celui qui contraint,
        # et il reste réservé aux quatre énumérations structurelles. Une liste
        # d'EXEMPLES peut en revanche être là : elle suggère, elle ne contraint
        # pas, et les règles qui suivent l'éprouvent.
        assert "data-choix=" not in h, (
            "le champ « %s » ne déclare aucun choix et rend pourtant une liste "
            "fermée" % k)
        entree = re.search(r"<input[^>]*data-cle=\"%s\"[^>]*>" % re.escape(k), h)
        assert entree and " hidden" not in entree.group(0), (
            "« %s » : le seul champ de saisie est caché — rien à remplir" % k)


# ═══════════════════════════════════════════════════════════════════════════
#  LES EXEMPLES — suggérer sans devenir un barème
# ═══════════════════════════════════════════════════════════════════════════
#
# CE QUI SÉPARE UN EXEMPLE D'UN CHOIX, ET POURQUOI LA LIGNE TIENT ENCORE.
# `test_les_listes_deroulantes_n_inventent_aucune_norme` interdit une liste de
# CHOIX sur un prix : elle installerait une norme inventée. Un formulaire de
# vingt-cinq cases vides pose pourtant au client une question qu'il ne peut pas
# trancher — « ce que j'écris est-il vraisemblable ? » — et il renonce, ou il
# écrit n'importe quoi.
#
# Les exemples répondent à cela SANS devenir un barème, à trois conditions que
# ces règles tiennent une par une. Sans la troisième, `exemples` ne serait que
# `choix` sous un autre nom.

def test_un_exemple_ne_se_choisit_jamais_TOUT_SEUL():
    """PREMIÈRE CONDITION. Une liste pré-sélectionnée met le chiffre du cabinet
    dans le champ sans que personne ne l'ait voulu — et il partira au chiffrage
    comme s'il venait du client."""
    echantillon = dict(F.QUANTITES); echantillon.update(F.PRIX)
    rendus = _champs_rendus(echantillon)
    for k, h in rendus.items():
        if "data-exemple=" not in h:
            continue
        bloc = h[h.index("data-exemple="):]
        bloc = bloc[:bloc.index("</select>")]
        options = re.findall(r'<option value="([^"]*)"([^>]*)>', bloc)
        assert options[0][0] == "", "« %s » : la liste d'exemples ne s'ouvre pas sur le vide" % k
        selectionnees = [v for v, attrs in options if "selected" in attrs]
        assert not selectionnees, (
            "« %s » : un exemple est pré-sélectionné (%s)" % (k, selectionnees))


def test_chaque_exemple_dit_DOU_IL_VIENT():
    """DEUXIÈME CONDITION. « 900 €/jour » sans rien d'autre est un barème.
    « 900 €/jour — usage du cabinet, à remplacer » est un point de départ."""
    echantillon = dict(F.QUANTITES); echantillon.update(F.PRIX)
    rendus = _champs_rendus(echantillon)
    vus = 0
    for k, h in rendus.items():
        if "data-exemple=" not in h:
            continue
        bloc = h[h.index("data-exemple="):h.index("</select>", h.index("data-exemple="))]
        for ex in F.EXEMPLES[k]:
            vus += 1
            motif = r'<option value="%s" data-prov="%s">([^<]*)</option>' % (
                re.escape(str(ex["valeur"])), re.escape(ex["provenance"]))
            m = re.search(motif, bloc)
            assert m, ("« %s » : l'exemple %r ne porte pas sa provenance dans "
                       "l'option" % (k, ex["libelle"]))
            texte = html.unescape(m.group(1))
            assert ex["libelle"] in texte, (k, texte)
            assert "(" in texte and ")" in texte, (
                "« %s » : l'option ne dit pas en clair d'où vient la valeur : %r"
                % (k, texte))
    assert vus >= 40, "l'échantillon ne couvre presque aucun exemple (%d)" % vus


def test_LE_POINT_QUI_DECIDE_ce_qui_reste_un_exemple_est_COMPTE():
    """TROISIÈME CONDITION, ET LA SEULE QUI PROTÈGE L'ÉTUDE EXPORTÉE.

    Les deux précédentes ne protègent que le moment de la saisie. Un client qui
    n'aurait rien remplacé repartirait sinon avec les ordres de grandeur du
    cabinet présentés comme les siens — et une étude chiffrée a l'air d'une
    étude chiffrée, quels que soient les nombres dedans.

    La règle éprouve les DEUX sens : une valeur reprise d'un exemple « cabinet »
    est signalée ; une valeur qui n'en vient pas ne l'est pas."""
    cabinet = next((k, e) for k, l in F.EXEMPLES.items() for e in l
                   if e["provenance"] == "cabinet" and k in F.PRIX)
    cle, ex = cabinet
    signale = F.valeurs_dexemple({}, {cle: ex["valeur"]})
    assert [x["champ"] for x in signale] == [cle], signale
    assert signale[0]["a_remplacer"] is True
    assert signale[0]["libelle"] == ex["libelle"]

    # LE TÉMOIN NÉGATIF. Sans lui, une fonction qui signale TOUT passerait.
    autre = float(ex["valeur"]) * 1.37 + 1
    assert F.valeurs_dexemple({}, {cle: autre}) == [], (
        "une valeur qui ne vient d'aucun exemple est signalée quand même")

    # ET LE BLOC DE SAISIE LE DIT, sinon le compte resterait dans une réponse
    # que personne ne lit.
    dit = F.etat_blocs({}, {cle: ex["valeur"]}, None, None)["s-saisie"]["dit"]
    assert "cabinet" in dit and "remplacer" in dit, dit
    assert "cabinet" not in F.etat_blocs({}, {cle: autre}, None, None)["s-saisie"]["dit"]


def test_un_exemple_qui_se_reclame_dune_source_la_DESIGNE():
    """« Traçable à une source du module » est une promesse vérifiable : ou
    l'ancrage existe, ou l'exemple se réclame d'une intention. Le module refuse
    au chargement — la règle éprouve ce refus."""
    cles = {a["cle"] for a in F.ANCRAGES}
    for champ, liste in F.EXEMPLES.items():
        for ex in liste:
            if ex["provenance"] == "ancrage":
                assert ex["ancrage"] in cles, (champ, ex)

    reel = F.EXEMPLES["tjm_conseil"]
    F.EXEMPLES["tjm_conseil"] = [{"valeur": 1, "libelle": "X",
                                  "provenance": "ancrage", "ancrage": "n_existe_pas"}]
    try:
        with pytest.raises(ValueError) as e:
            F._verifier_exemples()
        assert "n_existe_pas" in str(e.value)
    finally:
        F.EXEMPLES["tjm_conseil"] = reel


def test_lavertissement_precede_les_totaux():
    """UN AVERTISSEMENT PLACÉ SOUS UN MONTANT ARRIVE APRÈS QUE LE LECTEUR L'A
    RETENU — et un montant retenu ne se corrige plus. L'ordre n'est pas une
    question de mise en page : c'est ce qui décide si l'avertissement sert."""
    js = _src("ia-factory.js")
    # L'AFFECTATION QUI PEINT LE RÉSULTAT, pas celle qui écrit « en cours… » :
    # la première assignation trouvée n'était pas la bonne, et la règle tombait
    # en accusant un défaut qui n'existait pas.
    m = next((x for x in re.finditer(r"out\.innerHTML\s*=\s*(.+?);", js, re.S)
              if "rendreChiffrage" in x.group(1)), None)
    assert m, "le chiffrage ne peint plus le résultat dans « out »"
    expr = m.group(1)
    i = expr.index("rendreValeursDexemple")
    j = expr.index("rendreChiffrage")
    assert i < j, ("l'avertissement est concaténé APRÈS les totaux : %r" % expr[:160])


def test_les_listes_dexemples_sont_REELLEMENT_branchees():
    """Une liste qui ne fait rien propose un point de départ et ne le pose pas.
    Les DEUX rendus sont contrôlés — les quantités et les prix passent par des
    chemins différents, et c'est celui qu'on oublie qui reste mort."""
    _appel_pose('$("iaf-p").innerHTML', "brancherExemples")
    # CHERCHÉ DANS SA FONCTION, ET PAS « QUELQUE PART PLUS BAS ». Bornée au
    # fichier, la recherche trouvait l'appel du bloc des PRIX, plus bas : la
    # règle restait verte alors que le branchement des quantités avait disparu.
    # Une règle satisfaite par une occurrence voisine ne mesure rien.
    js = _src("ia-factory.js")
    corps = js[js.index("function redessinerQuantites("):]
    corps = corps[:corps.index("\n  }")]
    assert '$("iaf-q").innerHTML' in corps, "le rendu des quantités a changé de place"
    assert any(l.strip() == "brancherExemples();" for l in corps.split("\n")), (
        "les listes d'exemples des quantités ne sont pas branchées")


def test_aucun_PRIX_ne_gagne_de_liste_fermee_par_la_bande():
    """LA LIGNE D'ORIGINE, RÉAFFIRMÉE. Les exemples ne doivent pas devenir le
    chemin par lequel un barème entre : un prix garde son champ libre visible,
    et ne reçoit jamais de `choix`."""
    rendus = _champs_rendus(dict(F.PRIX))
    for k, h in rendus.items():
        assert "data-choix=" not in h, "le prix « %s » a gagné une liste fermée" % k
        entree = re.search(r'<input[^>]*data-cle="%s"[^>]*>' % re.escape(k), h)
        assert entree and " hidden" not in entree.group(0), (
            "« %s » : le champ libre est caché derrière une liste" % k)


def test_la_liste_renseigne_le_champ_et_ne_porte_pas_la_valeur():
    """UN SEUL PORTEUR DE LA VALEUR. `lire()` ne regarde que les `input` : si la
    liste portait la valeur de son côté, les deux dériveraient et c'est celui
    qu'on oublie qui partirait au serveur. La liste doit donc ÉCRIRE dans le
    champ, et le redessinage doit savoir REVENIR de la valeur vers la liste,
    sinon un secteur changé afficherait « non renseigné » sur un champ rempli."""
    js = _src("ia-factory.js")
    bloc = js[js.index("function brancherChoix("):]
    bloc = bloc[:bloc.index("\n  }")]
    assert "champ.value = sel.value" in bloc, (
        "la liste ne renseigne pas le champ : elle serait décorative")
    assert "champ.hidden = false" in bloc and "champ.focus()" in bloc, (
        "la sortie libre n'ouvre pas le champ — l'option serait un cul-de-sac")
    assert 'dispatchEvent(new Event("input"' in bloc, (
        "choisir dans la liste ne relance pas le calcul de l'état des blocs")
    lu = js[js.index("function lire("):]
    lu = lu[:lu.index("\n  }")]
    assert "data-choix" not in lu and "select" not in lu, (
        "lire() regarde la liste : la valeur aurait deux porteurs")
    red = js[js.index("function redessinerQuantites("):]
    red = red[:red.index("\n  }")]
    assert "brancherChoix()" in red, (
        "les listes redessinées ne sont plus branchées : muettes après un "
        "changement de secteur")
    assert "sel.value" in red, (
        "une valeur reprise ne retrouve pas sa place dans la liste")


def test_la_page_encadre_en_bleu_et_passe_au_vert(connecte):
    """LA COULEUR EST LUE DANS LA FEUILLE, pas affirmée. Et elle n'est pas le
    seul signal : une pastille porte l'état en toutes lettres, pour qui ne
    distingue pas les deux teintes."""
    css = _src("ingenierie-ia-factory.html")
    # UNE REQUÊTE MÉDIA N'EST PAS DE LA CASCADE — troisième fois que ce piège
    # se referme sur moi. La DERNIÈRE déclaration `.iaf-sec` du fichier est
    # celle de `@media(prefers-reduced-motion)`, qui ne pose qu'une transition :
    # la lire revenait à juger l'encadrement sur un bloc qui n'en parle pas.
    # On écarte donc les blocs conditionnels avant de lire le flux.
    flux = re.sub(r"@media[^{]*\{(?:[^{}]|\{[^{}]*\})*\}", "", css)
    base = re.findall(r"\.iaf-sec\{([^}]*)\}", flux)
    assert base and "border" in base[-1], "les blocs ne sont pas encadrés"
    bleu = [b for b in base if "3884de" in b]
    assert bleu, "l'encadrement au repos n'est pas bleu"
    vert = re.search(r"\.iaf-sec\.ok\{([^}]*)\}", css)
    assert vert and "--teal" in vert.group(1), (
        "l'état validé ne passe pas au vert")
    js = _src("ia-factory.js")
    # LA RECHERCHE EST BORNÉE À LA FONCTION QUI PEINT, et ce n'est pas un
    # détail : chercher `classList.remove("ok")` dans TOUT le fichier le
    # trouvait dans le gestionnaire de la case à cocher, pendant que la
    # peinture, elle, ne savait plus que verdir. Mutation vérifiée : elle
    # survivait. Une règle qui cherche une chaîne au mauvais endroit est verte
    # pour une raison sans rapport avec ce qu'elle garde.
    # BORNÉE À LA BOUCLE QUI PEINT, ET PAS À LA FONCTION. Le gestionnaire de
    # la case à cocher vit DANS `peindreBlocs` et contient lui aussi les deux
    # appels : borner à la fonction ne séparait donc rien, et la mutation
    # survivait encore. Deuxième resserrement, vérifié par mutation.
    peint = js[js.index("REF.sections.forEach"):]
    peint = peint[:peint.index("\n    });")]
    assert 'classList.add("ok")' in peint and 'classList.remove("ok")' in peint, (
        "la peinture doit pouvoir REVENIR au bleu : un état qui ne se défait "
        "pas ment dès que le fait cesse")
    assert "iaf-pastille" in js, (
        "l'état doit être écrit en toutes lettres, pas porté par la seule couleur")


def test_les_infobulles_restent_lisibles_sans_souris():
    """UNE INFOBULLE FABRIQUÉE AU SURVOL EXCLUT CEUX QUI N'ONT PAS DE SOURIS,
    et perd son texte pour un lecteur d'écran comme à l'impression. Celle-ci
    est écrite dans le document, portée par un bouton focalisable, et reliée
    par aria-describedby."""
    js = _src("ia-factory.js")
    bloc = js[js.index("function bulle("):]
    bloc = bloc[:bloc.index("\n  }")]
    assert "aria-describedby" in bloc, "l'infobulle n'est pas reliée à ce qu'elle décrit"
    assert 'role="tooltip"' in bloc, "l'infobulle ne se déclare pas comme telle"
    assert "<button" in bloc, (
        "l'infobulle doit être portée par un élément focalisable au clavier")
    assert "esc(texte)" in bloc, "le texte de l'infobulle n'est pas échappé"
    css = _src("ingenierie-ia-factory.html")
    assert ":focus-visible .iaf-bulle" in css or ".iaf-info:focus .iaf-bulle" in css, (
        "l'infobulle ne s'ouvre pas au focus clavier")


def test_l_etat_des_blocs_est_calcule_au_serveur_et_non_recopie():
    """Le critère qui fait verdir un bloc est une DÉCISION. Recopiée dans le
    script, elle dériverait de celle du module au premier poste ajouté — et un
    bloc vert pour un critère périmé est pire qu'un bloc bleu."""
    js = _src("ia-factory.js")
    assert "j.blocs" in js and "peindreBlocs" in js, (
        "la page doit peindre les blocs à partir de ce que le serveur rend")
    for interdit in ("n_non_chiffres === 0", "n_non_chiffres == 0", "manquantes"):
        assert interdit not in js, (
            "le script recalcule un critère de validation (%r) au lieu de le "
            "recevoir" % interdit)


# ═══════════════════════════════════════════════════════════════════════════
#  LES CAS COMPARABLES EN LISTE DÉROULANTE
# ═══════════════════════════════════════════════════════════════════════════
# POURQUOI UN MENU. Chaque cas porte de deux à six chiffres, chacun avec sa
# source ET ce qu'il ne dit pas : à la suite, cela fait un mur qu'on parcourt
# en diagonale. Or ces cas servent à SITUER, pas à caler — et on ne situe pas
# en lisant tout, on situe en comparant un cas à sa propre installation.

def _comparables_rendus(cmp=None, sources=None, secteurs=None):
    """Le HTML que `rendreComparables` produit RÉELLEMENT, en l'exécutant.

    Chercher « <select » dans le script serait vert pour un menu mort dans un
    commentaire."""
    src = _src("ia-factory.js")
    ancre = "\n(function () {\n"
    # LA TRANCHE VA JUSQU'APRÈS `rendreComparables`, qui vit plus bas que
    # `lire` : la borne employée par les autres règles de ce fichier s'arrête
    # avant elle et la fonction n'était pas définie.
    corps = src[src.index(ancre) + len(ancre):src.index("\n  function rendrePhases(")]
    prog = (corps
            + "\nconst d = JSON.parse(process.env.IAF_CMP);"
            + "\nprocess.stdout.write(rendreComparables(d.c, d.s, d.g));\n")
    ref = F.referentiel()
    env = dict(os.environ, IAF_CMP=json.dumps(
        {"c": cmp if cmp is not None else ref["comparables"],
         "s": sources if sources is not None else ref["sources"],
         "g": secteurs if secteurs is not None else ref["secteurs_comparables"]}))
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60, env=env)
    assert out.returncode == 0, out.stderr
    return out.stdout


def test_les_cas_comparables_se_choisissent_dans_une_liste():
    """UN VRAI `select`, que le navigateur dessine de lui-même — la leçon du
    `datalist` invisible s'applique ici aussi.

    ET RANGÉ PAR SECTEUR depuis que les cas ne viennent plus tous de la
    banque : un groupe par activité, chacun avec l'option qui l'ouvre en
    entier. Sans cette option, le groupe ne serait qu'un intertitre."""
    h = _comparables_rendus()
    assert "<select" in h and "</select>" in h, h[:300]
    assert "datalist" not in h, "un datalist ne se voit pas"
    options = re.findall(r'<option value="([^"]*)"[^>]*>([^<]*)</option>', h)
    valeurs = [v for v, _t in options]
    cas = F.comparables()
    groupes = F.secteurs_comparables()
    assert valeurs[0] == "__tous", "le menu n'offre pas de lire les cas à la suite"
    assert [v for v in valeurs if v.startswith("s:")] == ["s:" + g for g in groupes], (
        "les groupes du menu ne suivent pas ceux du module", valeurs, groupes)
    assert sorted(v for v in valeurs if v.startswith("c")) == sorted(
        "c%d" % i for i in range(len(cas))), "un cas n'a pas son option"
    assert len(valeurs) == 1 + len(groupes) + len(cas), valeurs


def test_chaque_cas_est_range_sous_le_groupe_de_SON_secteur():
    """UN CAS RANGÉ SOUS LA MAUVAISE ACTIVITÉ EST PIRE QU'UN CAS NON RANGÉ :
    il fait croire à un repère sectoriel qui n'en est pas un. La règle relit
    l'ordre réel du menu, groupe par groupe."""
    h = _comparables_rendus()
    cas = F.comparables()
    bloc = h[h.index("<select"):h.index("</select>")]
    for morceau in re.findall(r'<optgroup label="([^"]*)">(.*?)</optgroup>', bloc, re.S):
        libelle, dedans = morceau
        sec = re.search(r'<option value="s:([^"]+)"', dedans).group(1)
        assert F.nom_secteur_comparable(sec) in html.unescape(libelle), (libelle, sec)
        for i in [int(x) for x in re.findall(r'<option value="c(\d+)"', dedans)]:
            assert cas[i]["secteur"] == sec, (
                "le cas %d (secteur %s) est rangé sous « %s »"
                % (i, cas[i]["secteur"], sec))


def test_chaque_cas_rendu_PORTE_son_secteur_dans_le_document():
    """SANS CET ATTRIBUT, LE FILTRE PAR GROUPE NE PEUT RIEN — et le menu
    continue d'afficher ses cinq groupes comme si de rien n'était. Deux
    mutations ont survécu à la première batterie pour cette raison : mes règles
    éprouvaient le MENU, et rien n'éprouvait ce sur quoi le menu agit."""
    h = _comparables_rendus()
    cas = F.comparables()
    portes = re.findall(r'<article class="iaf-cmp" data-cas="c(\d+)" data-cmp-sec="([^"]+)"', h)
    assert len(portes) == len(cas), (
        "%d articles portent leur secteur pour %d cas" % (len(portes), len(cas)))
    for i, sec in portes:
        assert cas[int(i)]["secteur"] == html.unescape(sec), (i, sec)


def test_le_filtre_des_cas_traite_les_TROIS_niveaux():
    """Un menu à trois niveaux — tous, un groupe, un cas — dont le filtre n'en
    connaît que deux promet un tri qu'il ne rend pas : choisir un groupe ne
    ferait alors rien du tout, silencieusement."""
    js = _src("ia-factory.js")
    bloc = js[js.index("function brancherComparables("):]
    bloc = bloc[:bloc.index("\n  }")]
    for niveau, quoi in ((("CMP_TOUS",), "« tous les cas »"),
                         (('"s:"',), "« tout un groupe »"),
                         (("dataset.cas",), "« un seul cas »"),
                         (("dataset.cmpSec",), "le secteur porté par l'article")):
        assert any(n in bloc for n in niveau), (
            "le filtre ne traite pas %s : %r" % (quoi, bloc[:400]))
    for interdit in ("innerHTML", "rendreComparables("):
        assert interdit not in bloc, (
            "le filtre redessine (« %s ») au lieu de masquer" % interdit)


def test_les_cas_ne_viennent_pas_TOUS_du_meme_secteur():
    """LE DÉFAUT QUI A DÉCLENCHÉ CE TOUR. Quatre cas, une seule activité : « pour
    situer » ne veut rien dire pour qui n'est pas dans cette activité-là. La
    règle borne une PROPRIÉTÉ — plusieurs activités représentées, et aucune
    qui écrase les autres — jamais un compte, qui interdirait d'en ajouter."""
    cas = F.comparables()
    par_secteur = {}
    for c in cas:
        par_secteur.setdefault(c["secteur"], []).append(c)
    assert len(par_secteur) >= 3, (
        "les cas comparables couvrent %d activité(s) : %s"
        % (len(par_secteur), sorted(par_secteur)))
    domine = max(len(v) for v in par_secteur.values())
    assert domine <= len(cas) / 2, (
        "une seule activité porte %d des %d cas : le repère redevient sectoriel"
        % (domine, len(cas)))
    # Et chaque secteur du module doit être joignable par au moins un cas.
    orphelins = [k for k in F.SECTEURS if k not in par_secteur]
    assert not orphelins, (
        "aucun cas comparable pour : %s — un lecteur de ce secteur n'a aucun "
        "repère" % orphelins)


def test_un_cas_rattache_a_un_secteur_inconnu_est_refuse_au_CHARGEMENT():
    """Un cas dont le secteur n'existe pas ne se rangerait dans aucun groupe :
    il disparaîtrait de la page sans que rien ne le signale. Le module refuse
    au chargement plutôt que de le perdre à l'affichage."""
    reel = F.comparables
    F.comparables = lambda: [{"secteur": "inexistant", "organisation": "X",
                              "chiffres": [], "lecon": "y"}]
    try:
        with pytest.raises(ValueError) as e:
            F.secteurs_comparables()
        assert "inexistant" in str(e.value)
    finally:
        F.comparables = reel


def test_le_nombre_de_cas_vient_des_DONNEES_et_n_est_ecrit_qu_une_fois():
    """« Quatre cas documentés » au-dessus de « Les 4 cas » écrit le même
    nombre de deux façons dans la même commande — et un cinquième cas ajouté
    au module laisserait le premier faux. La règle l'éprouve en RETIRANT un
    cas : le menu doit suivre."""
    cas = F.comparables()
    h = _comparables_rendus()
    assert "%d cas documentés" % len(cas) in h, h[:400]
    assert "Les %d cas" % len(cas) in h
    trois = cas[:3]
    h3 = _comparables_rendus(cmp=trois)
    assert "3 cas documentés" in h3 and "Les 3 cas" in h3, (
        "le compte est écrit en dur : il ne suit pas les données")
    assert "4 cas" not in h3


def test_un_seul_cas_est_ouvert_au_chargement_et_le_menu_dit_combien_il_y_en_a():
    """UN MENU QUI N'EN MONTRE QU'UN PAR DÉFAUT FERAIT CROIRE QU'IL N'Y EN A
    QU'UN, si l'intitulé ne disait pas combien. Le premier est ouvert, les
    autres sont là et masqués — pas absents : les masquer permet de les
    rouvrir sans redessiner, donc sans perdre le choix qu'on vient de poser."""
    h = _comparables_rendus()
    articles = re.findall(r'<article class="iaf-cmp" data-cas="(c\d+)"([^>]*)>', h)
    assert len(articles) == len(F.comparables()), articles
    ouverts = [c for c, attrs in articles if "hidden" not in attrs]
    assert ouverts == ["c0"], (
        "au chargement, %d cas sont ouverts au lieu du premier seul" % len(ouverts))
    assert "cas documentés" in h, "l'intitulé ne dit pas combien il y en a"


def test_l_option_garde_le_repere_du_cas_et_coupe_le_developpement():
    """« Cas A — grand groupe bancaire coopératif : deux réseaux, deux systèmes
    d'information, une usine IA » ne tient pas dans une option sans la rendre
    illisible. On garde le repère et la nature, on coupe après le
    deux-points."""
    h = _comparables_rendus()
    options = dict(re.findall(r'<option value="(c\d+)"[^>]*>([^<]*)</option>', h))
    for i, c in enumerate(F.comparables()):
        t = html.unescape(options["c%d" % i])
        assert t == c["organisation"].split(" : ")[0], (t, c["organisation"])
        assert len(t) < 60, "l'option reste trop longue : %r" % t


def test_le_filtre_masque_et_ne_redessine_pas():
    """Redessiner referait le menu et perdrait le choix au moment même où on
    vient de le poser."""
    js = _src("ia-factory.js")
    bloc = js[js.index("function brancherComparables("):]
    bloc = bloc[:bloc.index("\n  }")]
    assert "hidden" in bloc, "le filtre ne masque rien"
    for interdit in ("innerHTML", "rendreComparables("):
        assert interdit not in bloc, (
            "le filtre redessine (« %s ») au lieu de masquer" % interdit)
    assert "CMP_TOUS" in bloc, "le retour à « tous les cas » ne fait rien"


def test_le_menu_des_cas_n_est_pas_cherche_comme_une_ancre_de_page():
    """UNE RÈGLE DE CE FICHIER VÉRIFIE QUE TOUT IDENTIFIANT VISÉ PAR `$()`
    EXISTE DANS LA PAGE — parce qu'un identifiant renommé d'un seul côté ne
    lève rien et laisse une zone vide. Ce menu n'est pas une ancre de la page :
    c'est le script qui le crée. Le viser par `$()` aurait fait passer pour une
    ancre manquante ce qui n'en est pas une, et affaibli une règle utile."""
    js = _src("ia-factory.js")
    assert '$("iaf-cmp-sel")' not in js
    assert 'document.querySelector("#iaf-cmp [data-cmp]")' in js, (
        "le menu n'est pas cherché dans son conteneur")


def _appel_pose(ancre_rendu, appel):
    """L'appel `appel` suit-il RÉELLEMENT le rendu `ancre_rendu`, sans condition ?

    LA LIGNE DE L'APPEL EST CONTRÔLÉE, PAS SEULEMENT CE QUI LA PRÉCÈDE. C'est
    le trou qu'une mutation a trouvé : `if (REF.absente) brancherX();` laissait
    l'espace entre le rendu et l'appel parfaitement vide, l'indentation
    intacte, et le mot présent — trois contrôles verts pour un menu mort. Une
    condition sur la ligne elle-même est la façon la plus courte de tuer un
    branchement sans le retirer."""
    lignes = _src("ia-factory.js").split("\n")
    i = next(k for k, l in enumerate(lignes) if ancre_rendu in l)
    j = next((k for k, l in enumerate(lignes)
              if k > i and (appel + "()") in l), None)
    assert j is not None, "%s n'est jamais appelé après le rendu" % appel
    entre = "\n".join(lignes[i + 1:j])
    assert not re.search(r"\bif\b|\?|&&|\|\|", entre), (
        "le branchement est sous condition : %r" % entre)
    assert lignes[j].strip() == appel + "();", (
        "l'appel n'est pas une instruction nue — il peut ne jamais s'exécuter :"
        " %r" % lignes[j].strip())
    creux = lambda l: len(l) - len(l.lstrip())
    assert creux(lignes[j]) == creux(lignes[i]) and j - i <= 3, (
        "le branchement ne suit pas immédiatement le rendu")


def test_le_menu_des_cas_est_REELLEMENT_branche():
    """UN MENU QUI NE FAIT RIEN EST PIRE QU'AUCUN MENU : il promet un tri et
    laisse le lecteur devant un seul cas sans moyen d'en voir un autre. Mes
    règles éprouvaient le rendu et le corps du gestionnaire ; aucune ne
    vérifiait qu'il soit POSÉ, et la mutation qui retirait l'appel survivait."""
    _appel_pose('$("iaf-cmp").innerHTML', "brancherComparables")


def test_la_page_n_ecrit_le_nombre_de_cas_NULLE_PART():
    """IL VIVAIT EN TOUTES LETTRES DANS LE CHAPÔ — « Quatre cas publics » —
    pendant que le menu le tient depuis les données. Un cinquième cas ajouté au
    module aurait laissé ce mot faux, et personne ne relit un chapô."""
    h = _src("ingenierie-ia-factory.html")
    i = h.index('id="s-ancrages"')
    bloc = h[i:h.index("</section>", i)]
    for compte in ("Quatre cas", "quatre cas", "4 cas", "Trois cas", "Cinq cas"):
        assert compte not in bloc, (
            "la page écrit le nombre de cas en dur : « %s »" % compte)


# ═══════════════════════════════════════════════════════════════════════════
#  LES SOURCES EN LISTE DÉROULANTE, RANGÉES PAR NATURE
# ═══════════════════════════════════════════════════════════════════════════

def _couverture_de(sources):
    """La couverture d'un corpus quelconque, calculée par LE MODULE — pas par
    une seconde arithmétique écrite dans les règles, qui pourrait diverger."""
    reel = F.SOURCES
    F.SOURCES = sources
    try:
        return F.couverture_sources()
    finally:
        F.SOURCES = reel


def _sources_rendues(sources=None):
    """Le HTML que `rendreSources` produit RÉELLEMENT, en l'exécutant.

    Le corpus est un PARAMÈTRE : c'est ce qui permet d'éprouver que la page
    suit le module au lieu de tomber d'accord avec lui par coïncidence."""
    sources = F.SOURCES if sources is None else sources
    src = _src("ia-factory.js")
    ancre = "\n(function () {\n"
    corps = src[src.index(ancre) + len(ancre):src.index("\n  function rendreChiffrage(")]
    prog = (corps
            + "\nconst d = JSON.parse(process.env.IAF_SRC);"
            + "\nprocess.stdout.write(rendreSources(d.s, d.c));\n")
    env = dict(os.environ, IAF_SRC=json.dumps(
        {"s": sources, "c": _couverture_de(sources)}))
    out = subprocess.run(["node"], input=prog, capture_output=True, text=True,
                         timeout=60, env=env)
    assert out.returncode == 0, out.stderr
    return out.stdout


_CORPUS_TEMOIN = {
    "t_off_1": {"titre": "T1", "editeur": "E1", "annee": 2024, "nature": "officiel",
                "url": "https://example.invalid/1"},
    "t_off_2": {"titre": "T2", "editeur": "E2", "annee": 2025, "nature": "officiel",
                "url": "https://example.invalid/2"},
    "t_pre_1": {"titre": "T3", "editeur": "E3", "annee": 2023, "nature": "presse"},
}


def test_les_sources_se_choisissent_par_NATURE_et_une_a_une():
    """TRENTE-SIX SOURCES À LA SUITE NE SE LISENT PAS, elles se survolent — et
    une liste qu'on survole ne sert plus à vérifier, qui est sa seule raison
    d'être. La nature est l'axe qui décide de ce qu'une source vaut : une
    autorité publique et un fournisseur ne s'opposent pas de la même façon à
    une contradiction.

    ET ON PEUT CHOISIR UNE NATURE ENTIÈRE. Avec trente-six entrées, filtrer une
    à une serait une commande sans usage : ce qu'on veut savoir, c'est « qu'est
    -ce qui vient d'une autorité ? »."""
    h = _sources_rendues()
    assert "<select" in h and "datalist" not in h
    natures = set(s["nature"] for s in F.SOURCES.values())
    groupes = re.findall(r'<optgroup label="([^"(]+)\(', h)
    assert {g.strip() for g in groupes} == natures, (groupes, natures)
    options = re.findall(r'<option value="([^"]*)"', h)
    assert options[0] == "__toutes", "le menu n'offre pas de les lire toutes"
    par_nature = [o for o in options if o.startswith("n:")]
    par_source = [o for o in options if o.startswith("s:")]
    assert len(par_nature) == len(natures), par_nature
    assert len(par_source) == len(F.SOURCES), (
        "%d options de source pour %d sources" % (len(par_source), len(F.SOURCES)))


def test_les_comptes_du_menu_viennent_du_MODULE_et_non_du_script():
    """Le module calcule déjà la couverture ; deux comptages divergeraient, et
    c'est le plus visible qui serait cru.

    LA RÈGLE ÉPROUVE LA DÉPENDANCE, PAS L'ACCORD. Écrite d'abord contre le seul
    corpus réel, elle constatait que la page affichait 36 pendant que le module
    en comptait 36 — et restait verte quand le 36 était écrit en dur dans le
    script. Un trente-septième source aurait laissé le menu faux. On rend donc
    un SECOND corpus, volontairement plus petit : si la page ne suit pas, elle
    ne tient pas ses comptes du module."""
    for sources in (None, _CORPUS_TEMOIN):
        h = _sources_rendues(sources)
        couv = _couverture_de(F.SOURCES if sources is None else sources)
        assert "%d sources, rangées par nature" % couv["total"] in h, h[:300]
        assert "Les %d sources, à la suite" % couv["total"] in h
        for nature, n in couv["par_nature"].items():
            assert "%s (%d)" % (nature, n) in h, (nature, n, h[:400])
        assert len(re.findall(r"<li data-src-cle=", h)) == couv["total"]


def test_les_trente_six_sources_restent_VISIBLES_au_chargement():
    """CE CHOIX DIFFÈRE DE CELUI DES CAS COMPARABLES, ET C'EST DÉLIBÉRÉ. Les
    cas se LISENT, un à la fois ; les sources se COMPTENT. « Obtenues, et
    comptées comme telles » : n'en montrer qu'une au chargement cacherait le
    registre, qui est ce que la section établit. Le menu sert à réduire, pas à
    révéler."""
    h = _sources_rendues()
    items = re.findall(r'<li data-src-cle="([^"]+)" data-src-nat="([^"]+)"([^>]*)>', h)
    assert len(items) == len(F.SOURCES)
    caches = [c for c, _n, attrs in items if "hidden" in attrs]
    assert not caches, (
        "%d sources sont masquées au chargement : le registre ne se compte "
        "plus" % len(caches))
    # Et chaque source porte sa nature, sinon le filtre par nature ne peut rien.
    for cle, nat, _a in items:
        assert F.SOURCES[cle]["nature"] == nat, (cle, nat)


def test_le_filtre_des_sources_masque_et_ne_redessine_pas():
    js = _src("ia-factory.js")
    bloc = js[js.index("function brancherSources("):]
    bloc = bloc[:bloc.index("\n  }")]
    assert "hidden" in bloc
    for interdit in ("innerHTML", "rendreSources("):
        assert interdit not in bloc, (
            "le filtre redessine (« %s ») au lieu de masquer" % interdit)
    for niveau in ('"n:"', '"s:"', "SRC_TOUTES"):
        assert niveau in bloc, (
            "le filtre ne traite pas le niveau %s" % niveau)


def test_le_menu_des_sources_est_REELLEMENT_branche():
    """Un menu qui ne fait rien promet un tri et ne le rend pas."""
    _appel_pose('$("iaf-sources").innerHTML', "brancherSources")
