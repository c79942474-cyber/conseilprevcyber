# -*- coding: utf-8 -*-
"""EMPREINTE DE L'IA — des règles qui mesurent le calcul, pas sa présence.

CE QUE CES RÈGLES GARDENT

  — LA SOURCE DE CHAQUE FACTEUR. Un facteur sans source est un nombre qui ne se
    réclame de personne. La garde d'import refuse le chargement ; ces règles
    vérifient qu'elle refuse VRAIMENT, en la faisant refuser.

  — CE QUE LE TEXTE DIT, ET CE QU'ON EN FAIT. Le coefficient 1,9 vient du
    règlement délégué (UE) 2023/807, lu verbatim. Le texte le destine au calcul
    d'ÉCONOMIES d'énergie ; l'employer sur une consommation est une
    transposition. Une règle exige que le module l'écrive — parce qu'un
    auditeur qui ouvre le texte le verra, et qu'il vaut mieux l'avoir dit.

  — L'AJUSTEMENT FIN NE S'ESTIME PAS. Cinq champs déclarés, ou rien. Une règle
    vérifie qu'un champ manquant fait refuser le calcul, et qu'on dit lequel.

  — LES TRAJECTOIRES COMPOSENT, ELLES N'ADDITIONNENT PAS. Une adoption de 40 %
    et une efficacité de 40 % ne s'annulent pas : c'est l'erreur d'arithmétique
    qui rend un scénario de sobriété faussement rassurant, et une règle la
    prend.

  — L'EAU N'EST PAS RECOPIÉE. L'EWIF a une définition, dans `eau_dc`. Une règle
    vérifie qu'aucune de ses valeurs ne réapparaît en dur ici — sans quoi le
    module créerait exactement le doublon qu'il existe pour supprimer.
"""
import importlib
import io
import os
import re
import sys
from datetime import date

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

# LE RÉFÉRENTIEL EAU N'EST PAS DANS LES DEUX DÉPÔTS, et ce fichier de règles
# est copié à l'identique comme le module qu'il garde. Les règles qui portent
# sur l'eau s'écartent donc là où `eau_dc` manque — en le DISANT, plutôt qu'en
# disparaissant silencieusement d'un des deux comptes.
try:
    import eau_dc as W                                              # noqa: E402
except ImportError:
    W = None
sans_eau = pytest.mark.skipif(W is None, reason="eau_dc absent de ce dépôt : "
                              "les règles d'eau ne s'y appliquent pas")
import empreinte_ia as E                                            # noqa: E402

SRC = io.open(os.path.join(ICI, "empreinte_ia.py"), encoding="utf-8").read()


# ═══════════════════════════════════════════════════════════════════════════
#  1. LES FACTEURS SE RÉCLAMENT DE QUELQU'UN
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cle", sorted(E.FACTEURS))
def test_chaque_facteur_porte_sa_source_sa_nature_et_ses_dates(cle):
    f = E.FACTEURS[cle]
    for champ in E.CHAMPS_FACTEUR:
        assert f.get(champ), "%s : pas de %s" % (cle, champ)
    assert f["nature"] in E.NATURES, (cle, f["nature"])
    assert len(f["source"]) >= 60, (
        "%s : une source de %d caractères ne désigne rien" % (cle, len(f["source"])))
    for d in ("releve_le", "revision_due"):
        date.fromisoformat(f[d])
    assert date.fromisoformat(f["revision_due"]) > date.fromisoformat(f["releve_le"])


