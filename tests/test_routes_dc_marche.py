"""Les quatre routes qui prolongent l'ingénierie — portes, entrées, réponses.

CE QUI EST ÉPROUVÉ ICI, et qui ne l'est pas dans les tests de modules :

  · LA PORTE. Le criblage et le plan de travaux sont ouverts à un compte
    connecté ; l'analyse d'un dossier de consultation ne l'est pas — elle rend
    le CONTENU des pièces d'un client, sous forme de citations.
  · LA LECTURE DES ENTRÉES. Une saisie illisible doit RESSORTIR, pas
    disparaître dans un champ absent : un criblage reparti sur un champ
    silencieusement écarté annoncerait « aucune rubrique atteinte » à
    quelqu'un qui vient de saisir une puissance.
  · CE QUE LA PAGE REÇOIT. Les listes déroulantes de la page sont construites
    sur ces réponses ; une clé absente les laisse vides sans rien signaler.
"""
import base64
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

ORIGINE = {"Origin": "http://localhost"}


# ── Les portes ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("chemin", ["/api/datacenter/icpe",
                                    "/api/datacenter/travaux",
                                    "/api/datacenter/marche/candidature",
                                    "/api/datacenter/marche/analyser"])
def test_un_visiteur_anonyme_n_atteint_aucune_des_quatre(anonyme, chemin):
    r = anonyme.post(chemin, json={}, headers=ORIGINE)
    assert r.status_code in (401, 403), (chemin, r.status_code)


def test_l_analyse_d_un_dossier_de_consultation_exige_l_administration(connecte):
    """ELLE REND LE CONTENU DES PIÈCES DU CLIENT, sous forme de citations.
    L'ouvrir à tout compte connecté reviendrait à servir un dossier de
    consultation à qui a une session."""
    r = connecte.post("/api/datacenter/marche/analyser",
                      json={"documents": [{"nom": "RC.pdf", "texte": "x"}]},
                      headers=ORIGINE)
    assert r.status_code in (401, 403), r.status_code


def test_le_criblage_et_le_plan_sont_ouverts_a_un_compte_client(connecte):
    """Ils ne rendent que des tables et un calcul sur les grandeurs saisies :
    rien qui appartienne à un tiers."""
    for chemin in ("/api/datacenter/icpe", "/api/datacenter/travaux",
                   "/api/datacenter/marche/candidature"):
        r = connecte.post(chemin, json={}, headers=ORIGINE)
        assert r.status_code == 200, (chemin, r.status_code)


# ── Le criblage ICPE ───────────────────────────────────────────────────────

def test_un_criblage_vide_rend_cinq_rubriques_sans_donnee(connecte):
    j = connecte.post("/api/datacenter/icpe", json={}, headers=ORIGINE).get_json()
    assert j["ok"]
    assert j["criblage"]["regime_site"] == "hors"
    assert all(r["etat"] == "a_verifier" for r in j["rubriques"])


def test_le_criblage_lit_le_profil_du_moteur_et_le_sien(connecte):
    """Les deux profils se rejoignent : le mode de refroidissement vient du
    moteur, la puissance des groupes de ce module. Les lire séparément puis
    les fondre évite de dupliquer une définition de champ."""
    j = connecte.post("/api/datacenter/icpe", json={
        "refroidissement": "tour_evaporative", "puissance_it_kw": "4000",
        "groupes_puissance_thermique_mw": "25",
    }, headers=ORIGINE).get_json()
    codes = {r["code"]: r for r in j["rubriques"] if r["etat"] == "declenchee"}
    assert "2921" in codes, j["rubriques"]
    assert "2910" in codes
    assert j["criblage"]["regime_site"] == "A"


def test_une_saisie_illisible_ressort_au_lieu_de_disparaitre(connecte):
    """LE DÉFAUT QUE CETTE RÈGLE EMPÊCHE. Un champ illisible tombé dans un
    `continue` muet ferait annoncer « aucune rubrique atteinte » à quelqu'un
    qui vient de saisir une puissance — un résultat IDENTIQUE à celui d'une
    saisie valide, et rassurant à tort."""
    j = connecte.post("/api/datacenter/icpe",
                      json={"groupes_puissance_thermique_mw": "vingt-cinq"},
                      headers=ORIGINE).get_json()
    assert j["rejets"], j
    assert j["rejets"][0]["champ"] == "groupes_puissance_thermique_mw"
    assert j["lecture"]


def test_la_question_sur_l_hydrogene_distingue_le_non_du_non_pose(connecte):
    """« Non » abaisse la rubrique ; « non précisé » ne l'abaisse pas. Les
    confondre ferait manquer la rubrique la plus souvent oubliée d'un centre
    de données."""
    def rubriques(charge):
        d = {"batteries_charge_kw": "100"}
        if charge is not None:
            d["batteries_hydrogene"] = charge
        j = connecte.post("/api/datacenter/icpe", json=d,
                          headers=ORIGINE).get_json()
        return {r["code"] for r in j["rubriques"] if r["etat"] == "declenchee"}
    assert "2925" in rubriques(None)
    assert "2925" in rubriques("oui")
    assert "2925" not in rubriques(False)


