"""L'AUTO-ÉVALUATION DE MATURITÉ OT — le seul endroit du site qui rende un
degré, et tout ce qui doit tenir pour qu'elle en ait le droit.

`checklist_62443` refuse d'annoncer un niveau, et il a raison : un compte de
cases n'en est pas un. Ce module en rend un, et la différence tient en une
phrase — LE NIVEAU N'EST PAS CALCULÉ, IL EST DÉCLARÉ. Quelqu'un choisit, parmi
six descriptions concrètes, celle qui correspond à ce qu'il peut MONTRER.

C'est un droit fragile. Il se perd de six façons, et ces contrôles gardent les
six :

  1. LE MOT « ASSESSMENT » NE DOIT PAS ÊTRE VOLÉ. La page promet un assessment
     conduit — entretiens, relevés, contradiction. Un formulaire qui s'en
     réclamerait vendrait la mise en page d'un travail qui n'a pas eu lieu.
  2. SANS RÉPONSE N'EST PAS ZÉRO. Zéro est une déclaration ; se taire en est
     une autre. Les confondre ferait dire au radar que le client n'a rien
     alors qu'il n'a rien DIT.
  3. L'ÉCHELLE SE DÉCRIT PAR CE QU'ON MONTRE. « Maturité moyenne » ne se
     choisit pas ; « écrit mais pas appliqué » se reconnaît.
  4. LE CLASSEMENT EST UN JUGEMENT, ET IL S'ANNONCE. Gravité et effort sont
     des jugements de ce cabinet ; chacun porte son motif écrit, sans quoi
     l'ordre serait arbitraire présenté comme une méthode.
  5. UN BLOC QUI NE SE CALCULE PAS LE DIT. Deux des cinq livrables de la page
     ne se dérivent pas de six curseurs. Les servir quand même fabriquerait
     un benchmark sans panel.
  6. L'EXPORT PASSE PAR LA MÊME PORTE QUE L'ÉCRAN. Un format de sortie ne doit
     jamais devenir le chemin de contournement d'un contrôle.
"""
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import app as A  # noqa: E402
import checklist_62443 as C  # noqa: E402
import maturite_ot as M  # noqa: E402
from conftest import ADMIN_EMAIL, _assurer_admin  # noqa: E402

H = {"Origin": "http://localhost", "Referer": "http://localhost/x"}

#: Une déclaration complète, tenue basse : c'est le cas réel — un site qui n'a
#: jamais rien fait n'ouvre pas cette page.
BAS = {"gouvernance": 1, "architecture": 1, "acces": 2,
       "protection": 3, "detection": 0, "fournisseurs": 2}


@pytest.fixture
def client():
    _assurer_admin()
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["user_email"] = ADMIN_EMAIL
    A._ip_rate._hits.clear()
    yield c
    A._ip_rate._hits.clear()


def _apo(s):
    """L'apostrophe est droite dans les sources, courbe au rendu."""
    return s.replace("’", "'")


def _plat(x, chemin=""):
    """Toutes les paires (chemin, valeur) d'une structure — pour chercher un
    mot AUSSI BIEN dans une clé que dans une valeur."""
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _plat(v, chemin + "." + str(k))
    elif isinstance(x, (list, tuple)):
        for i, v in enumerate(x):
            yield from _plat(v, chemin + "[%d]" % i)
    else:
        yield chemin, x


# ═══════════════════════════════════════════════════════════════════════════
#  1. LE MOT « ASSESSMENT » N'EST PAS VOLÉ
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_le_refus_ouvre_le_document_avant_tout_chiffre():
    """LE DOCUMENT CIRCULE SANS SA PAGE. Il est transféré, imprimé, joint à un
    comité, relu six mois plus tard par quelqu'un qui n'a jamais vu ce site.
    Si la réserve est en pied de page, elle arrive après la décision.

    Le contrôle ne se contente pas de la trouver : il exige qu'AUCUN degré ne
    la précède."""
    md = _apo(M.markdown(BAS))
    i_refus = md.index(_apo(M.REFUS_ASSESSMENT)[:60])

    # Le premier chiffre de degré rencontré dans le document.
    chiffres = [m.start() for m in re.finditer(r"\b[0-5] — (Rien|Ponctuel|Écrit|Appliqué|Mesuré|Tenu)", md)]
    assert chiffres, "aucun degré dans le document : le contrôle ne prouve rien"
    assert i_refus < min(chiffres), (
        "un degré apparaît avant la réserve — le lecteur pressé aura vu le "
        "chiffre et pas ce qu'il vaut")


