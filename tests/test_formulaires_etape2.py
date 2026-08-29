"""LES TROIS FORMULAIRES DE L'ÉTAPE 2 — et le défaut qu'ils partageaient.

CE QUI A ÉTÉ TROUVÉ EN LES ÉPROUVANT. Aucun défaut de structure : pas
d'identifiant en double, chaque champ étiqueté, tous atteignables au clavier,
aucune erreur de script. Les quatre défauts étaient de COMPORTEMENT, et tous de
la même famille : l'application avalait une saisie qu'elle ne savait pas lire,
et ne le disait pas.

  1. LE PROFIL TECHNIQUE repartait sur sa valeur par défaut. Mesuré : « 75 % »
     tapé dans un champ noté « 0–1 » — la faute la plus naturelle qui soit —
     produisait une étude complète calculée sur 0,65, dont RIEN ne la
     distinguait d'une étude valide. Le lecteur croyait avoir chiffré son
     projet.

  2. LE COMPTE D'UNITÉS refusait « 6,0 », l'écriture française d'un entier :
     `int()` levait, l'exception ramenait le compte à zéro, et le résultat
     disparaissait sans un mot.

  3. RIEN NE DISTINGUAIT « pas rempli » de « illisible ». Un champ vide et un
     « abc » donnaient exactement le même écran.

  4. AUCUNE BORNE HAUTE. Deux cents unités par chaîne passaient sans un mot, là
     où le formulaire du profil signale déjà ses propres saisies
     invraisemblables.

LA RÈGLE QUI EN SORT, et que ces contrôles gardent : un champ vide n'est pas
une erreur — on ne dit rien. Une saisie qu'on ne sait pas lire EST une erreur,
et elle se nomme, à côté du champ concerné.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import app as A  # noqa: E402
import ingenierie_dc as I  # noqa: E402
from conftest import ADMIN_EMAIL, _assurer_admin  # noqa: E402

H = {"Origin": "http://localhost", "Referer": "http://localhost/x"}
BASE = {"puissance_it_kw": "1500", "pays": "FR",
        "refroidissement": "air_direct", "classe_ashrae": "A2"}


@pytest.fixture
def client():
    _assurer_admin()
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["user_email"] = ADMIN_EMAIL
    A._ip_rate._hits.clear()
    yield c
    A._ip_rate._hits.clear()


def _etude(client, **champs):
    A._ip_rate._hits.clear()
    return client.post("/api/datacenter/etude", headers=H,
                       json=dict(BASE, **champs))


# ═══════════════════════════════════════════════════════════════════════════
#  1. LE PROFIL TECHNIQUE — ce qui n'est pas lu se dit
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_une_saisie_illisible_n_est_plus_avalee_en_silence():
    """Elle tombait dans un `continue` muet : le champ disparaissait, l'étude
    repartait sur la valeur par défaut, et le résultat était IDENTIQUE à celui
    d'une saisie valide. Un résultat exact et trompeur est pire qu'une erreur :
    il est crédible."""
    rejets = []
    p = A._profil_datacenter(dict(BASE, taux_charge="75%"), rejets)
    assert "taux_charge" not in p, "la valeur illisible est entrée dans le calcul"
    assert len(rejets) == 1, rejets
    r = rejets[0]
    assert r["champ"] == "taux_charge"
    assert r["saisi"] == "75%"
    assert "Taux de charge" in r["label"], r["label"]
    assert "n'a pas pu être lu" in r["message"]


def test_SANS_CE_CONTRASTE_le_controle_precedent_ne_prouverait_rien():
    """Il faut qu'une saisie VALIDE ne produise aucun rejet, sinon « les rejets
    sont publiés » serait vrai d'un module qui les publierait toujours."""
    rejets = []
    p = A._profil_datacenter(dict(BASE, taux_charge="0.75"), rejets)
    assert p["taux_charge"] == 0.75
    assert rejets == []


def test_LE_POINT_QUI_DECIDE_la_virgule_decimale_francaise_est_ACCEPTEE():
    """C'est le clavier du client. La refuser ici pendant que le reste de
    l'application l'accepte serait un piège."""
    rejets = []
    p = A._profil_datacenter(dict(BASE, taux_charge="0,75", pue_cible="1,3"),
                             rejets)
    assert p["taux_charge"] == 0.75 and p["pue_cible"] == 1.3
    assert rejets == []


