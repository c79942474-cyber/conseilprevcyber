"""LE PARCOURS DU CHIFFRAGE — l'ordre des gestes, et ce que chacun engage.

CE QUI MANQUAIT À LA SECTION. Elle chiffrait juste, mais ne disait nulle part
DANS QUEL ORDRE s'y prendre. Un lecteur qui arrive voit une liste déroulante,
une dizaine de champs et un bouton ; rien ne lui apprend que le choix de la
nature commande la liste des postes plutôt qu'un coefficient, ni que la part
technique qu'il constitue poste par poste vaut, pour les honoraires qui
suivent, bien plus que n'importe quel taux du barème.

CE QUE CES CONTRÔLES GARDENT, ET LE PREMIER EST LE VRAI SUJET :

  1. AUCUN COMPTE N'EST ÉCRIT À LA MAIN. Combien de postes, combien de
     quantités, combien de provenances : tout se dérive du référentiel. Un
     compte figé dans un texte d'aide se dément au premier poste ajouté — et
     personne ne le voit passer, parce qu'une phrase d'aide garde son air de
     vérité longtemps après avoir cessé d'être vraie. C'est le défaut que ce
     fichier surveille en priorité, en RECOMPTANT depuis les données.
  2. LES COMPTES SUIVENT LA NATURE. Annoncer cinq quantités à qui n'en
     remplira que trois fait chercher deux chiffres qui ne seront jamais
     demandés.
  3. LE PARCOURS VA JUSQU'AUX HONORAIRES. C'est l'étape qui relie les deux
     sections d'argent de la page ; la perdre remettrait la part technique à
     l'hypothèse de 70 % sans que rien ne le signale.
  4. IL N'INVENTE AUCUNE CIBLE. Une étape qui désigne un élément absent de la
     page conduit le lecteur dans le vide.
"""
import os
import re
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import econome_dc as E  # noqa: E402
from conftest import ORIGINE  # noqa: E402


def _page():
    with open(os.path.join(ICI, "ingenierie-datacenter.html"), encoding="utf-8") as f:
        return f.read()


# ── 1. Les comptes sont DÉRIVÉS, jamais écrits ─────────────────────────────

def test_les_comptes_se_recalculent_depuis_le_referentiel():
    """LE CONTRÔLE QUI COMPTE LE PLUS ICI : on recompte à la main depuis les
    données et on exige que le parcours dise la même chose."""
    p = E.parcours()
    assert p["ok"] is True
    c = p["comptes"]
    assert c["postes"] == len(E.POSTES)
    assert c["quantites"] == len(E.QUANTITES)
    assert c["provenances"] == len(E.ORDRE_PROVENANCES)
    assert c["natures"] == len(E.ORDRE_OPERATIONS)
    assert c["seuil_non_chiffre_pct"] == E.SEUIL_NON_CHIFFRE * 100


def test_aucun_compte_n_est_ecrit_en_dur_dans_les_textes():
    """Un nombre écrit dans un texte d'étape se démentirait au premier poste
    ajouté. Les textes disent le geste ; les comptes viennent à côté."""
    for e in E.PARCOURS:
        for champ in ("titre", "geste", "pourquoi", "engage"):
            texte = e[champ]
            # « 70 % » est une hypothèse du barème CITÉE comme telle, pas un
            # compte du référentiel : elle est nommée et n'a pas à bouger.
            reste = texte.replace("70 %", "")
            assert not re.search(r"\b\d+\s*(poste|quantité|provenance|nature)",
                                 reste), (e["id"], champ, texte)


# ── 2. Les comptes suivent la nature choisie ───────────────────────────────

def test_les_comptes_portent_sur_ce_que_la_nature_demande():
    neuf = E.parcours("neuf")
    rehab = E.parcours("rehabilitation_technique")
    assert neuf["comptes"]["postes"] == len(E.OPERATIONS["neuf"]["postes"])
    assert rehab["comptes"]["postes"] == len(
        E.OPERATIONS["rehabilitation_technique"]["postes"])
    # Les deux natures ne demandent pas la même chose : si ces comptes étaient
    # égaux, c'est que le parcours ne suivrait plus la nature du tout.
    assert neuf["comptes"]["postes"] != rehab["comptes"]["postes"]


def test_les_quantites_annoncees_sont_celles_que_les_postes_reclament():
    for cle in E.ORDRE_OPERATIONS:
        p = E.parcours(cle)
        attendues = {E.POSTES[x]["assiette"] for x in E.OPERATIONS[cle]["postes"]}
        servies = {q["cle"] for q in p["quantites_demandees"]}
        assert servies == attendues, cle
        assert p["comptes"]["quantites"] == len(attendues), cle


def test_chaque_quantite_annoncee_dit_ou_la_prendre():
    """C'est tout l'apport de l'étape 2 : une puissance souscrite prise pour
    une puissance informatique gonfle la colonne technique sans qu'aucun
    contrôle ne bronche."""
    for q in E.parcours("neuf")["quantites_demandees"]:
        assert q["ou"].strip(), q["cle"]
        assert q["unite"].strip(), q["cle"]


def test_une_nature_inconnue_est_refusee_avec_les_natures_attendues():
    r = E.parcours("nexiste_pas")
    assert r["ok"] is False and r["erreur"] == "operation_inconnue"
    for cle in E.ORDRE_OPERATIONS:
        assert cle in r["message"]


# ── 3. Le parcours va jusqu'aux honoraires ─────────────────────────────────