def test_le_refus_dit_ce_qui_manque_pas_seulement_que_ca_manque():
    """« Ceci n'est pas un assessment » sans dire ce qu'un assessment ferait
    de plus est une clause de style. Le lecteur doit apprendre la différence."""
    t = _apo(M.REFUS_ASSESSMENT).lower()
    for mot in ("entretien", "preuve", "contradiction"):
        assert mot in t, "le refus ne nomme pas « %s »" % mot
    assert "auto-évaluation" in t or "auto-evaluation" in t


def test_la_reserve_voyage_dans_chaque_reponse_pas_a_cote():
    """Servie à part, la réserve resterait sur la page pendant que le chiffre,
    lui, partirait en réunion."""
    for r in (M.evaluer(BAS), M.plan(BAS), M.referentiel()):
        assert _apo(M.REFUS_ASSESSMENT) in _apo(r["ce_que_ce_n_est_pas"])


def test_aucune_cle_ne_promet_un_assessment():
    """LE DANGER N'EST PAS LA PHRASE, C'EST LA CLÉ. Un client d'API qui lirait
    `assessment` afficherait « assessment » quoi qu'en dise la note d'à côté."""
    for chemin, _ in _plat(M.plan(BAS)):
        assert "assessment" not in chemin.lower(), (
            "la clé %s promet un assessment" % chemin)


def test_le_mot_ML_n_est_pas_employe_comme_resultat():
    """La 62443-2-4 a quatre ML et ils s'appliquent au programme d'un
    PRESTATAIRE. Les recopier ici ferait croire à une équivalence."""
    for l in M.evaluer(BAS)["domaines"]:
        assert not re.search(r"\bML\s*\d", str(l["niveau_nom"]) + str(l["cible_nom"]))
    # Le seul endroit où « ML » a le droit d'apparaître est le voisinage, et
    # il porte le mot « approximative ».
    assert "ML" in M.VOISINAGES
    assert "APPROXIMATIVE" in M.VOISINAGES or "approximative" in M.VOISINAGES


def test_les_degres_ne_sont_pas_nommes_comme_ceux_de_la_62443():
    """Six degrés, des noms qui appartiennent à ce cabinet."""
    assert len(M.ECHELLE) == 6
    noms = {e["nom"].lower() for e in M.ECHELLE}
    for emprunte in ("initial", "repeatable", "defined", "managed", "optimized",
                     "optimisé"):
        assert emprunte not in noms, (
            "« %s » emprunte le vocabulaire d'une autre échelle" % emprunte)


# ═══════════════════════════════════════════════════════════════════════════
#  2. SANS RÉPONSE N'EST PAS ZÉRO
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_un_domaine_muet_n_est_pas_compte_pour_zero():
    """Zéro est une déclaration — « rien n'existe ». Se taire en est une
    autre. Le radar qui les confond dessine une installation qui n'existe
    pas, et c'est celle-là qui part en comité."""
    ev = M.evaluer({"gouvernance": 3})
    par_cle = {l["cle"]: l for l in ev["domaines"]}

    assert par_cle["architecture"]["niveau"] is None
    assert par_cle["architecture"]["ecart"] is None, (
        "un écart a été calculé sur un domaine sans réponse")
    assert par_cle["architecture"]["poids"] is None
    assert "architecture" in ev["manquants"]

    # ET LA MOYENNE NE LES COMPTE PAS. Une moyenne sur six quand un seul
    # domaine est renseigné donnerait 0,5 au lieu de 3.
    assert ev["moyenne_declaree"] == 3.0
    assert ev["repondus"] == 1 and ev["sur"] == 6