def test_un_champ_VIDE_ou_ABSENT_n_est_pas_un_rejet():
    """Ne pas remplir est un choix, et il se respecte sans commentaire. Le
    compter comme une faute noierait les vraies dans une liste de treize."""
    for vide in ("", None):
        rejets = []
        A._profil_datacenter(dict(BASE, taux_charge=vide), rejets)
        assert rejets == [], (vide, rejets)
    rejets = []
    A._profil_datacenter(dict(BASE), rejets)
    assert rejets == []


def test_l_etude_PUBLIE_ce_qu_elle_n_a_pas_lu(client):
    r = _etude(client, taux_charge="75%", cycles_concentration="quatre")
    assert r.status_code == 200
    j = r.get_json()
    assert j["ok"] is True
    assert len(j["rejets"]) == 2, j["rejets"]
    assert "n'ont pas été lus" in j["lecture_rejets"]
    assert "Taux de charge" in j["lecture_rejets"]
    # …et la lecture nomme la conséquence, pas seulement le fait.
    assert "valeurs par défaut" in j["lecture_rejets"]


def test_une_etude_propre_ne_publie_AUCUN_rejet(client):
    j = _etude(client, taux_charge="0,75").get_json()
    assert j["rejets"] == [] and j["lecture_rejets"] is None


def test_LE_POINT_QUI_DECIDE_une_puissance_illisible_ne_se_dit_pas_ABSENTE(client):
    """On ne répond pas « champ nécessaire » à quelqu'un qui vient de le
    remplir : il rechercherait un champ vide qu'il ne trouverait pas."""
    A._ip_rate._hits.clear()
    r = client.post("/api/datacenter/etude", headers=H,
                    json={"puissance_it_kw": "beaucoup"})
    assert r.status_code == 400
    j = r.get_json()
    assert j["error"] == "puissance_illisible", j
    assert "beaucoup" in j["message"]
    # …tandis qu'un champ réellement vide garde son message d'origine.
    A._ip_rate._hits.clear()
    j2 = client.post("/api/datacenter/etude", headers=H, json={}).get_json()
    assert j2["error"] == "puissance_absente"


# ═══════════════════════════════════════════════════════════════════════════
#  2. LE NIVEAU DE DISPONIBILITÉ — le compte d'unités
# ═══════════════════════════════════════════════════════════════════════════

def _red(v):
    return I.disponibilite("III", v, None)["redondance"]


def test_LE_POINT_QUI_DECIDE_un_entier_ecrit_a_la_francaise_est_ACCEPTE():
    """« 6,0 » et « 6.0 » sont des façons ordinaires d'écrire six. `int()`
    levait sur les deux, et le compte disparaissait sans un mot."""
    for v in ("6", "6.0", "6,0", " 6 "):
        r = _red(v)
        assert r and r.get("nature") == "calcule", (v, r)
        assert r["besoin"] == 6 and r["installees"] == 7, (v, r)


def test_LE_POINT_QUI_DECIDE_une_demi_unite_est_REFUSEE_avec_son_motif():
    """On n'arrondit pas en silence : arrondir choisirait à la place du
    concepteur, dans le sens qui l'arrange le moins une fois sur deux."""
    r = _red("2,5")
    assert r["nature"] == "refus" and r["erreur"] == "non_entier"
    assert "machines entières" in r["message"]
    assert r["saisi"] == "2,5"


def test_une_saisie_illisible_est_REFUSEE_avec_son_motif():
    r = _red("abc")
    assert r["nature"] == "refus" and r["erreur"] == "illisible"
    assert "abc" in r["message"]


def test_zero_ou_negatif_est_REFUSE_avec_son_motif():
    for v in ("0", "-3", "-1"):
        r = _red(v)
        assert r["nature"] == "refus" and r["erreur"] == "hors_domaine", v
        assert "au moins une unité" in r["message"]


def test_LE_POINT_QUI_DECIDE_un_champ_VIDE_ne_reproche_rien():
    """Ne pas remplir est un choix. Le distinguer d'une saisie fautive est tout
    l'objet de la correction : les deux donnaient le même écran."""
    for v in ("", "   ", None):
        assert _red(v) is None, v


def test_LE_POINT_QUI_DECIDE_un_compte_invraisemblable_est_SIGNALE_jamais_refuse():
    """Le calcul reste juste, et c'est au projet de savoir s'il est hors norme.
    Mais le taire laissait passer deux cents groupes froid par chaîne sans un
    mot, là où le formulaire du profil signale déjà les siennes."""
    r = _red("200")
    assert r["nature"] == "calcule", r
    assert r["installees"] == 201
    assert r["hors_plage"] and "dépasse ce qu'on observe" in r["hors_plage"]
    # …et un compte ordinaire ne porte aucun signal.
    assert _red("6")["hors_plage"] is None


