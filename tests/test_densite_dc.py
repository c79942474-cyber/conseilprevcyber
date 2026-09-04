# -*- coding: utf-8 -*-
"""La densité par baie, le plancher qu'elle charge, et le tri du document.

CE QUE CES RÈGLES MESURENT, ET CE QU'ELLES REFUSENT DE MESURER. Elles portent
sur des RÉSULTATS DE CALCUL — quelles familles sont écartées à 130 kW, quel
critère mord sur une salle courante, combien de fois l'air demande la section
de l'eau — et non sur la présence d'une clé dans un dictionnaire. Une règle qui
vérifie qu'un mot figure dans un fichier passe pour une raison sans rapport
avec ce qu'elle prétend ; ce dépôt en a corrigé plusieurs, et celles-ci sont
écrites en sachant cela.

CE QU'ELLES GARDENT EN PLUS. Le module reprend des pratiques lues dans un livre
blanc COMMANDITÉ par un fabricant. Le risque n'est pas qu'une valeur soit
fausse : c'est que l'argument de vente du commanditaire entre au référentiel
sous les traits d'une bonne pratique. Trois règles portent donc sur le TRI —
chaque pratique déclare son origine, ce qui a été refusé est déclaré avec son
motif, et rien n'est à la fois retenu et écarté.

UNE FAUTE RÉELLE, ATTRAPÉE AVANT PUBLICATION, EST GARDÉE ICI. La première
version comparait la masse d'une baie rapportée à son EMPRISE NUE à une
capacité de plancher exprimée en charge RÉPARTIE. Les deux grandeurs n'ont pas
le même sens, et le module rendait « ne passe pas » sur une salle d'hébergement
ordinaire — c'est-à-dire sur des salles qui existent et qui fonctionnent. La
règle `test_une_baie_classique_passe_sur_une_salle_courante` est le témoin
négatif qui l'aurait attrapée : sans elle, rien n'aurait signalé qu'un moteur
qui refuse tout est cohérent avec lui-même.
"""
import io
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import densite_dc as D  # noqa: E402