def test_zero_declare_est_bien_un_zero_lui():
    """La symétrie du contrôle précédent : si `None` et `0` se confondaient
    dans l'autre sens, un client qui déclare n'avoir rien verrait son domaine
    traité comme sans réponse et disparaître du plan."""
    ev = M.evaluer({"detection": 0})
    l = next(x for x in ev["domaines"] if x["cle"] == "detection")
    assert l["niveau"] == 0
    assert l["ecart"] == l["cible"], "un zéro déclaré ne produit pas d'écart"
    assert "detection" not in ev["manquants"]
    assert l["cle"] in [x["cle"] for x in ev["a_combler"]]


def test_la_lecture_dit_combien_de_domaines_manquent():
    """Un texte de synthèse qui tairait les domaines muets laisserait croire à
    un tableau complet."""
    t = M.evaluer({"gouvernance": 3})["lecture"]
    assert "1 domaine(s) sur 6" in t
    assert "zéro" in t.lower(), (
        "la lecture ne dit pas que les manquants ne sont pas à zéro")


def test_aucun_domaine_renseigne_le_dit_au_lieu_de_rendre_un_tableau_vide():
    ev = M.evaluer({})
    assert ev["ok"] is True
    assert ev["moyenne_declaree"] is None
    assert ev["repondus"] == 0
    assert "Aucun domaine" in ev["lecture"]


# ═══════════════════════════════════════════════════════════════════════════
#  3. L'ÉCHELLE SE DÉCRIT PAR CE QU'ON PEUT MONTRER
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_chaque_degre_se_decrit_par_une_preuve():
    """« Maturité moyenne » ne se choisit pas de bonne foi : chacun se croit
    moyen. « Écrit et validé, mais pas appliqué partout » se reconnaît, et se
    conteste.

    Le contrôle refuse les adjectifs d'auto-appréciation dans la description
    des degrés — le seul vocabulaire admis est celui de ce qui existe."""
    interdits = ("bon niveau", "satisfaisant", "correct", "insuffisant",
                 "faible maturité", "excellent", "mauvais")
    for e in M.ECHELLE:
        d = _apo(e["dit"]).lower()
        assert len(d) >= 60, "le degré %d se décrit en moins d'une phrase" % e["n"]
        for mot in interdits:
            assert mot not in d, (
                "le degré %d s'apprécie (« %s ») au lieu de se constater"
                % (e["n"], mot))


def test_le_degre_le_plus_haut_exige_un_fait_pas_une_intention():
    """C'est le degré qu'on s'attribue le plus volontiers. Il doit demander
    quelque chose qui se raconte mal."""
    d = _apo(M.ECHELLE[5]["dit"]).lower()
    assert "réellement" in d or "reellement" in d
    assert "au moins une fois" in d


def test_l_echelle_est_continue_et_bornee():
    assert [e["n"] for e in M.ECHELLE] == list(range(M.MINI, M.MAXI + 1))
    for l in M.evaluer({"gouvernance": 99, "acces": -3})["domaines"]:
        assert l["niveau"] is None, "un degré hors échelle a été accepté"


def test_un_degre_non_entier_est_ecarte_pas_arrondi():
    """Arrondir « 2,5 » à 3 attribuerait au client un degré qu'il n'a pas
    choisi, dans le sens qui l'arrange."""
    l = next(x for x in M.evaluer({"gouvernance": "2,5"})["domaines"]
             if x["cle"] == "gouvernance")
    assert l["niveau"] is None


# ═══════════════════════════════════════════════════════════════════════════
#  4. LE CLASSEMENT EST UN JUGEMENT, ET IL S'ANNONCE
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_chaque_gravite_et_chaque_effort_porte_son_motif():
    """Une table de jugements sans motifs est un classement arbitraire
    présenté comme une méthode. Le lecteur doit pouvoir contester chaque
    ligne — c'est la seule chose qui distingue un avis d'un oracle."""
    for d in M.DOMAINES:
        for champ in ("gravite_dit", "effort_dit", "cible_dit"):
            t = _apo(d[champ]).strip()
            assert len(t) >= 60, "%s : %s tient en moins d'une phrase" % (d["cle"], champ)
            # Un motif qui ne fait que répéter la note n'explique rien.
            assert not re.fullmatch(r"[^a-zA-Zà-ÿ]*\d[^a-zA-Zà-ÿ]*", t)


def test_le_document_annonce_que_l_ordre_est_un_jugement_de_ce_cabinet():
    """Servi sans cette phrase, l'ordre passerait pour une dérivation."""
    md = _apo(M.markdown(BAS)).lower()
    assert "jugement de ce cabinet" in md
    assert "ne note personne" in md or "il ne note personne" in md


