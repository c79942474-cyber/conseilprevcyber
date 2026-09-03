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
                    "solution", "piece_marche", "piece_candidature",
                    "piece_offre"):
        assert famille in g, famille
        assert g[famille], famille


def test_le_plan_de_candidature_sert_aussi_le_dossier_d_offre(connecte):
    """DEUX DOSSIERS, UN SEUL APPEL : la page ouvre les deux blocs depuis la
    même réponse, au moment où elle affiche « Voir le dossier de
    candidature ». `offre()` ne dépend ni de la fiche ni de l'analyse — un
    second appel pour trois pièces statiques doublerait la requête pour
    rien."""
    import ao_dc
    j = connecte.post("/api/datacenter/marche/candidature", json={},
                      headers=ORIGINE).get_json()
    assert j["dossier_offre"]["pieces"]
    cles = {p["cle"] for p in j["dossier_offre"]["pieces"]}
    assert cles == {p["cle"] for p in ao_dc.DOSSIER_OFFRE}
    for p in j["dossier_offre"]["pieces"]:
        assert p["famille_nom"] and p["voie_nom"] and p["nature_nom"]
    # Et les deux dossiers restent bien SÉPARÉS dans la réponse.
    assert not (cles & {p["cle"] for p in j["plan"]["pieces"]})


def test_le_reglage_de_groupement_ATTEINT_LES_DEUX_DOSSIERS(connecte):
    """DÉFAUT RÉEL, TROUVÉ EN RELECTURE : la page envoie UN SEUL réglage de
    groupement pour tout l'écran. S'il n'atteignait que le plan de
    candidature, les dix-neuf cartes diraient « En groupement » et les
    trois de l'offre juste en dessous — dont le prix se répartit et l'acte
    d'engagement se signe différemment selon l'habilitation du mandataire —
    n'en diraient rien, sur le même écran."""
    j = connecte.post("/api/datacenter/marche/candidature",
                      json={"groupement": True}, headers=ORIGINE).get_json()
    for p in j["plan"]["pieces"]:
        assert p.get("en_groupement"), p["cle"]
    for p in j["dossier_offre"]["pieces"]:
        assert p.get("en_groupement"), p["cle"]


# ── Le pilotage de programme ───────────────────────────────────────────────

def test_la_vue_de_programme_est_ouverte_a_un_compte_client(connecte):
    r = connecte.post("/api/datacenter/programme",
                      json={"sites": [{"nom": "A", "puissance_it_kw": 100}]},
                      headers=ORIGINE)
    assert r.status_code == 200, r.get_json()


def test_un_visiteur_anonyme_n_atteint_pas_la_vue_de_programme(anonyme):
    r = anonyme.post("/api/datacenter/programme", json={"sites": []},
                     headers=ORIGINE)
    assert r.status_code in (401, 403)


def test_une_demande_sans_liste_de_sites_est_refusee_avec_ses_champs(connecte):
    """Refuser sans dire ce qu'on attend fait recommencer à l'identique. La
    liste des champs part avec le refus."""
    r = connecte.post("/api/datacenter/programme", json={}, headers=ORIGINE)
    assert r.status_code == 400
    j = r.get_json()
    assert j["error"] == "sites_manquants"
    assert j["champs"], "le refus n'indique pas ce qu'on attend"


def test_un_portefeuille_demesure_est_refuse_avec_une_consigne(connecte):
    """Un programme de plus de deux cents sites existe ; il ne se pilote pas
    depuis un formulaire. Le dire vaut mieux que de servir une page qui met
    trente secondes à s'afficher."""
    r = connecte.post("/api/datacenter/programme",
                      json={"sites": [{"nom": str(i)} for i in range(201)]},
                      headers=ORIGINE)
    assert r.status_code == 400
    assert r.get_json()["error"] == "trop_de_sites"
    assert "sous-portefeuilles" in r.get_json()["message"]


def test_la_vue_rend_le_perimetre_de_chaque_total(connecte):
    """C'est lui qui décide de ce que le total vaut, et la page l'affiche
    contre le chiffre — pas en note de bas de page."""
    j = connecte.post("/api/datacenter/programme", json={"sites": [
        {"nom": "A", "puissance_it_kw": 1000, "pue": 1.2},
        {"nom": "B"},
    ]}, headers=ORIGINE).get_json()
    cap = j["programme"]["capacite_engagee_kw"]
    assert cap["sites_comptes"] == 1
    assert cap["complet"] is False
    assert "B" in cap["sites_absents"]


