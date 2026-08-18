"""LE TABLEAU DE RÉPARTITION DES HONORAIRES — rempli, jamais recopié.

POURQUOI CES CONTRÔLES. Ce tableau est une pièce de marché : la maîtrise
d'ouvrage s'en sert pour contractualiser et pour payer. Trois façons de le
rendre faux, et chacune est ici empêchée :

  1. REPRENDRE LES FORMULES DU MODÈLE FOURNI. Vérifiées cellule par cellule,
     elles rendraient un total faux quoi qu'on saisisse — dont une référence
     circulaire en D26. Le module écrit des VALEURS et publie les réserves.
  2. INVENTER UN PARTAGE que la source ne porte pas. Le modèle demande
     quatorze lignes MOP, le barème n'en connaît que cinq : trois lignes sont
     des regroupements, deux n'existent pas au barème. Rien n'est réparti au
     prorata.
  3. ABSORBER L'ÉCART D'ARRONDI en douce. Les montants du barème sont arrondis
     au millier ; leur somme s'écarte de la base contractuelle. L'écart est
     publié, pas dissous dans une ligne au hasard.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from conftest import ORIGINE          # POST sans origine déclarée : refusé
import moe_dc
import repartition_honoraires as RH


def _res(bas=38.0, haut=42.0, fin=True):
    """Le calcul, à l'euro près par défaut — comme le font les routes.

    CE TABLEAU RÉPARTIT, IL N'AFFICHE PAS. Le barème arrondit au millier, ce
    qui convient pour lire ; additionner soixante-cinq montants ainsi arrondis
    faisait dériver la somme de 1,21 % sur un projet de 2 M€."""
    if fin:
        with moe_dc.precision_fine():
            r = moe_dc.honoraires_directs([bas, haut])
    else:
        r = moe_dc.honoraires_directs([bas, haut])
    assert r.get("ok"), r
    return r


def test_le_tableau_suit_les_lignes_du_modele():
    """Le vocabulaire du modèle est ce que le lecteur reconnaît."""
    codes = [L["code"] for L in RH.LIGNES]
    for attendu in ("ESQ", "APS", "APD", "DPC", "PRO", "DCE", "ACT",
                    "VISA", "DET", "AOR", "DOE", "OPC"):
        assert attendu in codes, attendu
    E = RH.etat(_res())
    assert len(E["lignes"]) == len(RH.LIGNES)


def test_LE_POINT_QUI_DECIDE_aucun_partage_n_est_invente():
    """Le barème groupe ESQ+APS+DPC, PRO+DCE, VISA+DET+AOR+DOE. Répartir au
    prorata à l'intérieur d'un groupe fabriquerait un chiffre que personne n'a
    publié — et il serait crédible, ce qui est pire."""
    E = RH.etat(_res())
    par = {L["code"]: L for L in E["lignes"]}
    for code in ("APS", "DPC", "DCE", "DET", "AOR", "DOE"):
        L = par[code]
        assert L["etat"] == "compris_dans", (code, L["etat"])
        assert L["montant"] == 0.0
        # …ET LA RAISON EST ÉCRITE. Un zéro muet laisserait croire que rien
        # n'est dû pour cette phase.
        assert "Compris dans" in L["dit"], (code, L["dit"])
    # Le montant du groupe est porté par sa première ligne, et il est réel.
    for code in ("ESQ", "PRO", "VISA"):
        assert par[code]["montant"] > 0, code
        assert "ne le partage pas" in par[code]["dit"], code


def test_ce_que_le_bareme_ne_couvre_pas_le_DIT_au_lieu_de_valoir_zero():
    """DAACT et GPA n'ont aucun équivalent au barème. Les afficher à zéro
    laisserait croire qu'elles sont dues et gratuites."""
    E = RH.etat(_res())
    par = {L["code"]: L for L in E["lignes"]}
    for code in ("DAACT", "GPA"):
        assert par[code]["etat"] == "absent_du_bareme", code
        assert "Aucune phase du barème" in par[code]["dit"], code


def test_l_OPC_n_est_compte_qu_une_fois():
    """L'ordonnancement est une MISSION au barème et une LIGNE au modèle. La
    compter aussi dans les phases la ferait payer deux fois."""
    E = RH.etat(_res())
    par = {L["code"]: L for L in E["lignes"]}
    assert par["OPC"]["montant"] > 0
    # Aucune ligne de phase ne porte la mission opc.
    for L in E["lignes"]:
        if L["code"] == "OPC":
            continue
        assert "opc" not in L["par_mission"], L["code"]