def test_l_effort_divise_et_la_gravite_multiplie():
    """Un chantier de dix-huit mois ne se met pas en tête d'une feuille de
    route qu'on veut voir bouger. Le contrôle vérifie le SENS des deux
    facteurs sur des cas construits, pas la formule recopiée."""
    ev = M.evaluer(BAS)
    par = {l["cle"]: l for l in ev["domaines"]}
    # gouvernance : écart 3, gravité 5, effort 2  → 7,5
    # architecture : écart 3, gravité 5, effort 5 → 3,0
    # Même écart, même gravité : c'est l'effort seul qui les sépare.
    assert par["gouvernance"]["ecart"] == par["architecture"]["ecart"]
    assert par["gouvernance"]["gravite"] == par["architecture"]["gravite"]
    assert par["gouvernance"]["poids"] > par["architecture"]["poids"], (
        "à écart et gravité égaux, le chantier le plus lourd ne passe pas "
        "derrière : l'effort ne divise pas")
    assert ev["a_combler"][0]["cle"] == "gouvernance"


def test_la_moyenne_est_servie_et_desamorcee_dans_la_meme_phrase():
    """La taire ne l'empêcherait pas d'être calculée de tête, et plus mal.
    Elle doit donc arriver avec ce qu'elle vaut."""
    md = _apo(M.markdown(BAS))
    i = md.index("Moyenne des degrés")
    fin = md.index("\n", i)
    phrase = md[i:fin].lower()
    assert "n'est pas une note" in phrase
    assert "1,5" in phrase, "le séparateur décimal n'est pas la virgule"


def test_la_cible_par_defaut_se_declare_comme_telle():
    """Une cible recommandée présentée comme un choix du client ferait passer
    l'avis du cabinet pour une donnée d'entrée."""
    ev = M.evaluer(BAS)
    assert all(l["cible_par_defaut"] for l in ev["domaines"])
    ev2 = M.evaluer(BAS, {"gouvernance": 5})
    par = {l["cle"]: l for l in ev2["domaines"]}
    assert par["gouvernance"]["cible"] == 5
    assert par["gouvernance"]["cible_par_defaut"] is False
    # UNE CIBLE HORS ÉCHELLE EST ÉCARTÉE, ET LA RECOMMANDATION REPREND LA
    # MAIN — en le disant. Prétendre le contraire ferait passer pour un choix
    # du client une valeur qu'il n'a pas obtenue.
    ev3 = M.evaluer(BAS, {"gouvernance": 42})
    par3 = {l["cle"]: l for l in ev3["domaines"]}
    assert par3["gouvernance"]["cible"] == 4
    assert par3["gouvernance"]["cible_par_defaut"] is True

    # LE CAS QUI SÉPARE LES DEUX LECTURES DU DRAPEAU, et le seul : le client
    # choisit EXACTEMENT la valeur recommandée. Comparer la cible retenue à la
    # recommandation — au lieu de regarder s'il a choisi — répondrait « c'est
    # la recommandation » et effacerait son geste. Sans ce cas, une telle
    # implémentation passe les trois vérifications ci-dessus sans broncher :
    # elle ne s'en écarte nulle part ailleurs.
    ev4 = M.evaluer(BAS, {"gouvernance": 4})
    par4 = {l["cle"]: l for l in ev4["domaines"]}
    assert par4["gouvernance"]["cible"] == 4
    assert par4["gouvernance"]["cible_par_defaut"] is False, (
        "une cible explicitement choisie est présentée comme la "
        "recommandation du cabinet")


def test_un_domaine_inconnu_est_refuse_pas_ignore():
    """Un total qui compterait des domaines inexistants ne se recouperait
    pas."""
    r = M.evaluer({"cantine": 3})
    assert r["ok"] is False and r["erreur"] == "domaines_inconnus"
    assert "cantine" in r["message"]


def test_les_domaines_restent_ceux_de_la_checklist():
    """Deux vocabulaires pour la même chose sur le même site obligeraient le
    lecteur à traduire de tête."""
    assert M.ORDRE == [s["cle"] for s in C.SECTIONS]