def test_le_refus_ne_se_fait_PAS_passer_pour_un_resultat():
    """L'origine du schéma se posait sur tout objet rendu : un message d'erreur
    s'affichait alors sous un schéma « déduit du niveau », comme un compte."""
    r = _red("abc")
    assert "origine_schema" not in r, r
    assert "installees" not in r and "marge_pct" not in r
    # …tandis qu'un vrai compte la porte toujours.
    assert _red("6")["origine_schema"] == "deduit_du_niveau"


def test_sans_schema_ni_niveau_il_n_y_a_rien_a_compter():
    assert I.disponibilite(None, "6", None)["redondance"] is None


def test_le_compte_lui_meme_n_a_pas_bouge():
    """Les corrections portent sur la LECTURE de la saisie, pas sur
    l'arithmétique. Six unités en 2(N+1) en installent quatorze — deux chaînes
    de sept —, ni douze, ni sept."""
    r = I.disponibilite("IV", "6", "2(N+1)")["redondance"]
    assert r["besoin"] == 6 and r["par_chaine"] == 7
    assert r["chaines"] == 2 and r["installees"] == 14


# ── DEUX REFUS QUI NE SE DISAIENT PAS ─────────────────────────────────────
# Trouvés au relevé de l'existant, tous deux dans la même famille de défauts
# que ce fichier tient depuis le début : une saisie écartée sans un mot.

def test_un_schema_mal_orthographie_est_REFUSE_avec_son_motif():
    """LE DERNIER REFUS MUET DE `redondance`. Tout le reste de la fonction a
    été réécrit pour nommer ce qu'il refuse ; son PREMIER contrôle — le schéma
    inconnu — rendait encore `None` nu. « 2N+1 » pour « 2(N+1) », la faute de
    frappe la plus naturelle qui soit, devenait indiscernable d'un champ vide :
    le compte disparaissait, et rien ne disait pourquoi."""
    r = I.redondance("2N+1", "6")
    assert r is not None, "un schéma inconnu ne se distingue pas d'un champ vide"
    assert r["nature"] == "refus"
    assert r["erreur"] == "schema_inconnu"
    assert "2(N+1)" in r["message"], "et le message dit les schémas admis"


def test_un_schema_ABSENT_ne_reproche_toujours_rien():
    """La distinction que le refus ci-dessus ne doit pas casser : un champ vide
    n'est pas une erreur. C'est le cas nominal — la page laisse « déduit du
    niveau » par défaut."""
    for vide in ("", "   ", None):
        assert I.redondance(vide, "6") is None, repr(vide)


def test_un_refus_de_saisie_ne_fait_PAS_planter_la_redaction():
    """LE PLANTAGE LATENT. `prompts_piece` testait `if dispo["redondance"]:`
    puis lisait `r_["nom"]`. Un refus est vrai au sens booléen et ne porte pas
    cette clé : l'étude entière levait un KeyError sur une saisie d'unités non
    numérique — que la page envoie sans filtrer. La page se gardait du cas, le
    serveur non."""
    pr = I.prompts_piece({"puissance_it_kw": 1000}, "APD", "SPC-TIER",
                         {"tier": "III", "n_unites": "abc"})
    txt = pr["user"] if isinstance(pr, dict) else str(pr)
    assert "NON CALCULÉ" in txt, (
        "le refus est avalé : la pièce se rédigerait sur un dimensionnement "
        "dont personne ne saurait qu'il manque")
    assert "[à compléter]" in txt


def test_un_schema_inconnu_ne_fait_pas_planter_la_redaction_non_plus():
    """Le même chemin, par l'autre porte : c'est le schéma qui est refusé."""
    pr = I.prompts_piece({"puissance_it_kw": 1000}, "APD", "SPC-TIER",
                         {"tier": "III", "n_unites": "6",
                          "schema_redondance": "2N+1"})
    txt = pr["user"] if isinstance(pr, dict) else str(pr)
    assert "SPC-TIER" in txt or "disponibilité" in txt.lower()