def test_le_criblage_sert_ses_champs_pour_que_la_page_les_dessine(connecte):
    j = connecte.post("/api/datacenter/icpe", json={},
                      headers=ORIGINE).get_json()
    assert j["champs"]
    for c in j["champs"]:
        assert c["id"] and c["label"] and c["rubrique"]


def test_le_criblage_sert_les_consequences_de_mission(connecte):
    """Le criblage dit le régime ; c'est la mission qui intéresse le maître
    d'ouvrage."""
    j = connecte.post("/api/datacenter/icpe",
                      json={"charge_frigorigene_kg": "500"},
                      headers=ORIGINE).get_json()
    assert j["mission"]["actions"]
    assert j["mission"]["reserve"]


# ── Le plan de travaux ─────────────────────────────────────────────────────

def test_le_plan_de_travaux_refuse_une_nature_inconnue(connecte):
    """Une nature inconnue rendrait un plan de construction neuve à quelqu'un
    qui a saisi un rétrofit — sans que rien ne le dise."""
    r = connecte.post("/api/datacenter/travaux",
                      json={"nature_travaux": "demolition"}, headers=ORIGINE)
    assert r.status_code == 400
    j = r.get_json()
    assert j["error"] == "nature_inconnue"
    assert j["natures"], "et il dit lesquelles sont admises"


def test_un_retrofit_rend_ses_prealables_bloquants(connecte):
    j = connecte.post("/api/datacenter/travaux",
                      json={"nature_travaux": "retrofit"},
                      headers=ORIGINE).get_json()
    cles = {x["cle"] for x in j["plan"]["prealables"]}
    assert {"phasage", "releve"} <= cles, cles
    assert j["nature_detail"]["nom"]


def test_sans_commissioning_les_essais_restent_avec_leur_orphelinat(connecte):
    j = connecte.post("/api/datacenter/travaux",
                      json={"commissioning": False},
                      headers=ORIGINE).get_json()
    orphelines = [o for o in j["plan"]["operations"] if o.get("sans_titulaire")]
    assert orphelines, [o["cle"] for o in j["plan"]["operations"]]


def test_le_plan_sert_les_natures_pour_la_liste_deroulante(connecte):
    """La page construit sa liste sur cette réponse : sans elle, elle
    afficherait une liste vide sans rien signaler."""
    j = connecte.post("/api/datacenter/travaux", json={},
                      headers=ORIGINE).get_json()
    assert set(j["natures"]) == {"neuf", "fit_out", "retrofit"}
    assert j["natures_note"]


# ── L'analyse d'un dossier de consultation ─────────────────────────────────

RC = ("REGLEMENT DE LA CONSULTATION\n"
      "La date et heure limites de reception des offres sont fixees au "
      "12 septembre 2026 a 12 h 00.\n"
      "Criteres de jugement : valeur technique 60 %, prix 40 %.\n")


def _fichier(nom, texte):
    return {"nom": nom,
            "contenu": base64.b64encode(texte.encode("utf-8")).decode("ascii"),
            "extension": ".txt"}


def test_un_fichier_transmis_est_analyse_sans_etre_depose(admin):
    """On lit un dossier de consultation AVANT de décider s'il vaut la peine
    d'être conservé. Les pièces d'une consultation à laquelle on ne répondra
    pas n'ont rien à faire dans la base de connaissance."""
    r = admin.post("/api/datacenter/marche/analyser",
                   json={"documents": [_fichier("RC_consultation.txt", RC)]},
                   headers=ORIGINE)
    assert r.status_code == 200, r.get_json()
    j = r.get_json()
    assert j["ok"]
    assert j["analyse"]["pieces"][0]["code"] == "rc"
    releve = [x for x in j["analyse"]["pieces"][0]["releves"]
              if x["cle"] == "date_limite"][0]
    assert releve["trouve"]


def test_un_contenu_indecodable_est_ecarte_avec_son_motif(admin):
    """Écarté en silence, un fichier se lit comme un fichier analysé — et le
    lecteur croirait son dossier complet."""
    r = admin.post("/api/datacenter/marche/analyser", json={"documents": [
        {"nom": "casse.txt", "contenu": "pas du base64 !!", "extension": ".txt"}
    ]}, headers=ORIGINE)
    j = r.get_json()
    assert not j["ok"]
    assert j["ignores"]
    assert "décodable" in j["ignores"][0]["pourquoi"]


def test_un_fichier_refuse_par_l_analyse_ne_va_pas_aux_extracteurs(admin):
    """LE FICHIER N'EST PAS CONSERVÉ, mais il est OUVERT par des extracteurs de
    texte — et un extracteur qui ouvre un fichier hostile est exactement ce
    contre quoi cette porte existe. Une extension refusée d'office suffit à le
    montrer."""
    r = admin.post("/api/datacenter/marche/analyser", json={"documents": [
        {"nom": "piege.exe",
         "contenu": base64.b64encode(b"MZ\x90\x00").decode("ascii"),
         "extension": ".exe"}
    ]}, headers=ORIGINE)
    j = r.get_json()
    assert not j["ok"]
    assert j["ignores"], j