# ═══════════════════════════════════════════════════════════════════════════
#  5. LE PLAN VA DEGRÉ PAR DEGRÉ
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_aucune_etape_ne_saute_un_degre():
    """« Passer de 1 à 4 » n'est pas une étape, c'est un vœu. Une feuille de
    route dont aucune ligne ne se termine ne se suit pas."""
    p = M.plan(BAS)
    assert p["n_etapes"] > 0
    par_dom = {}
    for e in p["etapes"]:
        assert e["vers"] == e["de"] + 1, (
            "l'étape %s saute de %d à %d" % (e["domaine"], e["de"], e["vers"]))
        par_dom.setdefault(e["domaine"], []).append(e["de"])
    # LA CHAÎNE EST COMPLÈTE : du degré déclaré à la cible, sans trou.
    for l in p["a_combler"]:
        assert par_dom[l["cle"]] == list(range(l["niveau"], l["cible"])), (
            "la chaîne de %s a un trou" % l["cle"])


def test_chaque_etape_dit_ce_qu_il_faut_pouvoir_montrer():
    """Une étape sans preuve attendue est un intitulé."""
    for e in M.plan(BAS)["etapes"]:
        assert e["ce_qu_il_faut"] == M.ECHELLE[e["vers"]]["dit"]
        assert len(_apo(e["ce_qu_il_faut"])) >= 60


def test_un_domaine_a_sa_cible_ne_produit_aucune_etape():
    p = M.plan({"protection": 3})
    assert p["etapes"] == []
    assert "protection" in p["atteints"]


def test_tout_a_la_cible_renvoie_a_ce_qui_ne_se_declare_pas():
    """C'est le moment où une auto-évaluation ne suffit plus, et le seul
    moment où la page a le droit de renvoyer à un assessment conduit."""
    ev = M.evaluer({d["cle"]: d["cible"] for d in M.DOMAINES})
    assert ev["a_combler"] == []
    t = ev["lecture"].lower()
    assert "déclaré" in t and "constate" in t


# ═══════════════════════════════════════════════════════════════════════════
#  6. UN BLOC QUI NE SE CALCULE PAS LE DIT
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_le_benchmark_refuse_de_se_calculer():
    """Un « vous êtes au-dessus de la moyenne » sans panel serait la pire
    ligne du document : invérifiable, flatteuse, et citée en comité."""
    d = M.LIVRABLES["mat-benchmark"]
    assert d["calculable"] is False
    assert d["ce_qu_il_faudrait"], "le refus ne dit pas ce qu'il faudrait"
    assert "panel" in _apo(d["ce_qu_il_faudrait"]).lower()
    for l in M.livrables(BAS)["livrables"]:
        if l["id"] == "mat-benchmark":
            assert l["pret"] is False


def test_un_livrable_non_calculable_n_est_jamais_pret_meme_tout_rempli():
    """Le piège serait qu'il s'active quand le formulaire est complet."""
    plein = {d["cle"]: 3 for d in M.DOMAINES}
    for l in M.livrables(plein)["livrables"]:
        if not l["calculable"]:
            assert l["pret"] is False, "%s s'active sans données" % l["id"]


def test_un_livrable_calculable_attend_au_moins_une_reponse():
    """Un radar sans un seul degré déclaré serait un cadre vide."""
    for l in M.livrables()["livrables"]:
        assert l["pret"] is False
    for l in M.livrables({"gouvernance": 2})["livrables"]:
        if l["calculable"]:
            assert l["pret"] is True


def test_les_intitules_viennent_de_livrables_py_jamais_recopies():
    """Deux listes du même objet divergent au premier ajout : la page
    afficherait un titre périmé sans que rien ne le signale."""
    import livrables as LV
    ref = {l["id"]: l["label"] for l in LV.TYPES}
    for l in M.livrables(BAS)["livrables"]:
        assert l["label"] == ref[l["id"]]


def test_un_livrable_declare_ici_et_absent_de_livrables_py_leve():
    """La garde qui empêche la divergence de passer inaperçue."""
    sauve = dict(M.LIVRABLES)
    try:
        M.LIVRABLES["mat-fantome"] = {"calculable": True, "dit": "x"}
        with pytest.raises(ValueError, match="absent de livrables.py"):
            M.livrables(BAS)
    finally:
        M.LIVRABLES.clear()
        M.LIVRABLES.update(sauve)