def test_la_garde_d_import_REFUSE_vraiment_un_facteur_sans_source():
    """LE DÉFAUT QUE CETTE RÈGLE PREND : une garde écrite mais jamais éprouvée.
    On la fait donc refuser, sur quatre manquements distincts."""
    original = dict(E.FACTEURS)
    essais = [
        ("source vide", {"valeur": 1, "unite": "x", "nature": "releve", "source": "",
                         "releve_le": "2026-01-01", "revision_due": "2027-01-01"}),
        ("nature inventée", {"valeur": 1, "unite": "x", "nature": "au_pif", "source": "s" * 70,
                             "releve_le": "2026-01-01", "revision_due": "2027-01-01"}),
        ("réglementaire sans adresse", {"valeur": 1, "unite": "x",
                                        "nature": "texte_reglementaire", "source": "s" * 70,
                                        "url": "", "releve_le": "2026-01-01",
                                        "revision_due": "2027-01-01"}),
        ("date illisible", {"valeur": 1, "unite": "x", "nature": "releve", "source": "s" * 70,
                            "releve_le": "hier", "revision_due": "2027-01-01"}),
    ]
    try:
        for nom, faux in essais:
            E.FACTEURS["essai"] = faux
            with pytest.raises((RuntimeError, ValueError)):
                E._verifier()
            E.FACTEURS.pop("essai", None)
    finally:
        E.FACTEURS.clear()
        E.FACTEURS.update(original)
    E._verifier()          # la table réelle repasse la garde


def test_le_module_se_recharge_proprement():
    """Une garde qui refuserait la table réelle ne se verrait qu'en production."""
    importlib.reload(E)
    assert E.VERSION


# ═══════════════════════════════════════════════════════════════════════════
#  2. L'ÉNERGIE PRIMAIRE — le seul facteur réglementaire, et ses trois réserves
# ═══════════════════════════════════════════════════════════════════════════

def test_le_coefficient_d_energie_primaire_cite_le_texte_qui_le_fixe():
    f = E.FACTEURS["pef_electricite"]
    assert f["valeur"] == 1.9, f["valeur"]
    assert f["nature"] == "texte_reglementaire"
    assert "2023/807" in f["source"] and "32023R0807" in f["source"]
    assert "2012/27" in f["source"], "la source ne dit pas quel texte est amendé"
    assert "32023R0807" in f["url"], f["url"]


def test_les_TROIS_reserves_du_texte_sont_ecrites_et_pas_tues():
    """Le texte impose trois limites à l'emploi du 1,9. Les taire donnerait un
    chiffre plus net et un livrable indéfendable.

    ET CHAQUE RÉSERVE EST CHERCHÉE DANS LE CHAMP QUI LA PORTE, pas dans le
    fichier. La première version concaténait toute la source : une mutation qui
    retirait « transposition » de la réserve SERVIE a survécu, le mot restant
    dans un commentaire. Une règle qui accepte n'importe quel endroit du
    fichier ne garde pas ce qui est servi — elle garde qu'on y a pensé un
    jour."""
    f = E.FACTEURS["pef_electricite"]
    reserve = f["reserve"].lower()
    assert "économies" in reserve, "la réserve ne dit pas que le texte vise des économies"
    assert "transposition" in reserve, "la réserve ne dit pas que l'emploi est transposé"
    assert "défaut" in reserve, "la réserve ne dit pas que le coefficient est un défaut"
    assert "remplac" in reserve, "la réserve ne dit pas qu'il peut être remplacé"
    assert "2023/1791" in f["point_ouvert"], "le point ouvert sur la refonte n'est pas porté"
    assert "vérifié" in f["point_ouvert"] or "verifie" in f["point_ouvert"]


def test_la_revision_est_celle_que_le_texte_impose():
    """« By 25 December 2022 and every four years thereafter » : la première
    échéance postérieure au relevé tombe le 25 décembre 2026."""
    f = E.FACTEURS["pef_electricite"]
    d = date.fromisoformat(f["revision_due"])
    assert (d.month, d.day) == (12, 25), d
    assert (d.year - 2022) % 4 == 0, d


