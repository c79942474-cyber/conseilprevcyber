"""La carte de décarbonation ne doit pas pouvoir mentir.

CE QUE CES RÈGLES TIENNENT. Chaque étape du cadre porte un `apport_moteur` —
`complet`, `partiel`, `cadre_seul`. C'est une déclaration écrite à la main, et
rien ne la vérifiait. Une fonction retirée, un calcul déplacé, et l'affirmation
reste : la carte promet ce que le moteur ne fait plus, et cela ne se découvre
qu'au moment où un client le demande.

LA CONFUSION QU'ELLES INTERDISENT, et c'est la plus coûteuse du domaine :
constater qu'une VALEUR SORT ne dit pas qu'elle SATISFAIT le texte. Le moteur
produit un PUE de conception ; le PUE au sens d'ISO/IEC 30134-2 demande douze
mois de mesure. L'étape « KPI » le dit déjà dans sa preuve. Une sonde qui
déclarerait l'exigence couverte parce qu'un nombre apparaît ferait exactement
la faute contre laquelle cette étape met en garde.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import datacenter as D                                             # noqa: E402
import decarbonation as DEC                                        # noqa: E402
import ecart_referentiel as E                                      # noqa: E402
import etat_art                                                    # noqa: E402

NOUVEAUX = ("iso14040", "ecodesign_serveurs", "deee", "agec")


# ── 1. Le référentiel s'est étendu là où le fonds déclarait ses trous ──────

def test_les_quatre_axes_verts_sont_entres_au_referentiel():
    """Carbone incorporé, matériel, fin de vie, réemploi : quatre sujets que
    les vingt et un textes d'origine ne portaient pas — et dont l'absence
    recoupait quatre lacunes déclarées depuis l'origine."""
    for cle in NOUVEAUX:
        assert cle in DEC.TEXTES, cle


def test_chaque_nouveau_texte_dit_ce_qu_il_NE_regle_PAS():
    """Un référentiel qui n'énonce que des obligations laisse croire qu'il
    couvre tout. ISO 14040 dit comment conduire l'étude, jamais ce que pèse un
    serveur : le taire ferait chercher dans la norme un chiffre qui n'y est
    pas."""
    for cle in NOUVEAUX:
        t = DEC.TEXTES[cle]
        assert t.get("portee") in DEC.PORTEES, cle
        assert (t.get("ne_regle_pas") or "").strip(), cle


def test_aucun_texte_n_est_orphelin():
    """Un texte rattaché à aucune étape est une exigence que personne
    n'applique — et qui figure pourtant au référentiel."""
    cites = set()
    for e in DEC.ETAPES:
        cites |= set(e["textes"])
    assert set(DEC.TEXTES) == cites


# ── 2. La sonde EXÉCUTE, elle ne nomme pas ────────────────────────────────

def test_chaque_etape_a_sa_sonde():
    """Une étape sans sonde passerait pour conforme sans avoir été regardée."""
    assert {e["code"] for e in DEC.ETAPES} == set(E.SONDES)


def test_un_moteur_vide_fait_apparaitre_les_regressions(monkeypatch):
    """LA RÈGLE QUI DISTINGUE UNE SONDE D'UN CONTRÔLE DE PRÉSENCE.

    On garde la fonction, son nom et sa signature ; on lui retire ce qu'elle
    produit. Un contrôle qui vérifierait l'existence du symbole resterait vert.
    """
    monkeypatch.setattr(D, "etude", lambda profil: {})
    a = E.analyse()
    assert a["regressions"], "un moteur muet doit se voir"
    for code in a["regressions"]:
        ligne = [l for l in a["etapes"] if l["code"] == code][0]
        assert ligne["declare"] in ("complet", "partiel")


def test_le_moteur_reel_ne_presente_aucune_regression():
    """Le pendant : une règle qui ne verrait que le cas dégradé resterait verte
    si la sonde criait au loup en permanence."""
    assert E.analyse()["regressions"] == []


def test_le_profil_de_sonde_exerce_le_moteur_au_lieu_de_le_frôler():
    """SUR LES VALEURS PAR DÉFAUT, LE SCOPE 1 NE PRODUIT RIEN — non parce qu'il
    est cassé, mais parce qu'on ne lui a rien donné à compter. Une sonde bâtie
    sur les défauts déclarerait cette étape en régression à chaque passage.

    LA PREMIÈRE VERSION DE CETTE RÈGLE SE CONTENTAIT D'UN POSTE PRÉSENT, et une
    mutation l'a prise en défaut : en mettant le gazole à zéro, le moteur rend
    toujours un poste — valant zéro. La formule tourne, elle n'est pas
    exercée. Un profil de sonde qui ne produirait que des zéros passerait donc
    pour un profil représentatif, et ne prouverait rien du moteur.
    """
    defauts = {c["id"]: c.get("defaut") for c in D.CHAMPS}
    assert not E._postes(D.etude(defauts), "scope1")
    postes = E._postes(D.etude(dict(E.PROFIL_SONDE)), "scope1")
    assert postes
    assert any((p.get("valeur") or 0) > 0 for p in postes), (
        "tous les postes du scope 1 valent zéro : la formule tourne, le "
        "moteur n'est pas exercé")