def test_le_document_nomme_ce_qu_il_ne_produit_pas():
    """Un document qui tairait ses deux trous laisserait croire qu'il couvre
    les cinq blocs de la page."""
    md = _apo(M.markdown(BAS))
    for cle, d in M.LIVRABLES.items():
        if not d["calculable"]:
            assert _apo(d["ce_qu_il_faudrait"])[:40] in md, (
                "%s ne dit pas dans le document ce qu'il faudrait" % cle)


# ═══════════════════════════════════════════════════════════════════════════
#  7. CE QUE LE FORMULAIRE NE COTE PAS EST NOMMÉ
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_les_domaines_hors_portee_sont_nommes():
    """La page promettait huit domaines. Deux n'ont aucun référentiel écrit
    derrière eux ici. Les faire disparaître réduirait la promesse en silence ;
    les coter fabriquerait un chiffre. Ils sont donc nommés."""
    noms = {h["nom"] for h in M.HORS_PORTEE}
    assert "Continuité & résilience" in noms
    assert "Culture & compétences" in noms
    for h in M.HORS_PORTEE:
        assert len(_apo(h["pourquoi"])) >= 40
        assert len(_apo(h["ou_ca_se_constate"])) >= 40, (
            "« %s » est écarté sans dire où cela se constate" % h["nom"])
    md = _apo(M.markdown(BAS))
    for h in M.HORS_PORTEE:
        assert h["nom"] in md


def test_un_hors_portee_sans_ou_ca_se_constate_leve():
    """Un refus sans suite n'apprend rien au lecteur."""
    sauve = list(M.HORS_PORTEE)
    try:
        M.HORS_PORTEE.append({"nom": "X", "pourquoi": "a" * 50,
                              "ou_ca_se_constate": "court"})
        with pytest.raises(ValueError, match="ou_ca_se_constate"):
            M._verifier()
    finally:
        M.HORS_PORTEE[:] = sauve


def test_les_controles_d_acces_sont_dans_la_portee():
    """Le modèle décoratif de la page les oubliait — c'est la porte la plus
    empruntée. Le formulaire, lui, les cote."""
    assert "acces" in M.ORDRE
    assert any("accès" in l["nom"] or "acces" in l["nom"]
               for l in M.evaluer(BAS)["domaines"])


# ═══════════════════════════════════════════════════════════════════════════
#  8. LES ROUTES — MÊME PORTE QUE L'ÉCRAN
# ═══════════════════════════════════════════════════════════════════════════

def test_le_referentiel_demande_une_session(client):
    A._ip_rate._hits.clear()
    anon = A.app.test_client()
    assert anon.get("/api/maturite-ot/referentiel").status_code in (302, 401, 403)


def test_le_referentiel_sert_l_echelle_et_les_domaines(client):
    r = client.get("/api/maturite-ot/referentiel")
    assert r.status_code == 200
    d = r.get_json()["referentiel"]
    assert len(d["echelle"]) == 6
    assert [x["cle"] for x in d["domaines"]] == list(M.ORDRE)
    assert d["ce_que_ce_n_est_pas"]
    assert len(d["hors_portee"]) == 2
    # Chaque domaine arrive avec son nom et sa partie de la norme : la page
    # n'a rien à recopier.
    for x in d["domaines"]:
        assert x["nom"] and x["partie"]


def test_evaluer_rend_le_plan_et_les_livrables(client):
    r = client.post("/api/maturite-ot/evaluer", json={"niveaux": BAS}, headers=H)
    assert r.status_code == 200
    d = r.get_json()
    assert d["ok"] and d["n_etapes"] > 0
    assert len(d["livrables"]) == 5
    assert d["ce_que_ce_n_est_pas"]


def test_evaluer_refuse_un_domaine_inconnu(client):
    r = client.post("/api/maturite-ot/evaluer",
                    json={"niveaux": {"cantine": 2}}, headers=H)
    assert r.status_code == 400
    assert r.get_json()["erreur"] == "domaines_inconnus"