def test_l_etat_signale_le_facteur_QUAND_sa_revision_est_due():
    """Une date de révision qui ne déclenche rien est une décoration."""
    veille = date.fromisoformat(E.FACTEURS["pef_electricite"]["revision_due"])
    assert not [x for x in E.etat(veille.replace(year=veille.year - 1))["revision_due"]
                if x["cle"] == "pef_electricite"]
    assert [x for x in E.etat(veille)["revision_due"] if x["cle"] == "pef_electricite"]


@pytest.mark.parametrize("kwh", [0.0, 1.0, 137.5, 1e6])
def test_l_energie_primaire_est_RECALCULEE_et_tombe_juste(kwh):
    assert E.energie_primaire_mj(kwh) == pytest.approx(kwh * 1.9 * 3.6)
    assert E.energie_primaire_mj(kwh, coefficient=2.5) == pytest.approx(kwh * 2.5 * 3.6)


def test_le_coefficient_du_client_REMPLACE_celui_du_defaut():
    """Le texte laisse cette latitude aux États membres ; la refuser ferait
    servir un défaut là où une valeur justifiée existe."""
    assert E.energie_primaire_mj(100, 2.1) != E.energie_primaire_mj(100)


# ═══════════════════════════════════════════════════════════════════════════
#  3. L'EAU N'EST PAS RECOPIÉE
# ═══════════════════════════════════════════════════════════════════════════

@sans_eau
def test_l_EWIF_n_est_pas_recopie_mais_DEMANDE_a_eau_dc(monkeypatch):
    """LE DOUBLON QUE CETTE RÈGLE FERME, ET POURQUOI ELLE EXÉCUTE.

    Rendre ce module autonome en y recopiant l'EWIF créerait deux définitions
    du même facteur — exactement ce qu'il existe pour supprimer.

    LA PREMIÈRE VERSION DE CETTE RÈGLE CHERCHAIT LES VALEURS DANS LA SOURCE, et
    elle était intenable : l'EWIF européen par défaut vaut 1,0, un nombre qui
    apparaît dix fois dans de l'arithmétique ordinaire. Elle aurait été rouge
    pour une raison sans rapport avec ce qu'elle garde. On mesure donc le
    COMPORTEMENT : on remplace la fonction d'eau_dc par un témoin, et on exige
    que la valeur servie vienne de lui."""
    temoin = {"valeur": 7.77, "mix": "témoin", "note": "", "national": True,
              "nature": "temoin"}
    monkeypatch.setattr(W, "ewif_pays", lambda code: temoin)
    r = E.eau_m3(1000.0, "FR")
    assert r["ewif"] == 7.77, (
        "l'eau ne vient pas d'eau_dc : une valeur est recopiée dans le module")
    assert r["m3"] == pytest.approx(1000.0 * 7.77 / 1000.0)
    # Et aucune table d'EWIF propre au module.
    assert not re.search(r"^\s*EWIF", SRC, re.M), (
        "empreinte_ia définit sa propre table d'EWIF")


@sans_eau
def test_l_eau_est_LUE_dans_eau_dc_et_suit_son_referentiel():
    r = E.eau_m3(1000.0, "FR")
    assert r["ewif"] == W.ewif_pays("FR")["valeur"]
    assert r["m3"] == pytest.approx(1000.0 * W.ewif_pays("FR")["valeur"] / 1000.0)
    assert r["ewif_national"] is True
    assert W.EWIF_INCERTITUDE in r["incertitude"]


@sans_eau
def test_un_pays_sans_EWIF_national_le_DIT_au_lieu_de_paraitre_documente():
    r = E.eau_m3(1000.0, "XX")
    assert r["ewif_national"] is False
    assert r["nature"] == "defaut_ue"


def test_sans_referentiel_eau_l_indicateur_est_INDISPONIBLE_et_dit_pourquoi(monkeypatch):
    """LE POINT QUI DÉCIDE, POUR UN MODULE PARTAGÉ ENTRE DEUX DÉPÔTS : là où
    `eau_dc` n'est pas présent, l'eau ne doit pas être approchée en silence."""
    monkeypatch.setattr(E, "_eau_dc", lambda: None)
    r = E.eau_m3(1000.0, "FR")
    assert r["nature"] == "indisponible" and r["m3"] is None
    assert "eau_dc" in r["motif"]