def test_la_vue_sert_les_indicateurs_et_les_parties_prenantes(connecte):
    """La page construit son tableau de bord sur cette réponse : une clé
    absente le laisserait vide sans rien signaler."""
    j = connecte.post("/api/datacenter/programme",
                      json={"sites": [{"nom": "A", "puissance_it_kw": 100}]},
                      headers=ORIGINE).get_json()
    assert j["kpi"] and j["champs"] and j["natures"]
    assert j["parties_prenantes"] and j["international"] and j["zero_defaut"]


def test_le_referentiel_d_ingenierie_porte_les_champs_de_site(connecte):
    j = connecte.get("/api/datacenter/ingenierie").get_json()
    champs = j["referentiel"]["programme_champs"]
    assert isinstance(champs, list) and champs
    assert {c["id"] for c in champs} >= {"nom", "puissance_it_kw", "pue"}


def test_le_glossaire_porte_les_familles_du_programme(connecte):
    g = connecte.get("/api/datacenter/ingenierie").get_json()["referentiel"]["glossaire"]
    for famille in ("nature_site", "kpi", "partie_prenante"):
        assert famille in g and g[famille], famille


# ── Le barème des seuils ICPE, servi à la page ────────────────────────────

def test_le_bareme_des_seuils_atteint_la_page(connecte):
    """LE BARÈME NE SERT À RIEN S'IL N'ARRIVE PAS. Il est calculé par le
    module qui connaît la nomenclature ET les unités de saisie ; s'il n'entre
    pas dans le référentiel du cadre, la page dessine des champs sans échelle
    et personne ne voit qu'il en manquait une."""
    j = connecte.get("/api/datacenter/ingenierie").get_json()
    b = j["referentiel"]["icpe_bareme"]
    import icpe_dc
    assert set(b["rubriques"]) == set(icpe_dc.RUBRIQUES)
    # Chaque champ numérique du formulaire porte son échelle, dans SON unité.
    for c in icpe_dc.CHAMPS:
        if c["type"] != "nombre":
            continue
        e = b["champs"][c["id"]]
        assert e["unite"] == c.get("unite"), c["id"]
        assert e["variantes"], c["id"]
    # Et les seuils convertis sont bien ceux, convertis, de la rubrique — pas
    # ceux de la nomenclature affichés tels quels sous une autre unité.
    m3 = b["champs"]["fioul_stocke_m3"]["variantes"][0]["paliers"]
    t = b["champs"]["fioul_stocke_t"]["variantes"][0]["paliers"]
    assert [p["a_partir_de_champ"] for p in m3] != [
        p["a_partir_de_champ"] for p in t]


# ── Le raccordement et la production sur site ─────────────────────────────

def test_un_visiteur_anonyme_n_atteint_pas_l_etude_de_raccordement(anonyme):
    r = anonyme.post("/api/datacenter/reseau", json={}, headers=ORIGINE)
    assert r.status_code in (401, 403)


def test_la_route_nomme_ce_qui_manque_au_lieu_de_supposer(connecte):
    """PAS DE VALEUR PAR DÉFAUT SUR CE SUJET. Une fréquence d'effacement
    supposée déplace le résultat d'un facteur trois, et personne ne conteste
    un formulaire déjà rempli."""
    j = connecte.post("/api/datacenter/reseau", json={"puissance_it_kw": 5000},
                      headers=ORIGINE).get_json()
    assert j["ok"] is True
    ns = j["etude"]["non_servi"]
    assert ns["nature"] == "incomplet" and ns["manques"]
    assert "part_non_servie" not in ns


def test_la_route_chiffre_et_rend_les_termes(connecte):
    j = connecte.post("/api/datacenter/reseau", json={
        "mode_raccordement": "non_ferme", "puissance_it_kw": 100000,
        "taux_charge": 0.65, "part_non_ferme": 0.5,
        "frequence_effacement": 0.3, "marge_operationnelle": 0.5,
    }, headers=ORIGINE).get_json()
    ns = j["etude"]["non_servi"]
    assert ns["nature"] == "calcule"
    assert ns["termes"]["deficit_horaire_kw"] > 0
    assert j["etude"]["marge"]["elasticite"] == pytest.approx(2.0)
    assert j["etude"]["mode"]["cle"] == "non_ferme"