def test_LE_POINT_QUI_DECIDE_le_tableau_BOUCLE_A_L_EURO_PRES():
    """LE DÉFAUT MESURÉ, ET IL ÉTAIT DANS LA PRÉCISION, PAS DANS LE PARTAGE.

    Le barème arrondit chaque montant au millier d'euros. Ce tableau en
    additionne soixante-cinq — treize missions sur cinq phases — et la somme
    s'écartait alors de la base contractuelle : 0,09 % sur un projet de 42 M€
    de travaux, mais 1,21 % sur un projet de 2 M€, soit 2 000 € sur 165 000 €.
    Dans une pièce qui sert à payer, ce n'est plus un arrondi.

    Calculé à l'euro près, l'écart est NUL — à toutes les tailles, y compris
    les petites, qui étaient les plus touchées."""
    for trav in ([2.0, 2.0], [8.0, 10.0], [38.0, 42.0], [400.0, 450.0]):
        for cote in ("bas", "haut"):
            E = RH.etat(_res(trav[0], trav[1]), cote)
            assert abs(E["ecart_arrondi_eur"]) < 1.0, (trav, cote, E["ecart_arrondi_eur"])


def test_sans_la_precision_fine_l_ecart_EXISTE_et_c_est_pourquoi_elle_est_la():
    """Le contrôle précédent ne prouverait rien si l'écart n'existait pas sans
    la précision fine : il passerait tout seul."""
    E = RH.etat(_res(2.0, 2.0, fin=False))
    assert abs(E["ecart_arrondi_pct"]) > 1.0, E["ecart_arrondi_pct"]


def test_l_ecart_d_arrondi_reste_PUBLIE_quand_il_existe():
    """Les montants du barème sont arrondis au millier ; sur treize missions et
    cinq phases, la somme s'écarte de la base contractuelle. Mesuré : +3 000 €
    sur 3,459 M€, soit 0,09 %. Forcer le total obligerait à retoucher une ligne
    au hasard ; le taire laisserait un lecteur attentif trouver seul une
    différence inexpliquée."""
    E = RH.etat(_res(2.0, 2.0, fin=False))
    assert E["total_eur"] > 0
    assert E["ecart_arrondi_eur"] != 0
    import io, openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(RH.octets(_res(2.0, 2.0, fin=False))))
    txt = " ".join(str(c.value) for row in wb.active.iter_rows() for c in row
                   if c.value is not None)
    assert "Écart d'arrondi" in txt


def test_LA_VENTILATION_FAIT_EXACTEMENT_CENT_POUR_CENT():
    """Un pourcentage qui ne fait pas cent se remarque dans une pièce de marché
    et fait douter du reste. Rapportée à la base du barème, la colonne
    totalisait 100,08 % à cause des arrondis ; elle se rapporte au total du
    tableau."""
    E = RH.etat(_res())
    s = sum(L["ventilation"] for L in E["lignes"])
    assert abs(s - 1.0) < 1e-9, s


def test_la_fourchette_ne_se_moyenne_pas_en_douce():
    """Le barème rend une fourchette, un marché porte un nombre. Moyenner
    produirait un chiffre que ni le bas ni le haut ne défend : le côté est
    choisi, et il change le résultat."""
    r = _res()
    bas = RH.etat(r, "bas")
    haut = RH.etat(r, "haut")
    assert bas["total_eur"] < haut["total_eur"]
    assert bas["cote"] == "bas" and haut["cote"] == "haut"
    import io, openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(RH.octets(r, "bas")))
    txt = " ".join(str(c.value) for row in wb.active.iter_rows() for c in row
                   if c.value is not None)
    assert "basse" in txt, "le classeur ne dit pas quelle borne il retient"


def test_LES_RESERVES_SUR_LE_MODELE_SONT_DANS_LE_CLASSEUR():
    """Les taire reviendrait à laisser quelqu'un remplir de nouveau l'original
    en croyant qu'il calcule juste."""
    assert len(RH.RESERVES_MODELE) >= 4
    import io, openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(RH.octets(_res())))
    txt = " ".join(str(c.value) for row in wb.active.iter_rows() for c in row
                   if c.value is not None)
    assert "circulaire" in txt, "la référence circulaire de D26 n'est pas signalée"
    assert "D26" in txt and "C38" in txt