def test_LE_POINT_QUI_DECIDE_l_export_refuse_ce_que_l_ecran_refuse(client):
    """Un format de sortie ne doit jamais devenir le chemin de contournement
    d'un contrôle : le domaine inconnu refusé à l'écran doit l'être aussi en
    PDF, et pour le même motif."""
    for fmt in ("pdf", "docx"):
        r = client.post("/api/maturite-ot/emporter",
                        json={"format": fmt, "niveaux": {"cantine": 2}},
                        headers=H)
        assert r.status_code == 400, "l'export %s a laissé passer" % fmt
        assert r.get_json()["erreur"] == "domaines_inconnus"


def test_l_export_refuse_un_formulaire_vide(client):
    """Un document sans une seule réponse circulerait comme les autres en ne
    disant rien."""
    r = client.post("/api/maturite-ot/emporter",
                    json={"format": "pdf", "niveaux": {}}, headers=H)
    assert r.status_code == 400
    assert r.get_json()["error"] == "rien_de_declare"


def test_l_export_refuse_un_format_inconnu(client):
    r = client.post("/api/maturite-ot/emporter",
                    json={"format": "xls", "niveaux": BAS}, headers=H)
    assert r.status_code == 400
    assert r.get_json()["error"] == "format_inconnu"


def test_l_export_pdf_rend_un_pdf(client):
    r = client.post("/api/maturite-ot/emporter",
                    json={"format": "pdf", "niveaux": BAS}, headers=H)
    assert r.status_code == 200
    assert r.data.startswith(b"%PDF-")
    assert "attachment" in r.headers.get("Content-Disposition", "")


def test_l_export_docx_rend_un_docx(client):
    r = client.post("/api/maturite-ot/emporter",
                    json={"format": "docx", "niveaux": BAS}, headers=H)
    assert r.status_code == 200
    assert r.data.startswith(b"PK\x03\x04")


def test_LE_POINT_QUI_DECIDE_l_intitule_des_documents_porte_ses_accents():
    """`meta["label"]` part dans l'EN-TÊTE DE CHAQUE PAGE et dans les
    propriétés du fichier. Écrit sans accents — « Auto-evaluation de maturite
    OT » — il coiffe un corps de texte accentué, et se lit comme une chaîne de
    production qui n'a pas été relue. Le lecteur qui le remarque doute ensuite
    du reste.

    LE CONTRÔLE PORTE SUR TOUS LES EXPORTS, PAS SUR LES DEUX QU'ON VIENT
    D'ÉCRIRE : le défaut n'a rien de particulier à ceux-là, et le prochain
    livrable ajouté doit tomber dessus tout seul."""
    src = open(os.path.join(ICI, "app.py"), encoding="utf-8").read()
    fautifs = []
    for m in re.finditer(r'"label":\s*"([^"]+)"', src):
        t = m.group(1)
        # Un mot français qui devrait porter un accent et n'en porte aucun.
        for mot in ("evaluation", "maturite", "etat", "strategie", "developpement",
                    "perimetre", "reglementaire", "securite", "reference",
                    "conformite", "operationnel", "systeme"):
            if re.search(r"\b" + mot + r"\b", t.lower()):
                fautifs.append((t, mot))
    assert not fautifs, (
        "intitulé(s) de document sans accents : %s"
        % "; ".join("« %s » (%s)" % f for f in fautifs))


def test_l_export_demande_une_session(client):
    A._ip_rate._hits.clear()
    anon = A.app.test_client()
    r = anon.post("/api/maturite-ot/emporter",
                  json={"format": "pdf", "niveaux": BAS}, headers=H)
    assert r.status_code in (302, 401, 403)


# ═══════════════════════════════════════════════════════════════════════════
#  9. LA PAGE FAIT CE QU'ELLE PROMET
# ═══════════════════════════════════════════════════════════════════════════

def _page():
    with open(os.path.join(ICI, "maturite-ot.html"), encoding="utf-8") as f:
        return f.read()


#: LES HUIT CARTES DÉCORATIVES QUE LA PAGE PORTAIT. Aucune n'était remplissable,
#: aucune ne mentionnait les contrôles d'accès, et deux n'avaient derrière elles
#: aucun référentiel écrit permettant de les coter.
ANCIENNES_CARTES = [
    "Gouvernance &amp; organisation", "Gestion des actifs OT",
    "Gestion des risques", "Architecture &amp; segmentation",
    "Détection &amp; réponse", "Gestion des tiers",
    "Continuité &amp; résilience", "Culture &amp; compétences",
]


