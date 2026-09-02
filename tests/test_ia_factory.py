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