# ═══════════════════════════════════════════════════════════════════════════
#  4. LES TROIS MÉTHODES — chacune ajoute un périmètre, et l'écart se voit
# ═══════════════════════════════════════════════════════════════════════════

def test_chaque_methode_AJOUTE_un_perimetre_a_la_precedente():
    """L'invariant qui fait tenir l'analyse d'écarts : A ⊂ B ⊂ C. Si B passait
    sous A, l'écart publié ne mesurerait plus un périmètre mais une erreur."""
    for modele in ("claude", "mistral-large", "mistral-embed", "inconnu-xyz"):
        r = E.inference(modele, 5000, 380.0, 380.0)
        assert r["wh_a"] <= r["wh_b"] <= r["wh_c"], (modele, r)
        assert r["g_b_min"] <= r["g_b"] <= r["g_b_max"], modele
        assert r["g_c_min"] <= r["g_c"] <= r["g_c_max"], modele


def test_l_inference_est_RECALCULEE_a_la_main_et_tombe_juste():
    bas, central, haut = E.WH_1K_JETONS["grand"]
    k, pue = 5000 / 1000.0, 1.20
    heb = E.FACTEURS["hebergement_wh_req"]["valeur"]
    fab = 1 + E.FACTEURS["fabrication_pct"]["valeur"] / 100.0
    r = E.inference("claude", 5000, 380.0, 380.0)
    assert r["wh_a"] == pytest.approx(central * k)
    assert r["wh_b"] == pytest.approx(central * k * pue)
    assert r["wh_c"] == pytest.approx(central * k * pue + heb)
    assert r["g_c"] == pytest.approx(
        (central * k * pue / 1000.0 * 380.0) * fab + heb / 1000.0 * 380.0)
    assert r["mj_c"] == pytest.approx(E.energie_primaire_mj(r["wh_c"] / 1000.0))
    assert r["g_b_max"] / r["g_b_min"] == pytest.approx(haut / bas)


def test_un_modele_inconnu_recoit_le_milieu_de_plage_ET_LE_DIT():
    """Un parc de modèles non profilés se chiffrerait sans que rien ne le
    signale : le repli doit remonter jusqu'à l'affichage."""
    r = E.inference("un-modele-jamais-vu", 1000, 380.0, 380.0)
    assert r["profil_connu"] is False and r["classe"] == "moyen"
    assert E.inference("claude", 1000, 380.0, 380.0)["profil_connu"] is True


def test_les_indicateurs_derives_ne_viennent_QUE_du_perimetre_le_plus_large():
    """Donner une eau ou une énergie primaire à un périmètre qui ne compte ni
    le matériel ni l'hébergement serait annoncer un cycle de vie sur un calcul
    d'usage."""
    r = E.inference("claude", 1000, 380.0, 380.0)
    assert r["mj_c"] == pytest.approx(E.energie_primaire_mj(r["wh_c"] / 1000.0))
    assert r["mj_c"] > E.energie_primaire_mj(r["wh_b"] / 1000.0)


# ═══════════════════════════════════════════════════════════════════════════
#  5. L'AJUSTEMENT FIN — déclaré, ou rien
# ═══════════════════════════════════════════════════════════════════════════

COMPLET = {"heures_accelerateur": 512, "nombre_accelerateurs": 8,
           "puissance_w": 700, "pue": 1.2, "amorti_mois": 24}


@pytest.mark.parametrize("absent", sorted(COMPLET))
def test_un_champ_manquant_fait_REFUSER_le_calcul_et_on_dit_lequel(absent):
    d = {k: v for k, v in COMPLET.items() if k != absent}
    r = E.ajustement_fin(d, 380.0)
    assert r["nature"] == "incomplet" and r["wh"] is None
    assert absent in r["manquants"], r["manquants"]