def test_AUCUNE_MISSION_N_EST_PERDUE_faute_de_colonne():
    """Le modèle fige sept cotraitants ; le barème peut en retenir treize. Se
    limiter à sept obligerait à fondre des missions entre elles — c'est-à-dire
    à effacer ce que ce tableau doit montrer."""
    E = RH.etat(_res())
    retenues = [m for m in _res()["missions"] if (m.get("part_retenue") or 0) > 0]
    assert len(E["cotraitants"]) == len(retenues)
    assert len(E["cotraitants"]) > 7, len(E["cotraitants"])
    import io, openpyxl
    ws = openpyxl.load_workbook(io.BytesIO(RH.octets(_res()))).active
    # Une paire de colonnes par cotraitant, plus les quatre de gauche.
    assert ws.max_column >= 4 + 2 * len(E["cotraitants"])


def test_le_classeur_s_ouvre_et_porte_l_operation():
    import io, openpyxl
    b = RH.octets(_res(), "haut", operation="Essai d'opération",
                  reference="REF-42")
    ws = openpyxl.load_workbook(io.BytesIO(b)).active
    txt = " ".join(str(c.value) for row in ws.iter_rows() for c in row
                   if c.value is not None)
    assert "Essai d'opération" in txt and "REF-42" in txt
    assert ws.title == "Tableau de répartition"


def test_sante():
    s = RH.sante()
    assert s["lignes_modele"] == len(RH.LIGNES)
    assert s["absents_du_bareme"] == 2
    assert s["regroupements"] == 3


# ═══════════════════════════════════════════════════════════════════════════
#  LA ROUTE — et la garde qu'elle partage avec le calcul qu'elle met en forme
# ═══════════════════════════════════════════════════════════════════════════

def test_la_route_est_FERMEE_au_visiteur_sans_compte(anonyme):
    """Ce tableau ne montre rien de plus que le calcul de maîtrise d'œuvre.
    Lui ouvrir une porte plus large reviendrait à publier par le classeur ce
    que la page refuse à l'écran."""
    r = anonyme.post("/api/datacenter/moe/repartition", headers=ORIGINE,
                     json={"travaux_meur": [38, 42]})
    assert r.status_code in (401, 403), r.status_code


def test_la_route_sert_les_donnees_au_client(connecte):
    r = connecte.post("/api/datacenter/moe/repartition", headers=ORIGINE,
                      json={"travaux_meur": [38, 42], "operation": "Essai"})
    assert r.status_code == 200, r.status_code
    d = r.get_json()
    assert d["ok"] is True
    assert len(d["lignes"]) >= 12
    assert d["total_eur"] > 0
    assert len(d["reserves_modele"]) >= 4


def test_la_route_sert_le_CLASSEUR_et_il_s_ouvre(connecte):
    r = connecte.post("/api/datacenter/moe/repartition?format=xlsx", headers=ORIGINE,
                      json={"travaux_meur": [38, 42]})
    assert r.status_code == 200, r.status_code
    assert "spreadsheetml" in r.headers.get("Content-Type", "")
    assert "attachment" in r.headers.get("Content-Disposition", "")
    import io, openpyxl
    ws = openpyxl.load_workbook(io.BytesIO(r.data)).active
    assert ws.title == "Tableau de répartition"


def test_un_montant_de_travaux_absent_ou_nul_est_REFUSE(connecte):
    """Sans travaux, il n'y a pas d'assiette : rendre un tableau vide de
    montants laisserait croire à une mission gratuite."""
    for charge in ({}, {"travaux_meur": 0}, {"travaux_meur": [0, 0]},
                   {"travaux_meur": "beaucoup"}):
        r = connecte.post("/api/datacenter/moe/repartition", headers=ORIGINE,
                          json=charge)
        assert r.status_code == 400, (charge, r.status_code)


def test_une_mission_HORS_PORTEE_est_refusee_avec_sa_raison(connecte):
    """Le barème ne chiffre que de la maîtrise d'œuvre. L'appliquer à une AMO
    ou à un EPC donnerait un nombre faux et crédible."""
    r = connecte.post("/api/datacenter/moe/repartition", headers=ORIGINE,
                      json={"travaux_meur": [38, 42], "mission": "amo"})
    assert r.status_code == 400
    d = r.get_json()
    assert d.get("error") == "hors_portee"
    assert d.get("dit")