def test_le_parcours_prolonge_jusqu_a_la_maitrise_d_oeuvre():
    ids = [e["id"] for e in E.PARCOURS]
    assert "maitrise_oeuvre" == ids[-1], (
        "l'étape qui relie le chiffrage aux honoraires doit CLORE le "
        "parcours : ailleurs, elle se lirait comme une option")
    etape = E.PARCOURS[-1]
    assert "#ig-moe-pont" == etape["ancre"]
    assert "70 %" in etape["pourquoi"], (
        "l'étape doit dire ce que la part technique CALCULÉE remplace — sans "
        "quoi rien ne distingue ce chiffrage d'un montant tapé à la main")


def test_les_provenances_sont_servies_dans_l_ordre_du_referentiel():
    p = E.parcours()
    servies = [x["cle"] for x in p["provenances_ordonnees"]]
    assert servies == E.ORDRE_PROVENANCES
    rangs = [x["rang"] for x in p["provenances_ordonnees"]]
    assert rangs == sorted(rangs), "l'ordre affiché contredirait les rangs"


# ── 4. Aucune cible inventée ───────────────────────────────────────────────

def test_chaque_etape_designe_un_element_qui_existe_dans_la_page():
    """LE CONTRÔLE QUI EMPÊCHE DE CONDUIRE DANS LE VIDE. Le module ne peut pas
    voir la page ; ce test les confronte."""
    page = _page()
    for e in E.PARCOURS:
        for champ in ("cible", "ancre"):
            ident = e[champ][1:]
            assert ('id="%s"' % ident) in page, (
                "l'étape %s désigne #%s, absent de la page" % (e["id"], ident))


def test_chaque_ancre_reserve_la_hauteur_de_l_entete_collant():
    """MESURÉ, PAS SUPPOSÉ. L'en-tête du site est collant et haut de 65 px ;
    scrollIntoView() dépose la cible à 0. Sans « scroll-margin-top », cinq des
    sept étapes atterrissaient SOUS l'en-tête — sur un guide dont conduire à
    la cible est tout le geste.

    Le CSS ne peut pas lire le référentiel : ce test les confronte, et tombe
    le jour où une étape désigne une ancre que la règle ne couvre pas."""
    page = _page()
    i = page.index("scroll-margin-top:84px")
    # Le sélecteur qui porte la règle, remonté jusqu'au début de sa ligne.
    debut = page.rindex("\n", 0, i) + 1
    regle = page[debut:i]
    for ancre in E.sante()["parcours_ancres"]:
        assert ancre in regle, (
            "l'ancre %s n'a pas de scroll-margin-top : l'étape qui y conduit "
            "déposera sa cible sous l'en-tête collant" % ancre)


def test_le_parcours_est_servi_avec_le_referentiel():
    """La page doit pouvoir le rendre sans un second aller-retour : sinon elle
    affiche « Chargement du parcours… » alors que la réponse est déjà là."""
    r = E.referentiel()
    assert r["parcours"]["ok"] is True
    assert len(r["parcours"]["etapes"]) == len(E.PARCOURS)


def test_la_page_ne_recopie_pas_les_textes_du_parcours():
    """Recopiés dans le HTML, ils dériveraient du module en silence."""
    page = _page()
    for e in E.PARCOURS:
        assert e["geste"] not in page, e["id"]
        assert e["pourquoi"] not in page, e["id"]


# ── 5. La route ────────────────────────────────────────────────────────────

def test_la_route_est_fermee_au_visiteur_sans_compte(anonyme):
    r = anonyme.get("/api/datacenter/economiste/parcours")
    assert r.status_code in (401, 403), r.status_code


def test_la_route_sert_le_parcours_au_client(connecte):
    r = connecte.get("/api/datacenter/economiste/parcours")
    assert r.status_code == 200, r.status_code
    d = r.get_json()
    assert d["ok"] is True and len(d["etapes"]) == len(E.PARCOURS)


def test_la_route_suit_la_nature_demandee(connecte):
    r = connecte.get("/api/datacenter/economiste/parcours?operation=neuf")
    assert r.status_code == 200
    d = r.get_json()
    assert d["operation"] == "neuf"
    assert d["comptes"]["postes"] == len(E.OPERATIONS["neuf"]["postes"])


def test_la_route_refuse_une_nature_inconnue(connecte):
    r = connecte.get("/api/datacenter/economiste/parcours?operation=zzz")
    assert r.status_code == 400
    assert r.get_json()["erreur"] == "operation_inconnue"


# ── 6. Le contrôle au chargement ───────────────────────────────────────────

def test_une_etape_muette_empeche_le_module_de_demarrer(monkeypatch):
    """Le module refuse de démarrer plutôt que de servir une étape sans
    consigne — elle ferait cliquer sans rien apprendre."""
    casse = [dict(E.PARCOURS[0], geste="")]
    monkeypatch.setattr(E, "PARCOURS", casse)
    try:
        E._verifier()
    except RuntimeError as e:
        assert "geste" in str(e)
    else:
        raise AssertionError("une étape sans consigne a été acceptée")


def test_une_ancre_qui_ne_designe_rien_empeche_le_demarrage(monkeypatch):
    casse = [dict(E.PARCOURS[0], ancre="ig-eco")]   # sans le « # »
    monkeypatch.setattr(E, "PARCOURS", casse)
    try:
        E._verifier()
    except RuntimeError as e:
        assert "ancre" in str(e)
    else:
        raise AssertionError("une ancre sans « # » a été acceptée")


def test_perdre_l_etape_des_honoraires_empeche_le_demarrage(monkeypatch):
    """La garde qui compte : c'est cette étape qui relie les deux sections
    d'argent de la page."""
    monkeypatch.setattr(E, "PARCOURS",
                        [e for e in E.PARCOURS if e["id"] != "maitrise_oeuvre"])
    try:
        E._verifier()
    except RuntimeError as e:
        assert "maîtrise" in str(e)
    else:
        raise AssertionError("le parcours a été accepté sans les honoraires")