def test_l_ajustement_fin_est_RECALCULE_et_tombe_juste():
    r = E.ajustement_fin(COMPLET, 380.0)
    attendu_wh = 512 * 8 * 700 * 1.2
    assert r["wh"] == pytest.approx(attendu_wh)
    assert r["g_co2"] == pytest.approx(attendu_wh / 1000.0 * 380.0)
    assert r["mj"] == pytest.approx(E.energie_primaire_mj(attendu_wh / 1000.0))


def test_la_part_mensuelle_ne_va_JAMAIS_sans_le_total():
    """Un entraînement est un coût unique ; l'amortir suppose une durée de
    service, qui est une décision. Les deux se lisent ensemble, ou l'un des
    deux ment."""
    r = E.ajustement_fin(COMPLET, 380.0)
    assert r["wh_mois"] * r["amorti_mois"] == pytest.approx(r["wh"])
    assert r["g_co2_mois"] * r["amorti_mois"] == pytest.approx(r["g_co2"])
    assert r["formule"] and "PUE" in r["formule"]


def test_une_declaration_absurde_est_refusee_et_pas_chiffree():
    for faux in ({"pue": 0}, {"heures_accelerateur": -3}, {"amorti_mois": 0}):
        d = dict(COMPLET); d.update(faux)
        assert E.ajustement_fin(d, 380.0)["nature"] == "incomplet", faux


# ═══════════════════════════════════════════════════════════════════════════
#  6. LES TRAJECTOIRES — elles composent, elles n'additionnent pas
# ═══════════════════════════════════════════════════════════════════════════

def test_adoption_et_efficacite_COMPOSENT_et_ne_s_annulent_pas():
    """L'ERREUR QUE CETTE RÈGLE PREND, ET QUI REND UN SCÉNARIO DE SOBRIÉTÉ
    FAUSSEMENT RASSURANT : +40 % d'usages et −40 % d'intensité ne se
    neutralisent pas. 1,4 × 0,6 = 0,84, pas 1."""
    t = E.trajectoire(100.0, 40.0, 40.0, 2026, 2030)
    assert t["facteur_annuel"] == pytest.approx(1.4 * 0.6)
    assert t["facteur_annuel"] != pytest.approx(1.0)
    assert t["points"][-1]["valeur"] == pytest.approx(100.0 * (1.4 * 0.6) ** 4)


def test_la_projection_part_de_la_base_et_couvre_toutes_les_annees():
    t = E.trajectoire(1000.0, 15.0, 5.0, 2026, 2030)
    assert [p["annee"] for p in t["points"]] == [2026, 2027, 2028, 2029, 2030]
    assert t["points"][0]["valeur"] == 1000.0, "la première année n'est pas la base"
    assert t["multiple"] == pytest.approx(t["points"][-1]["valeur"] / 1000.0)


def test_un_horizon_ou_une_efficacite_absurdes_sont_refuses():
    assert E.trajectoire(100.0, 10.0, 10.0, 2030, 2026)["nature"] == "indisponible"
    assert E.trajectoire(100.0, 10.0, 100.0, 2026, 2030)["nature"] == "indisponible"
    assert E.trajectoire(None, 10.0, 10.0, 2026, 2030)["nature"] == "indisponible"


def test_les_CINQ_reperes_couvrent_les_deux_axes_et_different_deux_a_deux():
    assert len(E.SCENARIOS) == 5
    couples = {(s["adoption"], s["efficacite"]) for s in E.SCENARIOS}
    assert len(couples) == 5, "deux repères ont les mêmes taux"
    assert len({s["adoption"] for s in E.SCENARIOS}) >= 3
    assert len({s["efficacite"] for s in E.SCENARIOS}) >= 3
    mult = [E.trajectoire(100.0, s["adoption"], s["efficacite"], 2026, 2030)["multiple"]
            for s in E.SCENARIOS]
    assert min(mult) < 1.0 < max(mult), (
        "aucun repère ne descend sous la base : l'éventail ne montre rien")