def test_une_grandeur_sans_valeur_ne_compte_pas_comme_produite():
    """UNE GRANDEUR QUI A CESSÉ DE CALCULER GARDE TOUT LE RESTE — son nom, son
    unité, sa formule, sa source — et perd sa seule valeur. C'est la forme que
    prend une régression réelle, et c'est précisément celle qui ressemble le
    plus à un calcul en bon état. La compter comme produite laisserait la carte
    promettre un chiffre qui ne sort plus.
    """
    etude = {"carbone": {"cue": {"nom": "CUE", "unite": "kgCO2e/kWh",
                                 "formule": "…", "valeur": None}}}
    assert E._grandeur(etude, "carbone.cue") is None
    # …MAIS ZÉRO EST UNE VALEUR. Un scope 1 nul parce qu'il n'y a pas de groupe
    # électrogène est un résultat, pas une absence : le confondre avec un
    # calcul manquant ferait accuser un moteur qui a répondu.
    etude["carbone"]["cue"]["valeur"] = 0
    assert E._grandeur(etude, "carbone.cue") is not None


def test_un_poste_sans_valeur_ne_compte_pas_davantage():
    sans = {"scope1": {"postes": [{"nom": "Groupes", "valeur": None}]}}
    avec = {"scope1": {"postes": [{"nom": "Groupes", "valeur": 0}]}}
    assert E._postes(sans, "scope1") == []
    assert len(E._postes(avec, "scope1")) == 1


def test_la_sonde_lit_les_deux_formes_de_sortie():
    """`scope1` rend des POSTES, les autres blocs des grandeurs. Une sonde qui
    ne connaîtrait que la seconde forme accuserait une étape qui calcule — et
    une accusation fausse use un rapport plus vite qu'un silence."""
    inv = [l for l in E.sonder() if l["code"] == "INV"][0]
    assert any(p["chemin"] == "scope1" for p in inv["produit"])
    assert any(p["chemin"].startswith("carbone.") for p in inv["produit"])


# ── 3. Les trois états, et ce qu'ils ont le droit d'affirmer ──────────────

def test_hors_calcul_n_est_jamais_un_ecart():
    """Exiger d'un moteur qu'il produise une note de périmètre signée
    fabriquerait un manque qui n'en est pas un."""
    a = E.analyse()
    hors = [l for l in a["etapes"] if l["etat"] == "hors_calcul"]
    assert hors
    for l in hors:
        assert l["code"] not in a["regressions"]
        assert l["dit"], "un hors-calcul doit dire POURQUOI"


def test_sous_declare_n_est_pas_presente_comme_une_faute():
    """LE CAS DU PUE DE CONCEPTION. Des valeurs sortent d'une étape annoncée
    « cadre seul » : ce n'est pas une faute, c'est souvent la bonne réponse.
    Le dire autrement ferait corriger une carte qui a raison."""
    ligne = [l for l in E.sonder() if l["etat"] == "sous_declare"]
    assert ligne, "l'étape KPI doit ressortir ainsi"
    assert "pas forcément une faute" in ligne[0]["dit"].lower()
    assert "relire" in ligne[0]["dit"].lower()


def test_le_reste_a_produire_est_rendu_meme_quand_tout_sort():
    """LA COLONNE QUI EMPÊCHE DE LIRE « UNE VALEUR EXISTE » COMME « LE TEXTE
    EST SATISFAIT ». Douze mois de mesure, une note signée, un vérificateur
    tiers : aucun calcul ne les remplace."""
    for l in E.sonder():
        assert (l["reste_a_produire"] or "").strip(), l["code"]
    assert "reste à produire" in E.analyse()["reserve"]


def test_une_etape_conforme_ne_dit_rien_de_plus():
    """Un rapport qui commente tout n'est plus lu là où il commente."""
    for l in E.sonder():
        if l["etat"] == "conforme":
            assert l["dit"] == ""


# ── 4. Le croisement avec les lacunes du fonds ────────────────────────────

def test_chaque_lacune_declaree_est_croisee_avec_un_texte():
    """Une lacune sans texte reste un constat ; avec le texte qui l'exige et
    les gisements ouverts de `lacunes.py`, elle devient une instruction de
    travail."""
    croisees = {c["lacune"] for c in E.CROISEMENTS}
    assert croisees == set(range(len(etat_art.LACUNES)))


def test_le_texte_de_la_lacune_est_celui_de_l_etat_de_l_art_mot_pour_mot():
    """Deux formulations qui divergent donneraient au lecteur deux versions du
    même trou, et il croirait à deux trous."""
    for c, brut in zip(E.croisements(), E.CROISEMENTS):
        assert c["lacune"] == etat_art.LACUNES[brut["lacune"]]


def test_chaque_croisement_nomme_des_textes_reels_et_leur_portee():
    for c in E.croisements():
        assert c["textes"]
        for t in c["textes"]:
            assert t["cle"] in DEC.TEXTES
            assert t["portee"] in DEC.PORTEES
        assert c["etape"] in {e["code"] for e in DEC.ETAPES}


def test_la_fin_de_vie_est_croisee_avec_les_textes_qui_l_exigent():
    """La lacune la plus récemment instruite : le renouvellement accéléré des
    accélérateurs se paie à la fin de vie, et rien ne l'exigeait."""
    fin = [c for c in E.croisements() if "fin de vie" in c["lacune"].lower()]
    assert fin
    cles = {t["cle"] for t in fin[0]["textes"]}
    assert {"deee", "agec"} <= cles


# ── 5. La route ───────────────────────────────────────────────────────────

def test_l_ecart_est_derriere_un_compte(anonyme):
    """Toute la famille `/api/datacenter/` est fermée : fermer la page sans
    fermer son interface ne protège rien."""
    assert anonyme.get("/api/datacenter/ecart-referentiel").status_code in (401, 403, 302)


def test_la_route_rend_l_analyse_et_sa_reserve(connecte):
    j = connecte.get("/api/datacenter/ecart-referentiel").get_json()
    assert j["ok"] is True
    assert len(j["etapes"]) == len(DEC.ETAPES)
    assert j["croisements"] and j["reserve"]
    assert set(j["resume"]) <= set(E.ETATS)
