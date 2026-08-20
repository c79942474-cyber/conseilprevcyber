"""CE QUE LA MAÎTRISE D'ŒUVRE ENGAGE — et que le montant des honoraires tait.

CE QUI MANQUAIT. Le module chiffrait ce que la maîtrise d'œuvre COÛTE. Il ne
disait rien de ce qu'elle GARANTIT — or c'est cet engagement qui transforme un
honoraire en risque, des deux côtés. Deux offres au même montant ne portent pas
la même promesse si leurs taux de tolérance diffèrent, et rien ne le montrait.

D'OÙ VIENNENT CES RÈGLES. Du modèle officiel de marché public de maîtrise
d'œuvre pour la réutilisation ou réhabilitation d'ouvrages de bâtiment (CCAP,
2 novembre 2012), qui applique le décret n° 93-1268 du 29 novembre 1993. Les
formules sont reprises telles qu'elles y sont écrites.

LE POINT QUI DÉCIDE, ET IL SE CALCULE ICI. Le plafond de pénalité de l'article
30.II vaut 15 % de la rémunération des éléments POSTÉRIEURS à l'attribution des
marchés. Ce module connaît déjà cette rémunération, phase par phase : le
plafond se déduit, il ne se demande pas. Sans lui, une pénalité calculée au
taux du marché peut dépasser d'un facteur trente ce que la loi autorise —
mesuré ici : 9,6 M€ bruts contre 0,315 M€ de plafond.

AUCUN TAUX N'EST PROPOSÉ. Le modèle officiel les laisse en blanc : taux de
tolérance, taux de pénalité et taux de rémunération se négocient. Un taux
suggéré par un outil devient le taux du marché sans que personne ne l'ait
négocié.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import moe_dc as M


def _res(bas=38.0, haut=42.0, **kw):
    r = M.honoraires_directs([bas, haut], **kw)
    assert r.get("ok"), r
    return r


def test_les_deux_engagements_sont_DISTINCTS_et_ne_declenchent_pas_la_meme_chose():
    """LE MALENTENDU LE PLUS COÛTEUX SUR CE SUJET. Il y a DEUX engagements
    successifs, pas un : sur le coût prévisionnel après l'APD, puis sur le coût
    de réalisation après la passation. Le premier ne peut donner lieu à AUCUNE
    pénalité financière ; le second, si."""
    cles = [e["cle"] for e in M.ENGAGEMENTS]
    assert cles == ["cout_previsionnel", "cout_realisation"], cles
    prev = next(e for e in M.ENGAGEMENTS if e["cle"] == "cout_previsionnel")
    real = next(e for e in M.ENGAGEMENTS if e["cle"] == "cout_realisation")
    assert prev["penalite"] is False
    assert real["penalite"] is True
    assert "AUCUNE PÉNALITÉ" in prev["depassement"]
    assert "30.I" in prev["depassement"], "la reprise gratuite n'est pas sourcée"
    assert "30.II" in real["depassement"], "le plafond n'est pas sourcé"


def test_le_seuil_de_tolerance_SE_REPRODUIT_par_sa_formule():
    """seuil = coût × (1 + taux). Écrite dans le modèle, elle doit se
    recalculer à la main sans surprise."""
    e = M.engagement(40.0, 5.0)
    assert e["ok"]
    assert e["seuil_meur"] == 42.0, e["seuil_meur"]
    assert "(1 + taux de tolérance)" in e["formule"]


def test_LE_POINT_QUI_DECIDE_la_penalite_est_PLAFONNEE_a_quinze_pour_cent():
    """Article 30.II. Sans ce plafond, une pénalité au taux du marché dépasse
    de très loin ce que la loi autorise — et l'écart n'est pas marginal."""
    r = _res()
    p = M.plafond_penalite(r)
    assert p["plafond_meur"] is not None
    # LA TOLÉRANCE RESPECTE L'ARRONDI DU MODULE, qui publie au millier
    # d'euros — c'est un choix documenté, pas une dérive. Exiger 1e-6 faisait
    # tomber le contrôle sur la précision d'affichage, pas sur le calcul.
    assert abs(p["plafond_meur"] - round(p["assiette_meur"] * 0.15, 3)) < 1e-9
    assert p["taux"] == 0.15

    e = M.engagement(40.0, 5.0, cout_reference_meur=90.0,
                     taux_penalite_pct=20.0, resultat=r)
    pen = e["penalite"]
    assert pen["plafonnee"] is True
    assert pen["retenue_meur"] == p["plafond_meur"], (pen, p)
    # L'ÉCART EST LE POINT : la brute vaut plus de vingt fois le plafond.
    assert pen["brute_meur"] > 10 * pen["retenue_meur"], (
        "le cas d'essai ne montre plus l'utilité du plafond : %s contre %s"
        % (pen["brute_meur"], pen["retenue_meur"]))


def test_SANS_DEPASSEMENT_franc_le_controle_precedent_ne_prouverait_rien():
    """Une pénalité inférieure au plafond ne doit PAS être plafonnée, sinon le
    contrôle ci-dessus passerait quel que soit le code."""
    r = _res()
    e = M.engagement(40.0, 5.0, cout_reference_meur=44.0,
                     taux_penalite_pct=10.0, resultat=r)
    assert e["depasse"] is True
    assert e["penalite"]["plafonnee"] is False
    assert e["penalite"]["retenue_meur"] == e["penalite"]["brute_meur"]


def test_l_assiette_du_plafond_est_VIDE_quand_le_chantier_n_est_pas_suivi():
    """Le plafond porte sur les éléments POSTÉRIEURS à l'attribution. Une
    maîtrise d'œuvre qui s'arrête au dossier de consultation n'en a aucun :
    l'assiette est vide, et cela se dit plutôt que de valoir zéro en silence."""
    r = _res(phases=["aps", "apd", "pro"])
    p = M.plafond_penalite(r)
    assert p["plafond_meur"] is None
    assert "ne suit pas le chantier" in p["dit"]