def test_une_saisie_illisible_ressort_dans_les_rejets(connecte):
    """Une valeur écartée en silence ferait calculer sur un champ absent : le
    résultat serait juste pour une question qui n'a pas été posée."""
    j = connecte.post("/api/datacenter/reseau", json={
        "puissance_it_kw": 100000, "taux_charge": 0.65,
        "part_non_ferme": "beaucoup", "frequence_effacement": 0.3,
    }, headers=ORIGINE).get_json()
    assert any(r["champ"] == "part_non_ferme" for r in j["rejets"])
    assert j["etude"]["non_servi"]["nature"] == "incomplet"


def test_le_criblage_reglementaire_voyage_avec_l_etude(connecte):
    """La production sur site s'ajoute aux groupes de secours déclarés dans le
    MÊME envoi : c'est le cumul qui décide du régime, et le demander à part
    les ferait diverger."""
    j = connecte.post("/api/datacenter/reseau", json={
        "puissance_it_kw": 100000, "taux_charge": 0.65,
        "part_non_ferme": 0.5, "frequence_effacement": 0.3,
        "groupes_puissance_elec_kw": 2000,
        "btm_puissance_elec_kw": 60000, "btm_combustible": "gaz",
        "btm_heures_an": 876, "btm_classe_iso": "prime",
    }, headers=ORIGINE).get_json()
    prod = j["etude"]["production_sur_site"]
    assert prod["icpe"]["regime_sans_production"] == "DC"
    assert prod["icpe"]["regime_avec_production"] == "A"
    assert prod["alertes"]
    assert prod["duty"]["qualifiante"]["qualifiante_kw"] < 60000


def test_un_mode_de_raccordement_inconnu_est_refuse(connecte):
    j = connecte.post("/api/datacenter/reseau",
                      json={"mode_raccordement": "gratuit"},
                      headers=ORIGINE).get_json()
    assert j["etude"]["nature"] == "refus"
    assert j["etude"]["modes"]


def test_le_referentiel_de_raccordement_accompagne_la_reponse(connecte):
    j = connecte.post("/api/datacenter/reseau", json={}, headers=ORIGINE).get_json()
    r = j["referentiel"]
    for table in ("modes", "leviers", "charges", "btm", "facteurs", "champs"):
        assert r[table], table
    # Chaque mode porte son repère de marché, avec son auteur.
    for m in r["modes"]:
        assert m["repere"]["editeur"], m["cle"]


# ── La qualification Tier ──────────────────────────────────────────────────

def test_un_visiteur_anonyme_n_atteint_pas_la_qualification(anonyme):
    r = anonyme.post("/api/datacenter/tier",
                     json={"sous_systemes": {"prod_elec": "IV"}},
                     headers=ORIGINE)
    assert r.status_code in (401, 403)


def test_une_demande_sans_sous_systemes_dit_ce_qu_elle_attend(connecte):
    """Refuser sans dire ce qu'on attend fait recommencer à l'identique."""
    r = connecte.post("/api/datacenter/tier", json={}, headers=ORIGINE)
    assert r.status_code == 400
    j = r.get_json()
    assert j["error"] == "sous_systemes_manquants"
    assert j["sous_systemes"] and j["niveaux"] == ["I", "II", "III", "IV"]


def test_la_route_rend_le_plus_bas_et_nomme_le_limitant(connecte):
    """LA RÈGLE QUI FAIT TOUT LE MODULE, éprouvée de bout en bout."""
    import tier_dc
    ss = {c: "IV" for c in tier_dc.SOUS_SYSTEMES if c != "eau_appoint"}
    ss["distribution_meca"] = "I"
    j = connecte.post("/api/datacenter/tier", json={"sous_systemes": ss},
                      headers=ORIGINE).get_json()
    q = j["qualification"]
    assert q["niveau"] == "I"
    assert [l["cle"] for l in q["limitants"]] == ["distribution_meca"]


def test_le_refroidissement_du_profil_decide_du_perimetre(connecte):
    """L'eau d'appoint n'est un sous-système à noter que sur un site
    évaporatif. Le redemander à part le ferait diverger de la famille
    réellement retenue au moteur."""
    def etat(fam):
        j = connecte.post("/api/datacenter/tier", json={
            "sous_systemes": {"prod_elec": "IV"}, "refroidissement": fam,
        }, headers=ORIGINE).get_json()
        par = {s["cle"]: s for s in j["qualification"]["sous_systemes"]}
        return par["eau_appoint"]["etat"]
    assert etat("air_dx") == "hors_perimetre"
    assert etat("tour_evaporative") == "non_evalue"