def _lire(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


# ══════════════════════════════════════════════════════════════════════════
# 0. Le garde-fou — une lecture cassée rendrait tout le reste vert
# ══════════════════════════════════════════════════════════════════════════

def test_le_referentiel_porte_bien_ce_que_les_regles_suivantes_mesurent():
    """Le défaut que ce dépôt a déjà commis : des règles vertes qui ne
    mesurent rien parce que la table qu'elles interrogent est vide."""
    assert len(D.DIFFUSION) >= 6, len(D.DIFFUSION)
    assert len(D.REGIMES) >= 4, len(D.REGIMES)
    assert len(D.PLANCHERS) >= 3, len(D.PLANCHERS)
    assert len(D.FAUX_PLANCHERS) >= 3, len(D.FAUX_PLANCHERS)
    assert len(D.CONSTRUCTION) >= 8, len(D.CONSTRUCTION)
    assert len(D.ECARTES) >= 4, len(D.ECARTES)


# ══════════════════════════════════════════════════════════════════════════
# 1. Les familles de diffusion — l'ordre porte du sens, et il est mesuré
# ══════════════════════════════════════════════════════════════════════════

def test_l_ordre_declare_couvre_exactement_les_familles():
    """Une famille absente de l'ordre serait invisible du formulaire ET des
    calculs, sans qu'aucune erreur ne se lève."""
    assert sorted(D.ORDRE_DIFFUSION) == sorted(D.DIFFUSION), (
        set(D.DIFFUSION) ^ set(D.ORDRE_DIFFUSION))
    assert sorted(D.ORDRE_REGIMES) == sorted(D.REGIMES)


def test_les_plafonds_croissent_dans_l_ordre_declare():
    """L'ordre sert à dire « la famille suivante » et « la moins coûteuse en
    bâtiment ». Un plafond qui classerait l'air au-dessus du liquide ferait
    proposer de l'air à 300 kW — sans qu'aucune règle de forme ne bronche."""
    plafonds = [D.DIFFUSION[c].get("plafond_kw_baie") for c in D.ORDRE_DIFFUSION]
    bornes = [p for p in plafonds if p is not None]
    assert bornes == sorted(bornes), plafonds
    # Les familles SANS plafond viennent en fin d'ordre : une famille bornée
    # placée après une famille libre ne serait jamais retenue.
    libres = [i for i, p in enumerate(plafonds) if p is None]
    assert not libres or min(libres) > max(
        i for i, p in enumerate(plafonds) if p is not None), plafonds


def test_une_famille_sans_plafond_dit_ce_qui_le_porte():
    """« Pas de plafond » sans explication se lit « aucune limite ». Or la
    limite existe : elle a changé de nature, et c'est tout le propos."""
    muettes = [c for c, v in D.DIFFUSION.items()
               if v.get("plafond_kw_baie") is None
               and not (v.get("plafond_porte_par") or "").strip()]
    assert not muettes, muettes


@pytest.mark.parametrize("cle", sorted(D.DIFFUSION))
def test_chaque_famille_dit_ce_qui_la_plafonne_et_ce_qu_elle_coute_en_renovation(cle):
    """Sans ces deux champs, la table est une liste d'options — et le lecteur
    choisit une étiquette sans savoir ce qu'elle engage."""
    v = D.DIFFUSION[cle]
    # LE NOM EST UNE ÉTIQUETTE, PAS UNE EXPLICATION : lui imposer une longueur
    # minimale poussait à rallonger « Échangeur en porte arrière », qui est le
    # nom exact. C'est la règle qui avait tort, pas la donnée — et une règle
    # qui pousse à dégrader ce qu'elle garde est pire qu'une règle absente.
    assert (v.get("nom") or "").strip(), cle
    for champ in ("principe", "ce_qui_plafonne", "renovation"):
        assert len((v.get(champ) or "").strip()) > 40, (cle, champ)


# ══════════════════════════════════════════════════════════════════════════
# 2. Le calcul — mesuré sur ses sorties
# ══════════════════════════════════════════════════════════════════════════

def test_a_la_densite_des_accelerateurs_aucune_famille_a_air_ne_tient():
    """LA RÈGLE QUI PORTE LA THÈSE. « Quand la densité monte, l'eau
    s'impose » : ici on l'exige du CALCUL, à la densité réellement déployée.
    Une table dont les plafonds seraient relevés en douce la ferait tomber."""
    d = D.salle(130)["diffusion"]
    admises = {a["cle"] for a in d["admises"]}
    assert not (admises & {"air_libre", "air_confine", "air_confine_haut"}), admises
    assert d["premiere_admise"]["cle"] in ("dlc", "immersion"), d["premiere_admise"]
    assert d["liquide_impose"] is True


def test_a_la_densite_classique_l_air_le_plus_simple_suffit():
    """LE TÉMOIN NÉGATIF DE LA PRÉCÉDENTE. Un moteur qui imposerait le liquide
    partout satisferait la règle ci-dessus sans rien mesurer."""
    d = D.salle(5)["diffusion"]
    assert d["premiere_admise"]["cle"] == "air_libre", d["premiere_admise"]
    assert d["liquide_impose"] is False
    assert not d["exclues"], d["exclues"]


def test_le_rapport_des_sections_est_le_meme_a_toutes_les_densites():
    """CE QUE LE CHIFFRE DIT VRAIMENT, et qu'un rendu pressé ferait dire de
    travers : le rapport ne dépend que des fluides et des vitesses retenues.
    Ce que la densité change, c'est la taille absolue de la gaine."""
    r5 = D.transport(5)["rapport_sections"]
    r300 = D.transport(300)["rapport_sections"]
    assert r5 == r300, (r5, r300)
    assert r5 > 100, r5


def test_la_gaine_devient_impossible_quand_le_tube_reste_ordinaire():
    """La conséquence concrète : à la densité des accélérateurs, l'eau tient
    dans un tube de plomberie et l'air demande une gaine d'un mètre de côté."""
    t = D.transport(130)
    assert t["eau"]["diametre_equivalent_mm"] < 60, t["eau"]
    assert t["air"]["cote_carre_m"] > 1.0, t["air"]


# ══════════════════════════════════════════════════════════════════════════
# 3. Le plancher — deux critères, et le témoin négatif de la faute corrigée
# ══════════════════════════════════════════════════════════════════════════

def test_une_baie_classique_passe_sur_une_salle_courante():
    """LE TÉMOIN NÉGATIF QUI AURAIT ATTRAPÉ LA FAUTE. Une première version
    rapportait la masse à l'emprise NUE et la comparait à une capacité
    exprimée en charge RÉPARTIE : elle refusait une baie de 700 kg dans une
    salle d'hébergement ordinaire, c'est-à-dire une situation qui existe par
    milliers. Un moteur qui refuse tout ne se signale jamais tout seul."""
    p = D.salle(5, regime="classique", plancher_cle="courant",
                faux_plancher="standard")["plancher"]
    assert p["verdict"] == "go", p
    assert p["dalle"]["verdict"] == "go", p["dalle"]
    assert p["faux_plancher"]["verdict"] == "go", p["faux_plancher"]


def test_une_baie_d_accelerateurs_ne_passe_pas_sur_une_salle_courante():
    """L'autre bout de la mesure, sans lequel la précédente serait satisfaite
    par un moteur qui accepte tout."""
    p = D.salle(130, regime="ia_accelerateurs", plancher_cle="courant",
                faux_plancher="standard")["plancher"]
    assert p["verdict"] == "nogo", p


def test_le_faux_plancher_mord_avant_la_dalle_sur_une_baie_dense_a_air():
    """LE CAS QUI DÉCIDE D'UNE RÉNOVATION, et que le seul critère en
    kilopascals ne voit pas : la dalle tient, les panneaux non. Le remède
    n'est alors pas une reprise de structure — c'est un démontage."""
    p = D.salle(30, regime="dense_air", plancher_cle="courant",
                faux_plancher="standard")["plancher"]
    assert p["dalle"]["verdict"] != "nogo", p["dalle"]
    assert p["faux_plancher"]["verdict"] == "nogo", p["faux_plancher"]
    assert p["critere_qui_mord"] == "le faux-plancher", p


def test_le_verdict_est_le_plus_defavorable_des_deux_criteres():
    """Rendre le meilleur ferait passer une baie que le plancher n'accepte
    pas ; c'est la faute la plus coûteuse que ce module puisse commettre."""
    rang = {"go": 0, "limite": 1, "nogo": 2}
    for kw, reg, pl, fp in ((5, "classique", "courant", "standard"),
                            (30, "dense_air", "courant", "standard"),
                            (30, "dense_air", "renforce", "lourd"),
                            (130, "ia_accelerateurs", "renforce", "lourd"),
                            (300, "ia_suivante", "lourd", "aucun")):
        p = D.salle(kw, regime=reg, plancher_cle=pl, faux_plancher=fp)["plancher"]
        pires = [p["dalle"]["verdict"]]
        if p["faux_plancher"]["verdict"]:
            pires.append(p["faux_plancher"]["verdict"])
        attendu = max(pires, key=lambda v: rang[v])
        assert p["verdict"] == attendu, (kw, reg, pl, fp, p["verdict"], pires)


def test_sans_masse_declaree_le_plancher_n_est_pas_tranche():
    """RIEN N'EST DEVINÉ. Aucune loi ne relie la puissance d'une baie à son
    poids : un GO calculé sur une masse supposée serait pire qu'un refus de
    trancher, parce qu'on ne le contesterait pas."""
    p = D.salle(130, plancher_cle="courant")["plancher"]
    assert p["verdict"] == "indetermine", p
    assert any("masse" in m for m in p["manques"]), p["manques"]


def test_la_masse_reprise_d_un_regime_est_declaree_comme_telle():
    """Un chiffre repris d'ailleurs qui se présenterait comme une saisie de
    l'utilisateur serait une supposition déguisée en donnée."""
    r = D.salle(130, regime="ia_accelerateurs")
    assert r["masse"]["origine"] == "reprise_du_regime", r["masse"]
    assert r["masse"]["regime"] == "ia_accelerateurs"
    assert D.salle(130, masse_baie_kg=900)["masse"]["origine"] == "declaree"


def test_la_charge_repartie_se_calcule_sur_la_surface_d_influence():
    """L'ARITHMÉTIQUE DE LA FAUTE CORRIGÉE, vérifiée directement : la charge
    répartie divise par la surface d'influence — allées comprises — et la
    pression sous emprise divise par l'emprise nue. Les deux sortent, et
    elles diffèrent."""
    p = D.plancher(masse_baie_kg=1360, capacite_kpa=7.2)
    assert p["dalle"]["charge_repartie_kg_m2"] == round(
        1360 / D.CONSTANTES["emprise_baie_m2"]["valeur"])
    assert p["pression_sous_emprise_kg_m2"] == round(
        1360 / D.CONSTANTES["emprise_baie_nue_m2"]["valeur"])
    assert p["pression_sous_emprise_kg_m2"] > p["dalle"]["charge_repartie_kg_m2"]


# ══════════════════════════════════════════════════════════════════════════
# 4. La rénovation — l'obstacle qui se lève et celui qui ne se lève pas
# ══════════════════════════════════════════════════════════════════════════

def test_la_renovation_nomme_le_nombre_de_familles_a_franchir():
    r = D.salle(130, regime="ia_accelerateurs", plancher_cle="courant",
                diffusion_existante="air_confine")["renovation"]
    assert r["verdict"] == "bloque", r
    assert any("air à l'eau" in o for o in r["obstacles"]), r["obstacles"]


def test_une_dalle_qui_ne_porte_pas_et_un_faux_plancher_qui_ne_porte_pas_ne_disent_pas_la_meme_chose():
    """C'EST LA DISTINCTION QUI VAUT DE L'ARGENT. Le premier obstacle se lève
    en démontant un plancher technique ; le second suppose de reprendre une
    dalle en salle occupée, et décide souvent de construire ailleurs."""
    fp = D.salle(30, regime="dense_air", plancher_cle="courant",
                 faux_plancher="standard",
                 diffusion_existante="air_confine")["renovation"]
    dalle = D.salle(300, regime="ia_suivante", plancher_cle="courant",
                    faux_plancher="aucun",
                    diffusion_existante="air_confine")["renovation"]
    assert any("FAUX-PLANCHER" in o for o in fp["obstacles"]), fp["obstacles"]
    assert any("se lève" in o for o in fp["obstacles"]), fp["obstacles"]
    assert any("DALLE" in o for o in dalle["obstacles"]), dalle["obstacles"]
    assert any("construire ailleurs" in o for o in dalle["obstacles"]), \
        dalle["obstacles"]


# ══════════════════════════════════════════════════════════════════════════
# 5. L'échelle du parc — la lecture suit le nombre, elle ne le précède pas
# ══════════════════════════════════════════════════════════════════════════

def test_la_lecture_de_parc_emploie_le_meme_critere_que_la_lecture_de_salle():
    """DEUX FABRIQUES D'UN MÊME CHIFFRE DIVERGENT, toujours. Le parc annonçait
    un refus que la salle dément deux écrans plus bas, parce qu'il divisait
    par l'emprise nue quand la salle divise par la surface d'influence."""
    p = D.pression_construction(regime_ia="ia_accelerateurs",
                                plancher_existant="courant")
    s = D.salle(130, regime="ia_accelerateurs", plancher_cle="courant")
    assert p["charge_du_regime_kg_m2"] == s["plancher"]["dalle"]["charge_repartie_kg_m2"]


def test_la_lecture_ne_qualifie_un_compte_de_modeste_que_s_il_l_est():
    """UNE CONCLUSION ÉCRITE EN DUR N'EST PAS UNE LECTURE. La phrase affirmait
    « un nombre modeste » quel que soit le résultat — vrai au régime IA, faux
    au régime classique où le compte est vingt-cinq fois plus grand.

    CETTE RÈGLE A ÉTÉ REPRISE PARCE QU'ELLE ÉTAIT COMPLAISANTE. Sa première
    version comparait la lecture du régime IA à celle du régime classique — or
    ces deux lectures empruntent des BRANCHES DIFFÉRENTES : au régime
    classique le plancher passe, et la branche correspondante ne contient
    jamais l'expression cherchée, quelle que soit la logique de choix. La
    règle était verte sans rien mesurer, et une mutation qui figeait le choix
    à « toujours » lui survivait. Elle éprouve désormais la phrase LÀ OÙ ELLE
    SE CHOISIT, à branche égale, sur les deux ordres de grandeur.
    """
    charge, cap = 900.0, 734.0            # même branche : le plancher ne passe pas
    dense = D._lecture_pression(805.0, 920.0, D.REGIMES["ia_accelerateurs"],
                                D.REGIMES["dense_air"], charge, cap, "courant")
    epars = D._lecture_pression(805.0, 920.0, D.REGIMES["classique"],
                                D.REGIMES["dense_air"], charge, cap, "courant")
    assert "moins nombreuses" in dense, dense
    assert "moins nombreuses" not in epars, epars
    # Et le fait mesuré derrière la phrase : le compte de baies s'inverse.
    ia = D.pression_construction(regime_ia="ia_accelerateurs")
    cl = D.pression_construction(regime_ia="classique")
    assert ia["baies_au_regime_ia"][0] < ia["baies_si_meme_puissance_en_air"][0]
    assert cl["baies_au_regime_ia"][0] > cl["baies_si_meme_puissance_en_air"][0]


def test_un_depassement_infime_ne_s_annonce_pas_en_facteur():
    """« Soit 1,0 fois trop » pour un dépassement d'un pour mille aurait
    décrédibilisé un constat pourtant exact."""
    t = D.pression_construction(regime_ia="ia_accelerateurs",
                                plancher_existant="courant")["lecture"]
    assert "1,0 fois trop" not in t, t
    assert "sans aucune marge" in t, t


def test_la_projection_de_marche_porte_son_emetteur_et_sa_reserve():
    """Un ordre de grandeur repris sans son émetteur devient un fait au bout
    de deux citations."""
    m = D.MARCHE_FR
    assert "France Datacenter" in m["source"], m["source"]
    assert m["nature"] == "projection_de_cabinet"
    assert len(m["reserve"]) > 150, len(m["reserve"])
    # La déduction du point de départ est déclarée comme déduction.
    assert "DÉDUCTION" in m["reserve"] or "déduction" in m["reserve"]


# ══════════════════════════════════════════════════════════════════════════
# 6. LE TRI DU DOCUMENT — ce qui est retenu, ce qui est refusé, et pourquoi
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cle", sorted(D.CONSTRUCTION))
def test_chaque_pratique_declare_son_origine_et_son_mecanisme(cle):
    """UNE PRATIQUE SANS MÉCANISME EST UNE RECOMMANDATION, et une
    recommandation sans origine est celle du dernier qui a parlé."""
    v = D.CONSTRUCTION[cle]
    assert v.get("origine") in ("document", "mecanisme_etabli"), (cle, v.get("origine"))
    assert len((v.get("mecanisme") or "").strip()) > 80, cle
    assert len((v.get("ne_couvre_pas") or "").strip()) > 40, cle


def test_le_tri_a_refuse_quelque_chose_et_dit_quoi():
    """UN TRI QUI NE MONTRE QUE CE QU'IL GARDE N'EST PAS UN TRI. Une table
    d'écarts vide signalerait qu'on a repris le document, pas qu'on l'a lu."""
    assert len(D.ECARTES) >= 4, len(D.ECARTES)
    for cle, v in D.ECARTES.items():
        assert len((v.get("affirmation") or "").strip()) > 40, cle
        assert len((v.get("motif") or "").strip()) > 80, cle


def test_l_argument_de_scope_2_automatique_est_explicitement_ecarte():
    """LA RAISON D'ÊTRE DE LA TABLE DES ÉCARTS. « Les émissions de scope 2 de
    nos produits baissent automatiquement, sans action de l'équipe projet »
    est le raisonnement en approche marché que le moteur de décarbonation du
    cabinet signale déjà comme trompeur. Le laisser entrer au référentiel
    sous les traits d'une bonne pratique aurait contredit un autre module du
    même site."""
    motifs = " ".join(v["motif"] for v in D.ECARTES.values())
    affirmations = " ".join(v["affirmation"] for v in D.ECARTES.values())
    assert "scope 2" in affirmations.lower(), affirmations
    assert "approche marché" in motifs, motifs


def test_rien_n_est_a_la_fois_retenu_et_ecarte():
    """Une affirmation présente des deux côtés signalerait un arbitrage qui a
    changé sans que l'autre table suive."""
    assert not (set(D.CONSTRUCTION) & set(D.ECARTES)), \
        set(D.CONSTRUCTION) & set(D.ECARTES)


def test_la_provenance_du_document_est_declaree_avec_son_commanditaire():
    """Le lecteur doit pouvoir peser ce qu'il lit. Taire que la source est
    commanditée par un fabricant de charpente reviendrait à présenter son
    argumentaire comme un état de l'art."""
    t = D.CONSTRUCTION_SOURCE
    assert "commandit" in t.lower(), t
    assert "norme" in t.lower(), t


def test_la_reserve_de_charge_dit_ce_qu_elle_n_est_pas():
    """LE PIÈGE DE LECTURE de cette valeur : la prendre au mètre carré la
    multiplierait par la trame, la prendre en total de bâtiment la
    diviserait d'autant. Elle est portée par l'ÉLÉMENT."""
    r = D.reserve_de_charge()
    assert "NON par mètre carré" in r["porte_par"], r["porte_par"]
    assert r["origine"] == "document"
    assert len(r["citation"]) > 60
    assert "MÉCANISME" in r["reserve"], r["reserve"]


# ══════════════════════════════════════════════════════════════════════════
# 7. Les constantes — chacune porte sa nature, et le calcul les rend
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cle", sorted(D.CONSTANTES))
def test_chaque_constante_dit_sa_nature_et_d_ou_elle_vient(cle):
    """Une vitesse d'air de 7 m/s au lieu de 10 change une section de
    moitié. Une constante sans nature déclarée se lit comme une mesure."""
    v = D.CONSTANTES[cle]
    assert v["nature"] in ("physique", "geometrie", "hypothese_geometrique",
                           "plage_de_conception"), (cle, v["nature"])
    assert len((v.get("source") or "").strip()) > 20, cle


def test_le_resultat_emporte_les_constantes_qui_l_ont_produit():
    """Un chiffre sans ses hypothèses ne se conteste pas — et ce sont les
    hypothèses qui décident ici, pas la formule."""
    r = D.salle(130, regime="ia_accelerateurs")
    assert r["constantes"] is D.CONSTANTES or r["constantes"] == D.CONSTANTES
    assert r["transport"]["eau"]["vitesse_m_s"] == D.CONSTANTES["vitesse_eau"]["valeur"]


def test_une_puissance_nulle_ou_negative_est_refusee():
    for mauvais in (0, -1):
        with pytest.raises(ValueError):
            D.salle(mauvais)


# ══════════════════════════════════════════════════════════════════════════
# 8. Ce que la page et le glossaire en font
# ══════════════════════════════════════════════════════════════════════════

def test_la_section_existe_dans_la_page_et_porte_ses_commandes():
    h = _lire("ingenierie-datacenter.html")
    for ancre in ('id="ig-densite"', 'id="ig-den-form"', 'id="ig-den-go"',
                  'id="ig-den-out"', 'id="ig-den-echelle"', 'id="ig-den-prat-c"'):
        assert ancre in h, ancre


def test_la_page_ne_recopie_aucun_plafond_ni_aucune_masse():
    """LE DÉFAUT QUI GUETTE CE GENRE DE SECTION : un chiffre recopié dans le
    HTML « pour l'exemple », qui devient faux au premier ajustement du
    référentiel et que personne ne relit."""
    h = _lire("ingenierie-datacenter.html")
    deb = h.index('id="ig-densite"')
    corps = h[deb:h.index("</section>", deb)]
    for v in (str(int(D.REGIMES["ia_accelerateurs"]["masse_baie_kg"])),
              str(int(D.PLANCHERS["courant"]["kpa"] * 1000 / 9.80665)),
              str(int(D.RESERVE_CHARGE_KG))):
        assert v not in corps, (
            "la valeur %s est écrite en dur dans la page : elle divergera du "
            "référentiel sans que rien ne le signale" % v)


def test_le_glossaire_du_module_couvre_les_quatre_familles_neuves():
    g = D.glossaire()
    for famille, table in (("diffusion", D.DIFFUSION), ("regime", D.REGIMES),
                           ("plancher_dc", D.PLANCHERS),
                           ("faux_plancher", D.FAUX_PLANCHERS),
                           ("pratique_construction", D.CONSTRUCTION)):
        assert set(g[famille]) == set(table), famille
        for cle, v in g[famille].items():
            assert len(v["aide"]) > 80, (famille, cle)


def test_le_glossaire_de_la_page_sert_bien_les_familles_du_module():
    """Le mécanisme d'infobulle de la page ne connaît QU'UNE table. Un module
    qui ne s'y verse pas rend des étiquettes muettes — sans erreur."""
    import ingenierie_dc as G
    g = G.glossaire()
    for famille in ("diffusion", "regime", "plancher_dc", "faux_plancher",
                    "pratique_construction"):
        assert famille in g, famille
        assert g[famille], famille


def test_la_section_est_atteinte_par_au_moins_un_parcours_guide():
    """Une section qu'aucun guide ne fait visiter n'est trouvable qu'en
    déroulant la page entière."""
    import ingenierie_dc as G
    roles = [r for r, seq in G.SEQUENCES.items() if "ig-densite" in seq]
    assert len(roles) >= 2, roles
    for r in roles:
        assert "ig-densite" in G._CONSIGNES[r], r


def test_le_js_lit_le_referentiel_au_lieu_de_recopier_les_familles():
    js = _lire("ingenierie-dc.js")
    deb = js.index("function densiteFormulaire(")
    corps = js[deb:deb + 3000]
    assert "R.ordre_diffusion" in corps and "R.regimes" in corps, corps[:200]
    assert "R.faux_planchers" in corps