def test_le_module_REFUSE_de_proposer_un_taux():
    """Le modèle officiel les laisse en blanc : ils se négocient. Un taux
    suggéré par un outil devient le taux du marché sans négociation."""
    e = M.engagement(40.0, None)
    assert e["ok"] is False and e["erreur"] == "taux_absent"
    assert "se négocie" in e["message"]
    # …et aucun taux n'est écrit dans la source déclarée.
    assert "laissés en blanc" in M.SOURCE_ENGAGEMENT["note"] \
        or "laissés en blanc" in M.SOURCE_ENGAGEMENT["note"].replace("y sont ", "")


def test_un_depassement_du_cout_PREVISIONNEL_ne_coute_pas_d_argent():
    """Il se règle en études : reprise partielle sans rémunération
    supplémentaire. Présenter une pénalité à ce stade serait un contresens."""
    e = M.engagement(40.0, 3.0, cout_reference_meur=50.0,
                     taux_penalite_pct=10.0, resultat=_res(),
                     cle="cout_previsionnel")
    assert e["depasse"] is True
    assert e["penalite"] is None
    assert "pas en argent" in e["lecture"] or "aucune pénalité" in e["lecture"].lower()


def test_LE_POINT_QUI_DECIDE_ce_que_le_VISA_n_est_PAS_est_ECRIT():
    """Acheter un VISA n'est pas acheter un contrôle. Un maître d'ouvrage qui
    l'ignore croit avoir transféré un risque qu'il porte encore."""
    V = M.LIMITE_VISA
    assert "NI LE CONTRÔLE" in V["n_est_pas"]
    assert "VÉRIFICATION INTÉGRALE" in V["n_est_pas"]
    assert "NE DÉGAGE PAS" in V["n_est_pas"]
    assert "homme de l'art" in V["n_est_pas"].lower()
    assert "1994" in V["source"] and "5 bis" in V["est"]


def test_la_correspondance_avec_le_MODELE_OFFICIEL_est_publiee():
    """Sept éléments au modèle, cinq phases ici : trois se retrouvent dans une
    seule. Ce n'est pas une approximation cachée — le barème relevé ne publie
    pas leur partage — mais le lecteur qui a le modèle sous les yeux doit
    pouvoir retrouver ses lignes."""
    c = M.correspondance_modele()
    assert len(c["elements"]) == 7, len(c["elements"])
    codes = [e["code"] for e in c["elements"]]
    for attendu in ("APS", "APD", "PRO", "ACT", "EXE/VISA", "DET", "AOR"):
        assert attendu in codes, attendu
    # Les trois derniers tombent bien dans une seule phase, et c'est DIT.
    exe = [g for g in c["regroupements"] if g["phase"] == "exe"][0]
    assert len(exe["elements"]) == 3
    assert "n'en publie pas le partage" in exe["dit"], exe["dit"]
    # …et la réserve dit que le modèle porte la réhabilitation, pas le neuf.
    assert "RÉHABILITATION" in c["reserve"] and "NEUVE" in c["reserve"]