def test_les_reperes_DISENT_qu_ils_sont_des_parametres_du_cabinet():
    """Les publier comme un référentiel serait leur prêter une autorité qu'ils
    n'ont pas — la source de l'infographie n'est pas connue ici."""
    s = E.SCENARIOS_SOURCE.lower()
    assert "cabinet" in s and ("pas un référentiel" in s or "pas un referentiel" in s)


def test_le_levier_du_MIX_ELECTRIQUE_dit_ce_qu_il_ne_change_pas():
    """La confusion la plus commune : déplacer des émissions n'économise pas un
    kilowattheure. Un livrable qui la laisse passer promet une sobriété qui
    n'existe pas."""
    mix = [l for l in E.LEVIERS_2030 if l["cle"] == "mix_electrique"][0]
    assert mix["agit_sur"] == "ges"
    assert "ne change" in mix["porte"].lower()
    assert len({l["cle"] for l in E.LEVIERS_2030}) == 4


# ═══════════════════════════════════════════════════════════════════════════
#  7. LA COUVERTURE ET CE QUI MANQUE
# ═══════════════════════════════════════════════════════════════════════════

def test_l_indicateur_ABSENT_est_declare_avec_ce_qu_il_faudrait_pour_le_combler():
    """Un indicateur retiré sans le dire se lit comme un indicateur jugé nul."""
    absents = E.indicateurs_absents()
    assert [i["cle"] for i in absents] == ["ressources"]
    assert len(absents[0]["manque"]) >= 80
    assert {i["cle"] for i in E.indicateurs_servis()} == {
        "electricite", "ges", "eau", "energie_primaire"}


def test_la_couverture_compte_le_declare_et_NOMME_le_manquant():
    parc = [{"nom": "A", "volume_sortie_mois": 1000},
            {"nom": "B"},
            {"nom": "C", "volume_sortie_mois": 20, "ajustement_fin": COMPLET},
            {"nom": "D", "volume_sortie_mois": 5, "ajustement_fin": {"pue": 1.2}}]
    c = E.couverture(parc)
    assert c["systemes"] == 4 and c["volume_declare"] == 3
    assert c["volume_manquant"] == ["B"]
    assert c["ajustement_declare"] == 1 and c["ajustement_incomplet"] == ["D"]
    assert c["part"] == pytest.approx(0.75)
    assert E.couverture([])["part"] == 0.0


def test_une_valeur_substituee_par_l_environnement_est_SIGNALEE(monkeypatch):
    """Sans cela, la page citerait un règlement européen pour une valeur qui ne
    vient plus de lui."""
    assert E.etat()["substitues"] == []
    monkeypatch.setenv("EMPREINTE_PEF_ELEC", "2.5")
    importlib.reload(E)
    try:
        assert E.FACTEURS["pef_electricite"]["valeur"] == 2.5
        assert "pef_electricite" in E.etat()["substitues"]
    finally:
        monkeypatch.delenv("EMPREINTE_PEF_ELEC", raising=False)
        importlib.reload(E)
    assert E.FACTEURS["pef_electricite"]["valeur"] == 1.9


def test_le_module_N_OUVRE_AUCUNE_SOCKET():
    """Un module de calcul qui interroge le réseau ne se teste pas, il se
    moque. Les intensités lui sont PASSÉES.

    LA PREMIÈRE VERSION INTERDISAIT LA CHAÎNE « https:// », et elle tombait sur
    l'adresse du règlement européen citée par le facteur d'énergie primaire —
    une CITATION, pas un appel. Une règle qui interdit un texte au lieu d'un
    comportement finit toujours par prendre la source pour le crime : on mesure
    donc les imports et les appels."""
    for module in ("requests", "urllib", "http", "socket", "httpx"):
        assert not re.search(r"^\s*(?:import|from)\s+%s\b" % module, SRC, re.M), (
            "empreinte_ia importe %s" % module)
    for appel in ("urlopen", "urlretrieve", "get", "post"):
        assert not re.search(r"\brequests\.%s\(|\b%s\(\s*[\"']https?://" % (appel, appel),
                             SRC), appel
    # Et la preuve par l'exécution : le calcul tombe juste sans réseau.
    assert E.inference("claude", 1000, 380.0, 380.0)["wh_c"] > 0