def test_une_demande_sans_document_est_refusee_proprement(admin):
    r = admin.post("/api/datacenter/marche/analyser", json={"documents": []},
                   headers=ORIGINE)
    assert r.status_code == 400
    assert r.get_json()["error"] == "aucun_document"


def test_les_documents_sont_analyses_ensemble_pour_dire_ce_qui_manque(admin):
    """L'information la plus utile d'une analyse est CE QUI MANQUE — et cela
    ne se voit qu'en regardant le dossier entier."""
    j = admin.post("/api/datacenter/marche/analyser",
                   json={"documents": [_fichier("RC.txt", RC)]},
                   headers=ORIGINE).get_json()
    absents = {m["code"] for m in j["analyse"]["manquantes"]}
    assert {"ccap", "cctp", "ae"} <= absents, absents


# ── Le plan de candidature ─────────────────────────────────────────────────

def test_le_plan_de_candidature_dit_quelles_notes_se_redigent(connecte):
    """Le lien pièce → livrable se fait au serveur : une page qui devinerait
    quel livrable rédige quelle pièce se tromperait le jour où l'un des deux
    changerait de nom."""
    j = connecte.post("/api/datacenter/marche/candidature", json={},
                      headers=ORIGINE).get_json()
    assert j["plan"]["redaction"]
    for r in j["plan"]["redaction"]:
        assert r["type"] and r["label"], r


def test_toute_piece_annoncee_redigeable_existe_au_catalogue(connecte):
    """Un livrable annoncé et absent du catalogue conduirait le lecteur vers
    une page vide."""
    import livrables
    j = connecte.post("/api/datacenter/marche/candidature", json={},
                      headers=ORIGINE).get_json()
    for r in j["plan"]["redaction"]:
        assert livrables.get_type(r["type"]), r["type"]


def test_toute_piece_redigeable_designe_une_piece_du_dossier(connecte):
    """L'inverse : un pont vers une pièce inexistante afficherait un bouton de
    rédaction sous aucune pièce."""
    import ao_dc
    cles = {p["cle"] for p in ao_dc.DOSSIER_CANDIDATURE}
    j = connecte.post("/api/datacenter/marche/candidature", json={},
                      headers=ORIGINE).get_json()
    for r in j["plan"]["redaction"]:
        assert r["piece"] in cles, r["piece"]


def test_seules_les_notes_sont_annoncees_redigeables(connecte):
    """Un formulaire ne se rédige pas, un justificatif s'obtient. Proposer de
    générer un DC1 produirait un document d'apparence officielle sur des faits
    que personne n'a vérifiés."""
    import ao_dc
    natures = {p["cle"]: p["nature"] for p in ao_dc.DOSSIER_CANDIDATURE}
    j = connecte.post("/api/datacenter/marche/candidature", json={},
                      headers=ORIGINE).get_json()
    for r in j["plan"]["redaction"]:
        assert natures[r["piece"]] == "note", (r["piece"], natures[r["piece"]])


def test_le_plan_sert_le_vocabulaire_des_pieces_de_marche(connecte):
    j = connecte.post("/api/datacenter/marche/candidature", json={},
                      headers=ORIGINE).get_json()
    assert "ccap" in j["pieces_marche"]
    assert j["pieces_marche"]["ccap"]["sigle"] == "CCAP"


# ── Ce que la page reçoit avec le référentiel ──────────────────────────────

def test_le_referentiel_d_ingenierie_porte_les_champs_icpe(connecte):
    """La page dessine son formulaire de criblage sur cette réponse. Servi
    séparément, il s'afficherait vide le temps d'un second appel."""
    j = connecte.get("/api/datacenter/ingenierie").get_json()
    assert j["referentiel"]["icpe_champs"]
    assert j["referentiel"]["natures_travaux"]


def test_le_referentiel_du_moteur_porte_la_technique_des_fluides(connecte):
    """Le formulaire de choix des fluides est construit sur cette réponse :
    servir l'explication séparément l'afficherait APRÈS la liste, c'est-à-dire
    au moment exact où le lecteur choisit."""
    j = connecte.get("/api/datacenter/referentiel").get_json()
    t = j["technique"]
    assert t["modes_refroidissement"]
    assert t["modes_source"]
    familles = {m.get("famille") for m in t["modes_refroidissement"].values()}
    assert set(j["referentiel"]["refroidissement"]) <= familles


def test_le_glossaire_de_la_page_porte_les_familles_des_quatre_modules(connecte):
    """Le navigateur ne connaît qu'UNE table et un seul attribut. Une famille
    absente rend l'infobulle muette — et une infobulle muette ne se voit pas."""
    g = connecte.get("/api/datacenter/ingenierie").get_json()["referentiel"]["glossaire"]
    for famille in ("mode_froid", "archi_elec", "enjeu", "nature_travaux",
                    "rubrique_icpe", "regime_icpe", "intervenant", "operation",
                    "solution", "piece_marche", "piece_candidature"):
        assert famille in g, famille
        assert g[famille], famille