def test_la_penalite_de_retard_se_calcule_et_AVOUE_qu_elle_majore():
    """1/3000ᵉ par jour. Deux éléments ne sont retenus que POUR PARTIE — l'ACT
    pour son DCE, l'AOR pour son DOE — et le modèle ne dit pas laquelle. Le
    module calcule sur l'élément entier et le signale, plutôt que d'inventer
    une fraction."""
    r = _res()
    p = M.penalite_retard(r, "exe", 10)
    assert p["ok"]
    assert abs(p["montant_meur"]
               - round(p["assiette_meur"] / 3000.0 * 10, 3)) < 1e-9
    assert p["reserve"] and "MAJORANT" in p["reserve"]
    # Une phase pleine ne porte pas cette réserve.
    assert M.penalite_retard(r, "apd", 5)["reserve"] is None
    assert M.penalite_retard(r, "inventee", 5)["ok"] is False


def test_le_referentiel_SERT_tout_cela_aux_pages():
    r = M.referentiel()
    for cle in ("engagements", "source_engagement", "plafond_penalite",
                "retard_par_jour", "limite_visa", "correspondance_modele"):
        assert cle in r, cle
    assert r["plafond_penalite"] == 0.15
    assert "93-1268" in " ".join(r["source_engagement"]["textes"])


def test_le_bareme_RESTE_celui_qu_il_etait():
    """L'ajout ne devait toucher ni les missions, ni les taux, ni les phases :
    un chiffrage en cours ne doit pas bouger parce qu'on a documenté un
    engagement."""
    assert len(M.MISSIONS) == 13
    r = _res()
    # `total_meur` est une FOURCHETTE [bas, haut] : ce module ne moyenne jamais
    # une fourchette, et un contrôle qui la traiterait en scalaire l'aurait
    # oublié.
    assert isinstance(r["total_meur"], (list, tuple)) and len(r["total_meur"]) == 2
    assert r["total_meur"][0] > 0 and r["total_meur"][1] >= r["total_meur"][0]
    assert set(M.ORDRE_PHASES) == {"aps", "apd", "pro", "act", "exe"}


def test_LE_POINT_QUI_DECIDE_l_assiette_du_plafond_s_arrete_APRES_l_attribution():
    """TROU TROUVÉ EN ÉPROUVANT LES CONTRÔLES EUX-MÊMES. Élargir l'assiette à
    l'ACT ne faisait tomber aucun test — or l'ACT est l'assistance à la
    PASSATION : elle précède l'attribution, elle n'est pas postérieure. L'y
    inclure gonflerait le plafond d'une phase que l'article 30.II exclut, et
    donc la pénalité que le maître d'œuvre peut supporter."""
    assert M.PHASES_APRES_ATTRIBUTION == ("exe",), M.PHASES_APRES_ATTRIBUTION
    # …et le plafond doit valoir 15 % de la SEULE phase exe, recompté ici.
    r = _res()
    exe = 0.0
    for m in r["missions"]:
        ph = (m.get("phases") or {}).get("exe") or {}
        mt = ph.get("montant_meur")
        if ph.get("retenue") and isinstance(mt, (list, tuple)):
            exe += float(mt[1])
    p = M.plafond_penalite(r)
    assert abs(p["assiette_meur"] - round(exe, 3)) < 1e-9, (p["assiette_meur"], exe)
    # Une assiette qui engloberait l'ACT serait strictement plus grande.
    act = 0.0
    for m in r["missions"]:
        ph = (m.get("phases") or {}).get("act") or {}
        mt = ph.get("montant_meur")
        if ph.get("retenue") and isinstance(mt, (list, tuple)):
            act += float(mt[1])
    assert act > 0, "l'ACT ne pèse rien : le contrôle ne distinguerait plus rien"
    assert p["assiette_meur"] < round(exe + act, 3)


def test_le_dépassement_du_previsionnel_ne_produit_JAMAIS_de_montant():
    """Second trou : forcer la pénalité sur le coût prévisionnel doit tomber.
    Le premier engagement se règle en études — art. 30.I al. 2 — et publier un
    montant à ce stade serait un contresens juridique, pas une nuance."""
    for tx in (0.0, 10.0, 50.0):
        e = M.engagement(40.0, 3.0, cout_reference_meur=80.0,
                         taux_penalite_pct=tx, resultat=_res(),
                         cle="cout_previsionnel")
        assert e["penalite"] is None, (tx, e["penalite"])


def test_la_limite_du_VISA_reste_une_LIMITE_et_non_une_garantie():
    """Troisième trou : adoucir la phrase du VISA ne faisait tomber que les
    contrôles de mots. On vérifie ici le SENS — le texte doit nier, pas
    promettre."""
    n = M.LIMITE_VISA["n_est_pas"].lower()
    assert "ne comprend ni" in n or "ne comprend pas" in n, n
    assert "ne dégage pas" in n, n
    # Aucune formule qui promettrait un contrôle.
    for interdit in ("comprend la vérification", "garantit", "assure le contrôle"):
        assert interdit not in n, interdit