def test_LE_POINT_QUI_DECIDE_la_page_ne_porte_aucune_liste_de_domaines_ecrite_a_la_main():
    """La page listait huit domaines décoratifs au-dessus de blocs inertes. Un
    visiteur qui lit huit cartes puis remplit six champs se demande où sont
    passées les deux autres, et il a raison.

    LE CONTRÔLE EST NÉGATIF, ET C'EST VOLONTAIRE. Vérifier que les six noms du
    formulaire sont DANS la page exigerait de les y recopier — c'est-à-dire
    d'y créer la seconde liste que `test_la_page_ne_recopie_pas_l_echelle`
    interdit, et qui se périmerait au premier ajout. Ce qui doit être vrai est
    l'inverse : la page n'énumère AUCUN domaine de son côté, et les reçoit
    tous de la route."""
    h = _page()
    for carte in ANCIENNES_CARTES:
        assert "<h3>%s</h3>" % carte not in h, (
            "la carte décorative « %s » est encore écrite dans la page" % carte)
    # Et la page va bien les chercher là où ils sont écrits une seule fois.
    assert "REF.domaines.forEach" in h, (
        "la page ne parcourt jamais les domaines servis par la route")


def test_les_domaines_hors_portee_sont_affiches_et_viennent_de_la_route():
    """« Continuité & résilience » et « Culture & compétences » étaient deux
    des huit cartes. Les supprimer en silence aurait rétréci la promesse sans
    le dire ; ils sont servis par la route et rendus par la page."""
    h = _page()
    assert 'id="mo-hors"' in h, "la page n'a pas d'emplacement pour le hors portée"
    assert re.search(r"(?m)^\s*REF\.hors_portee\.forEach", h), (
        "la page ne rend jamais les domaines hors portée servis par la route")
    assert "mo-hors" in h.split("REF.hors_portee.forEach")[1][:800], (
        "le hors portée est parcouru mais n'est écrit nulle part")


def test_les_cinq_blocs_ne_renvoient_plus_tous_a_l_espace_administrateur():
    """C'était le défaut : pour un visiteur, la section entière était inerte.
    Trois blocs se calculent depuis ses propres réponses."""
    h = _page()
    for cle in sorted(k for k, v in M.LIVRABLES.items() if v["calculable"]):
        assert "/admin/livrables?type=%s" % cle not in h, (
            "%s renvoie encore à l'espace administrateur alors qu'il se "
            "calcule ici" % cle)


def test_la_page_porte_le_refus_avant_le_formulaire():
    """Sur la page comme dans le document : la réserve avant les curseurs. Le
    texte vient de la route — le vérifier ici en recopiant en ferait une
    seconde copie — mais SA PLACE, elle, est une propriété de la page."""
    h = _page()
    i_refus = h.index('id="mo-refus"')
    i_form = h.index('id="mo-form"')
    assert i_refus < i_form, (
        "la réserve est placée après le formulaire : elle arriverait après la "
        "décision")
    # Et elle est bien remplie depuis la route, pas laissée vide.
    assert "REF.ce_que_ce_n_est_pas" in h
    assert "mo-refus" in h.split("REF.ce_que_ce_n_est_pas")[0][-400:], (
        "la réserve est lue mais écrite ailleurs que dans son emplacement")


def test_la_page_appelle_les_trois_routes():
    """Un formulaire qui n'appellerait rien serait une maquette."""
    h = _page()
    for route in ("/api/maturite-ot/referentiel", "/api/maturite-ot/evaluer",
                  "/api/maturite-ot/emporter"):
        assert route in h, "la page n'appelle jamais %s" % route


def test_la_page_ne_recopie_pas_l_echelle():
    """Deux tables du même objet divergent au premier ajout. L'échelle vient
    de la route ; la page ne doit pas en porter une seconde."""
    h = _apo(_page())
    dits = [_apo(e["dit"])[:50] for e in M.ECHELLE]
    presents = [d for d in dits if d in h]
    assert not presents, (
        "la page recopie la description de %d degré(s) : %s"
        % (len(presents), presents[:1]))