# ── LA TABLE DES NIVEAUX, QUE RIEN N'ÉPROUVAIT ────────────────────────────
# Le relevé l'a constaté : aucune règle ne portait sur `NIVEAUX_TIER`, ni sur
# les familles d'infobulles qui en dérivent. Deux corrections viennent d'y être
# faites sur le référentiel Uptime ; sans règle, elles se perdraient à la
# première réécriture.

def test_le_niveau_III_distingue_le_backbone_de_la_distribution_critique():
    """CORRIGÉ SUR LE RÉFÉRENTIEL. Cette entrée disait « plusieurs chemins, un
    seul actif » — vrai du backbone électrique, FAUX de la distribution
    critique, qui exige deux chemins simultanément actifs de la sortie des
    onduleurs aux baies. C'est la nuance que les dossiers manquent le plus
    souvent, et elle se découvre en revue."""
    c = I.NIVEAUX_TIER["III"]["chemins"]
    bas = c.lower()
    # LA PREMIÈRE VERSION DE CETTE RÈGLE SE LAISSAIT TROMPER. Elle cherchait
    # trois mots n'importe où dans la phrase — « onduleur », « simultanément »,
    # « alterné ». Une entrée qui aurait rouvert par « plusieurs chemins, un
    # seul actif » AVANT de les employer les contenait tous, et passait : elle
    # aurait affirmé la règle générale fausse ET sa correction dans la même
    # phrase, ce qui est pire que l'erreur seule.
    #
    # Ce qui se vérifie ici, c'est la DISTINCTION : les deux côtés sont nommés,
    # chacun avec son exigence, et l'affirmation générale erronée est absente.
    assert "backbone" in bas, c
    assert "un seul a besoin de desservir" in bas, c
    assert "simultanément" in bas, c
    i_backbone, i_ond = bas.index("backbone"), bas.index("sortie des onduleurs")
    assert i_backbone < i_ond, (
        "les deux côtés ne sont pas distingués dans l'ordre : le chemin unique "
        "doit être rattaché au backbone AVANT que la sortie des onduleurs soit "
        "nommée, sinon la nuance ne se lit pas")
    assert "un seul actif" not in bas, (
        "l'affirmation générale erronée est de retour : « un seul actif » vaut "
        "pour le backbone, jamais pour la distribution critique")


def test_le_niveau_IV_exige_un_resultat_et_non_un_schema():
    """« N après toute panne » est un RÉSULTAT. Écrire « 2N » comme l'exigence
    transforme un référentiel fondé sur les résultats en liste de matériel."""
    cq = I.NIVEAUX_TIER["IV"]["consequence"]
    assert "2N" not in cq, cq
    assert "défaillance" in cq.lower()
    # Le schéma reste 2N : c'est ce que le CALCUL de quantités retient à
    # défaut, pas la définition du niveau. Les deux ne se confondent pas.
    assert I.NIVEAUX_TIER["IV"]["schema_type"] == "2N"


def test_le_niveau_IV_porte_le_compartimentage_et_le_froid_continu():
    """Deux exigences propres au niveau IV, absentes de la table d'origine."""
    cq = I.NIVEAUX_TIER["IV"]["consequence"].lower()
    assert "compartimentage" in cq
    assert "froid continu" in cq


def test_les_quatre_niveaux_gardent_la_meme_forme():
    """Une clé qui manquerait sur un seul niveau ferait un trou dans
    l'infobulle correspondante — et une infobulle trouée ne se voit pas."""
    champs = {"nom", "nature", "chemins", "maintenance", "defaut",
              "consequence", "schema_type"}
    for code in ("I", "II", "III", "IV"):
        assert champs <= set(I.NIVEAUX_TIER[code]), code
        assert I.NIVEAUX_TIER[code]["schema_type"] in I.REDONDANCES, code


def test_l_ordre_des_niveaux_couvre_exactement_la_table():
    d = I.disponibilite("III", "6", None)
    assert set(d["niveaux_ordre"]) == set(I.NIVEAUX_TIER)
    assert d["niveaux_ordre"] == ["I", "II", "III", "IV"]


def test_les_infobulles_des_niveaux_derivent_de_la_table():
    """« Tier III » se lit sur trois pages du dossier ; trois définitions du
    même sigle valent moins qu'une seule. L'infobulle doit REPRENDRE la table,
    pas la réécrire."""
    g = I.glossaire()["tier"]
    assert set(g) == set(I.NIVEAUX_TIER)
    for code, e in g.items():
        assert I.NIVEAUX_TIER[code]["chemins"] in e["aide"], code
        assert I.TIER_SOURCE in e["aide"], code