def test_les_repere_de_puissance_portent_leur_propre_valeur():
    """Nommer un accélérateur par une marque supposerait une fiche technique
    qu'on n'a pas. Le nom EST la puissance déclarée."""
    for nom, w in E.PUISSANCE_ACCELERATEUR.items():
        assert float(nom) == w
    assert "ne désignent aucun modèle" in E.PUISSANCE_SOURCE



# ═══════════════════════════════════════════════════════════════════════════
#  8. LE PARC — la couverture d'abord, et le périmètre incomplet nommé
# ═══════════════════════════════════════════════════════════════════════════

PARC = [
    {"nom": "Assistant support", "modele": "claude", "unite_facturation": "jetons",
     "volume_sortie_mois": "12 000 000"},
    {"nom": "Recherche interne", "modele": "mistral", "unite_facturation": "requetes",
     "volume_sortie_mois": "40000"},
    {"nom": "Vision qualité", "modele": "inconnu"},
    {"nom": "Copilote métier", "modele": "mistral-large", "unite_facturation": "jetons",
     "volume_sortie_mois": "3000000", "ajustement_fin": COMPLET},
]


def test_un_volume_ABSENT_ne_devient_jamais_zero():
    """LE DÉFAUT QUE CETTE RÈGLE PREND : un parc à moitié déclaré qui paraît
    deux fois plus sobre qu'il n'est. Une ligne sans volume ressort « non
    instruite », jamais à zéro kilowattheure."""
    m = E.mensuel({"nom": "X", "modele": "claude"}, 60.0, 380.0)
    assert m["nature"] == "non_instruit" and m["wh"] is None
    assert "aucun volume" in m["motif"]
    for faux in ("", None, "à venir", "-3"):
        assert E.mensuel({"modele": "claude", "volume_sortie_mois": faux},
                         60.0, 380.0)["nature"] == "non_instruit", faux


def test_un_volume_ecrit_a_la_francaise_est_LU():
    """« 12 000 000 » avec des espaces fines est ce qu'un client recopie de sa
    console. Le refuser ferait ressortir la ligne comme non instruite — un
    manque qui n'existe pas."""
    for ecriture in ("12000000", "12 000 000", "12 000 000", "12000000,0"):
        m = E.mensuel({"modele": "claude", "volume_sortie_mois": ecriture}, 60.0, 380.0)
        assert m["nature"] == "declare" and m["jetons"] == 12000000.0, ecriture


def test_le_terme_d_HEBERGEMENT_n_est_pas_derive_d_un_volume_de_jetons():
    """LE POINT LE PLUS DÉLICAT DE L'AGRÉGATION, ET IL EST NOMMÉ.

    L'hébergement vaut 0,15 Wh PAR REQUÊTE. Un parc facturé au jeton déclare
    des jetons : le nombre d'appels est inconnu, et l'inventer — en supposant
    une longueur de réponse moyenne — ferait entrer un chiffre que personne n'a
    déclaré dans un livrable vendu. Le drapeau dit que le périmètre est
    incomplet ; la liste nomme les systèmes concernés."""
    jetons = E.mensuel(PARC[0], 60.0, 380.0)
    requetes = E.mensuel(PARC[1], 60.0, 380.0)
    assert jetons["hebergement_derive"] is False
    assert requetes["hebergement_derive"] is True
    # Au jeton, la méthode C n'ajoute que la majoration de fabrication.
    fab = 1 + E.FACTEURS["fabrication_pct"]["valeur"] / 100.0
    assert jetons["wh"] == pytest.approx(jetons["wh_b"])
    assert jetons["g_co2"] == pytest.approx(
        jetons["wh_b"] / 1000.0 * 60.0 * fab)
    # À la requête, il l'ajoute vraiment.
    heb = E.FACTEURS["hebergement_wh_req"]["valeur"] * 40000
    assert requetes["wh"] == pytest.approx(requetes["wh_b"] + heb)