def test_l_ecart_n_est_calcule_que_si_un_niveau_est_vise(connecte):
    """Sans intention déclarée, un écart n'a pas de sens."""
    sans = connecte.post("/api/datacenter/tier",
                         json={"sous_systemes": {"prod_elec": "IV"}},
                         headers=ORIGINE).get_json()
    assert sans["ecart"] is None
    avec = connecte.post("/api/datacenter/tier",
                         json={"sous_systemes": {"prod_elec": "IV"},
                               "vise": "III"}, headers=ORIGINE).get_json()
    assert avec["ecart"]["vise"] == "III"


def test_la_classe_du_groupe_decide_de_la_capacite_qualifiante(connecte):
    j = connecte.post("/api/datacenter/tier", json={
        "sous_systemes": {"prod_elec": "IV"},
        "groupe_classe": "secours", "groupes_puissance_elec_kw": "2000",
    }, headers=ORIGINE).get_json()
    assert j["groupes"]["qualifiante_kw"] == 0
    assert j["groupes"]["eligible_iii_iv"] is False


def test_l_autonomie_voyage_avec_la_qualification(connecte):
    """Les douze heures sont une exigence du niveau, pas une option : elles
    n'ont pas à être demandées séparément."""
    j = connecte.post("/api/datacenter/tier", json={
        "sous_systemes": {"prod_elec": "IV"},
        "groupes_puissance_elec_kw": "2000",
    }, headers=ORIGINE).get_json()
    assert j["autonomie"]["heures"] == 12
    assert j["autonomie"]["combustible"]["volume_m3"] > 0


def test_le_referentiel_d_ingenierie_porte_les_sous_systemes(connecte):
    """La page dessine une liste déroulante par sous-système sur cette
    réponse : les demander à part afficherait un bloc vide."""
    j = connecte.get("/api/datacenter/ingenierie").get_json()["referentiel"]
    assert isinstance(j["tier_sous_systemes"], dict) and j["tier_sous_systemes"]
    assert j["tier_ordre"] == ["I", "II", "III", "IV"]


def test_le_glossaire_porte_les_familles_du_tier(connecte):
    g = connecte.get("/api/datacenter/ingenierie").get_json()["referentiel"]["glossaire"]
    for famille in ("tier_exigence", "tier_essai", "tier_regle",
                    "classe_groupe"):
        assert famille in g and g[famille], famille
    # La famille « tier » du cadre reste distincte : elle NOMME les niveaux,
    # les nouvelles portent les exigences. Deux modules ne peuvent pas tenir
    # la même — un contrôle de démarrage le refuse.
    assert "tier" in g


# ═══════════════════════════════════════════════════════════════════════════
#  LE REMPLISSAGE ET L'EXPORT — deux routes, une même exigence
# ═══════════════════════════════════════════════════════════════════════════

FICHE_R = {"raison_sociale": "Bureau d'études Essai", "siret": "80295478500019",
           "representant_nom": "A. Dupont"}


@pytest.mark.parametrize("chemin", ["/api/datacenter/marche/remplir",
                                    "/api/datacenter/marche/export"])
def test_le_remplissage_est_ferme_a_l_anonyme(anonyme, chemin):
    r = anonyme.post(chemin, json={}, headers=ORIGINE)
    assert r.status_code in (401, 403), (chemin, r.status_code)


def test_le_remplissage_rend_les_champs_ET_l_etat_en_un_seul_appel(connecte):
    """LA PAGE NE CONNAÎT PAS LA LISTE DES CHAMPS : elle la reçoit. Une seconde
    route pour la servir se désynchroniserait de celle qui calcule, et le
    formulaire proposerait des cases que le moteur ignore."""
    r = connecte.post("/api/datacenter/marche/remplir", json={}, headers=ORIGINE)
    assert r.status_code == 200
    j = r.get_json()["remplissage"]
    assert j["champs"] and j["groupes"] and j["pieces"]
    assert j["etat"]["rubriques"] == sum(p["total"] for p in j["pieces"])
    assert j["sans_dossier"] is True