def test_le_parc_NOMME_les_systemes_au_perimetre_incomplet():
    r = E.parc(PARC, 60.0, 380.0, pays_eau="FR", depuis=2026, horizon=2030)
    assert r["hebergement_non_derivable"] == ["Assistant support", "Copilote métier"]
    assert "Recherche interne" not in r["hebergement_non_derivable"]


def test_la_COUVERTURE_precede_les_totaux_et_nomme_le_manquant():
    r = E.parc(PARC, 60.0, 380.0)
    assert list(r)[0] == "couverture", "la couverture n'est pas la première clé"
    assert r["couverture"]["volume_declare"] == 3
    assert r["couverture"]["volume_manquant"] == ["Vision qualité"]


def test_l_ajustement_fin_est_rendu_SEPAREMENT_de_l_inference():
    """Les mêler ferait disparaître le terme qui, sur un parc qui affine ses
    modèles, est souvent le plus lourd."""
    r = E.parc(PARC, 60.0, 380.0)
    assert r["ajustement_fin_mois"]["wh"] > 0
    # LE TOTAL D'INFÉRENCE NE CONTIENT QUE DE L'INFÉRENCE, et c'est cela qu'on
    # mesure. La première version comparait le total à la somme des deux postes
    # — une égalité qui reste vraie si l'ajustement fin a DÉJÀ été versé dans
    # l'inférence : la mutation qui les fondait a survécu, en comptant deux
    # fois le terme le plus lourd. On recompose donc l'inférence ligne à ligne.
    somme_lignes = sum(l["inference"]["wh"] for l in r["lignes"]
                       if l["inference"]["nature"] == "declare")
    assert r["inference_mois"]["wh"] == pytest.approx(somme_lignes), (
        "le total d'inférence contient autre chose que de l'inférence")
    assert r["total_mois"]["wh"] == pytest.approx(
        r["inference_mois"]["wh"] + r["ajustement_fin_mois"]["wh"])
    assert r["total_mois"]["g_co2"] == pytest.approx(
        r["inference_mois"]["g_co2"] + r["ajustement_fin_mois"]["g_co2"])
    # Un seul système déclare un ajustement fin, et c'est le sien qui pèse.
    seul = E.ajustement_fin(COMPLET, 60.0)
    assert r["ajustement_fin_mois"]["wh"] == pytest.approx(seul["wh_mois"])


def test_la_base_des_trajectoires_est_LE_TOTAL_annualise():
    """Projeter la seule inférence ferait décrire une trajectoire à un parc
    dont on aurait retiré le terme dominant."""
    r = E.parc(PARC, 60.0, 380.0, depuis=2026, horizon=2030)
    assert r["base_annuelle_kg"] == pytest.approx(
        r["total_mois"]["g_co2"] * 12.0 / 1000.0)
    assert len(r["trajectoires"]) == 5
    assert all(t["points"][0]["valeur"] == pytest.approx(r["base_annuelle_kg"])
               for t in r["trajectoires"])


def test_un_parc_vide_ne_rend_pas_un_total_rassurant():
    r = E.parc([], 60.0, 380.0)
    assert r["couverture"]["systemes"] == 0 and r["couverture"]["part"] == 0.0
    assert r["total_mois"]["wh"] == 0.0
    assert r["lignes"] == []