def test_la_route_ne_declare_rien_meme_avec_une_fiche_complete(connecte):
    """LE VERROU EST AU SERVEUR, PAS DANS LA PAGE. Une page peut être
    remplacée ; la route, non. Aucune déclaration ne ressort pré-remplie,
    quelle que soit la richesse de ce qu'on lui envoie."""
    pleine = {c: "renseigné" for c in
              ("raison_sociale", "forme_juridique", "adresse", "capital",
               "rcs", "naf", "code_postal", "ville", "telephone", "courriel",
               "representant_nom", "representant_qualite", "effectif",
               "ca_n1", "ca_n2", "ca_n3", "assurance_compagnie",
               "assurance_police", "assurance_echeance")}
    pleine["siret"] = "80295478500019"
    j = connecte.post("/api/datacenter/marche/remplir",
                      json={"fiche": pleine}, headers=ORIGINE).get_json()
    decl = [l for p in j["remplissage"]["pieces"] for l in p["rubriques"]
            if l["source"] == "declaration"]
    assert decl
    assert all(l["valeur"] is None and l["statut"] == "a_declarer"
               for l in decl)
    assert all(not p["pret"] for p in j["remplissage"]["pieces"]
               if p["porte_declaration"])


def test_une_valeur_a_rallonge_est_bornee_a_l_entree(connecte):
    """UNE CASE DE FORMULAIRE QUI RECEVRAIT UN ROMAN NE SE REMPLIT PAS : elle
    sert à faire grossir une réponse. Les entrées sont bornées AVANT le calcul."""
    j = connecte.post("/api/datacenter/marche/remplir",
                      json={"fiche": {"raison_sociale": "X" * 5000}},
                      headers=ORIGINE).get_json()
    v = [l["valeur"] for p in j["remplissage"]["pieces"] for l in p["rubriques"]
         if l["cle"] == "candidat" and l["valeur"]]
    assert v and all(len(x) <= 400 for x in v), [len(x) for x in v]


def test_la_route_ne_conserve_rien_d_un_appel_a_l_autre(connecte):
    """Un état retenu ferait ressortir, sur la consultation suivante, des
    valeurs de la précédente — et personne ne relit une case déjà remplie."""
    connecte.post("/api/datacenter/marche/remplir",
                  json={"fiche": FICHE_R}, headers=ORIGINE)
    j = connecte.post("/api/datacenter/marche/remplir", json={},
                      headers=ORIGINE).get_json()
    v = [l["valeur"] for p in j["remplissage"]["pieces"] for l in p["rubriques"]
         if l["source"] == "fiche"]
    assert not any(v), "une valeur du premier appel survit au second"


def test_le_dossier_s_emporte_en_word_et_en_pdf(connecte):
    """UN DOCUMENT QUI NE SORT PAS DU SITE N'EST PAS UN LIVRABLE : le seul moyen
    de l'emporter serait de sélectionner le texte à l'écran, c'est-à-dire de
    perdre le titrage, les tableaux et les origines."""
    for fmt, debut in (("docx", b"PK"), ("pdf", b"%PDF")):
        r = connecte.post("/api/datacenter/marche/export",
                          json={"fiche": FICHE_R, "format": fmt},
                          headers=ORIGINE)
        assert r.status_code == 200, (fmt, r.status_code)
        assert r.data[:4].startswith(debut), fmt
        assert len(r.data) > 4000, (fmt, len(r.data))
        assert fmt in r.headers.get("Content-Disposition", "")


def test_un_format_inconnu_ne_produit_pas_un_fichier_qui_MENT(connecte):
    """CE QUE CETTE RÈGLE MESURE VRAIMENT, après une mutation qui a survécu à
    sa première version. Le repli sur le Word ne change pas le CONTENU — la
    mise en page retombe déjà sur le docx — mais il change le NOM : sans lui,
    « format: wordperfect » rendait un document Word appelé
    « dossier-candidature.wordperfect », que le poste du client refuse
    d'ouvrir. Un fichier dont l'extension ment sur son contenu est perdu pour
    celui qui le reçoit.

    Ma première version vérifiait le contenu (« ça commence par PK »), qui est
    juste des deux côtés de la mutation : elle était verte pour une raison sans
    rapport avec ce qu'elle prétendait garder."""
    r = connecte.post("/api/datacenter/marche/export",
                      json={"fiche": FICHE_R, "format": "wordperfect"},
                      headers=ORIGINE)
    assert r.status_code == 200 and r.data[:2] == b"PK"
    nom = r.headers.get("Content-Disposition", "")
    assert ".docx" in nom and "wordperfect" not in nom, (
        "le fichier rendu est un Word appelé autrement : %r" % nom)
