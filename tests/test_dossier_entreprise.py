# -*- coding: utf-8 -*-
"""Le dossier d'entreprise de CONSEILPREV — à qui il appartient, et ce qui lui
manque.

DEUX CHOSES SONT EN JEU, ET LA PREMIÈRE EST LA PLUS GRAVE.

  1. CE DOSSIER N'EST PAS CELUI DES CLIENTS DU MODULE. `ao_dc.remplir()` sert
     des clients qui préparent LEUR candidature. Y faire entrer les
     qualifications et les références de CONSEILPREV donnerait à un client les
     références d'un autre — et lui permettrait de les déposer comme siennes.
     Ce n'est pas une question de discrétion : une candidature appuyée sur les
     références d'un tiers est un faux.

  2. LES TROUS SONT DES DONNÉES, PAS DE LA PROSE. Les documents d'origine
     portent « [à compléter] », « référence à préciser », « attestation à
     joindre ». Recopiés dans un texte, ces trous deviennent invisibles au
     décompte, et le dossier se lit comme complet. Comptés, ils disent la
     vérité : à la transcription du 13 août 2026, AUCUNE des neuf
     qualifications n'est justifiée de bout en bout, et quatre références sur
     huit seulement sont utilisables — pour un minimum de six.

CES CHIFFRES SONT UNE MESURE DATÉE, pas une propriété du module. Ils bougeront
dès qu'une correction sera enregistrée, et c'est le but. Ce que les règles
tiennent, c'est la MÉTHODE de comptage — et le fait qu'un trou comblé fasse
bouger le compte.
"""
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc                                                     # noqa: E402
import dossier_entreprise as D                                   # noqa: E402

ORIGINE = {"Origin": "http://localhost"}


def _etat(corrections=None):
    return D.etat(ao_dc.DOSSIER_CANDIDATURE, corrections=corrections)


# ══════════════════════════════════════════════════════════════════════════
# 1. IL NE SORT PAS DE L'ADMINISTRATION
# ══════════════════════════════════════════════════════════════════════════

def test_aucune_reference_de_CONSEILPREV_n_entre_dans_le_report_client():
    """LA RÈGLE LA PLUS IMPORTANTE DE CE FICHIER. Un client qui déposerait les
    références de CONSEILPREV comme siennes ne commettrait pas une maladresse :
    il déposerait un faux. On mesure donc que RIEN de ce dossier n'apparaît
    dans ce que `remplir()` rend — ni un nom de client, ni un montant, ni une
    dénomination."""
    r = ao_dc.remplir(fiche={"raison_sociale": "Un client quelconque"})
    texte = repr(r)
    temoins = [D.IDENTITE["raison_sociale"], D.IDENTITE["siren"],
               D.IDENTITE["courriel"]]
    temoins += [x["client"] for x in D.REFERENCES if x["client"]]
    temoins += [x["intitule"] for x in D.QUALIFICATIONS]
    assert len(temoins) >= 12, "trop peu de témoins pour que la règle morde"
    for t in temoins:
        assert t not in texte, (
            "« %s » sort du dossier de CONSEILPREV dans le report servi aux "
            "clients" % t)


def test_le_dossier_n_est_servi_que_sous_api_admin(anonyme, connecte):
    """La politique d'accès du site ferme la famille /api/admin/ à
    l'administrateur, et refuse de démarrer si une de ses routes ne l'est pas.
    Cette règle mesure la RÉPONSE : un compte client connecté n'entre pas
    davantage qu'un visiteur."""
    for client in (anonyme, connecte):
        r = client.get("/api/admin/dossier-entreprise", headers=ORIGINE)
        assert r.status_code in (401, 403), r.status_code
        r = client.post("/api/admin/dossier-entreprise",
                        json={"corrections": {}}, headers=ORIGINE)
        assert r.status_code in (401, 403), r.status_code


# ══════════════════════════════════════════════════════════════════════════
# 2. LES TROUS SONT COMPTÉS, ET LES COMBLER FAIT BOUGER LE COMPTE
# ══════════════════════════════════════════════════════════════════════════

def test_une_reference_sans_client_sans_periode_ou_sans_montant_n_est_pas_utilisable():
    """« UTILISABLE » N'EST PAS « PRÉSENTE ». Annoncer huit références là où
    l'acheteur en trouvera quatre documentées fait perdre plus qu'un dossier :
    cela fait douter du reste."""
    r = _etat()["references"]
    assert r["total"] == len(D.REFERENCES) == 8
    assert r["utilisables"] + r["a_completer"] == r["total"]
    assert 0 < r["utilisables"] < r["total"], (
        "toutes utilisables ou aucune : la distinction ne sépare rien")
    for ligne in r["lignes"]:
        attendu = not (ligne["client"] and ligne["periode"]
                       and ligne["montant"] and ligne["manques"] == [])
        assert (not ligne["complete"]) == bool(attendu or ligne["manques"]), (
            ligne["annexe"], ligne["complete"], ligne["manques"])
        if not ligne["client"]:
            assert any("Client non nommé" in m for m in ligne["manques"])
        if not ligne["periode"]:
            assert any("Période non renseignée" in m for m in ligne["manques"])


def test_combler_un_trou_fait_monter_le_compte_des_utilisables():
    """LE TÉMOIN QUI PROUVE QUE LE COMPTE EST CALCULÉ ET NON ÉCRIT. Une règle
    qui se contenterait de lire « 4 » resterait verte devant un chiffre en
    dur."""
    avant = _etat()["references"]
    creuse = [x for x in avant["lignes"] if not x["complete"]][0]
    corr = {"references.%s.client" % creuse["annexe"]: "Un maître d'ouvrage",
            "references.%s.periode" % creuse["annexe"]: "2024–2025",
            "references.%s.montant" % creuse["annexe"]: "80 k€ HT",
            "references.%s.manques" % creuse["annexe"]: []}
    apres = _etat(corr)["references"]
    assert apres["utilisables"] == avant["utilisables"] + 1, (
        avant["utilisables"], apres["utilisables"])
    assert apres["manque_au_minimum"] == max(0, avant["manque_au_minimum"] - 1)


def test_le_minimum_est_LU_sur_la_piece_du_dossier_de_candidature():
    """« Références — six au minimum » : le chiffre est écrit là-bas. Le
    recopier ici en ferait une seconde vérité, qui divergerait le jour où
    l'une des deux serait corrigée."""
    piece = [p for p in ao_dc.DOSSIER_CANDIDATURE
             if p["cle"] == "references"][0]
    assert D.minimum_references(piece["nom"]) == 6, piece["nom"]
    assert _etat()["references"]["minimum"] == 6
    # ET IL SUIT LE NOM DE LA PIÈCE, il n'est pas gravé ici.
    assert D.minimum_references("Références — huit au minimum") == 8
    assert D.minimum_references("Références — 4 au moins") == 4
    # UN NOM QUI NE PORTE PLUS DE BARRE N'EN INVENTE PAS UNE.
    assert D.minimum_references("Références") is None
    assert "minimum" not in D.etat_references(None)


def test_chaque_qualification_dit_par_quelle_voie_elle_se_justifie():
    """Un certificat d'organisme et une affirmation du candidat ne se valent
    pas devant un acheteur. Les confondre reviendrait à présenter une
    affirmation là où il attend un document opposable."""
    q = _etat()["qualifications"]
    assert q["total"] == len(D.QUALIFICATIONS) == 9
    assert q["completes"] + q["a_completer"] == q["total"]
    for ligne in q["lignes"]:
        assert ligne["voie"] in D.VOIES_JUSTIFICATION, ligne["annexe"]
        assert ligne["voie_nom"], ligne["annexe"]
        assert ligne["intitule"].strip() and ligne["appui"].strip()
    # LA MESURE DATÉE : à la transcription, aucune n'est justifiée de bout en
    # bout. Si cela change, cette règle doit être revue DÉLIBÉRÉMENT — c'est
    # une bonne nouvelle, pas une régression.
    assert q["completes"] == 0, (
        "des qualifications sont devenues complètes : mettre à jour cette "
        "mesure datée plutôt que la contourner — %s"
        % [x["annexe"] for x in q["lignes"] if x["complete"]])
    assert q["manques"] >= q["total"], q["manques"]


# ══════════════════════════════════════════════════════════════════════════
# 3. LES CORRECTIONS — CE QUI EST REFUSÉ EST NOMMÉ
# ══════════════════════════════════════════════════════════════════════════

def test_une_correction_qui_ne_designe_rien_est_refusee_et_nommee():
    """Une correction avalée en silence fait croire à une modification qui n'a
    pas eu lieu — et c'est au moment de déposer qu'on s'en aperçoit."""
    cas = {"references.RXX.client": "x",       # repère inconnu
           "references.R1.inconnu": "x",       # champ non corrigible
           "qualifications.A1.voie": "magie",  # voie inconnue
           "qualifications.A1.manques": "pas une liste",
           "identite.pas_un_champ": "x",
           "n_importe_quoi": "x"}
    _q, _r, _i, _t, refuses = D.appliquer(cas)
    assert {x["cible"] for x in refuses} == set(cas), refuses
    motifs = {x["cible"]: x["motif"] for x in refuses}
    assert motifs["references.RXX.client"] == "repere_inconnu"
    assert motifs["references.R1.inconnu"] == "champ_non_corrigible"
    assert motifs["qualifications.A1.voie"] == "voie_inconnue"
    assert motifs["qualifications.A1.manques"] == "manques_mal_formes"
    assert motifs["identite.pas_un_champ"] == "champ_inconnu"
    assert motifs["n_importe_quoi"] == "cible_illisible"
    # ET AUCUNE N'A ÉTÉ APPLIQUÉE : le témoin, sans lequel la règle serait
    # verte devant une fonction qui refuse ET applique.
    assert _etat(cas)["references"]["utilisables"] == _etat()["references"]["utilisables"]


def test_une_correction_valide_ne_touche_QUE_sa_cible():
    """Corriger le client de R8 ne doit rien changer à R1."""
    avant = {x["annexe"]: dict(x) for x in _etat()["references"]["lignes"]}
    apres = {x["annexe"]: dict(x)
             for x in _etat({"references.R8.client": "Ørsted France"})
             ["references"]["lignes"]}
    assert apres["R8"]["client"] == "Ørsted France"
    for annexe in avant:
        if annexe == "R8":
            continue
        assert apres[annexe] == avant[annexe], annexe


def test_la_table_declaree_n_est_jamais_modifiee_par_une_correction():
    """`appliquer()` rend une COPIE. Muter la table en place ferait durer la
    correction au-delà de la requête — et la ferait s'appliquer à l'appel
    suivant, sans que rien ne l'ait demandé."""
    avant = [dict(x, manques=list(x["manques"])) for x in D.REFERENCES]
    D.appliquer({"references.R1.client": "Écrasé", "references.R1.manques": ["x"]})
    assert [dict(x, manques=list(x["manques"])) for x in D.REFERENCES] == avant


# ══════════════════════════════════════════════════════════════════════════
# 4. CE QUE CHAQUE DOCUMENT COUVRE DU DOSSIER DE CANDIDATURE
# ══════════════════════════════════════════════════════════════════════════

def test_chaque_document_couvre_des_pieces_QUI_EXISTENT():
    """Une correspondance déclarée vers une pièce inexistante ferait annoncer
    une couverture que le dossier de candidature ne connaît pas."""
    cles = {p["cle"] for p in ao_dc.DOSSIER_CANDIDATURE}
    e = _etat()
    assert len(e["documents"]) == len(D.DOCUMENTS) == 4
    couvertes = set()
    for d in e["documents"]:
        assert d["couvre_inconnues"] == [], d
        assert d["present"] is True, (
            "le document d'origine « %s » n'est pas déposé" % d["fichier"])
        for c in d["couvre"]:
            assert c["cle"] in cles, c
            assert c["nom"] != c["cle"], (
                "la pièce est nommée par sa clé : le nom n'a pas été repris "
                "du dossier de candidature")
            couvertes.add(c["cle"])
    assert couvertes == {"atd_atp", "references", "qse", "moyens"}, couvertes


def test_le_papier_en_tete_ne_pretend_couvrir_aucune_piece():
    """Il porte les courriers, il n'en est pas un. Lui attribuer une pièce
    ferait compter comme fournie une note que personne n'a écrite."""
    entete = [d for d in _etat()["documents"]
              if d["cle"] == "papier_entete"][0]
    assert entete["couvre"] == []
    assert D.PAPIER_ENTETE["champs"] == ["date", "destinataire",
                                         "adresse_destinataire", "objet",
                                         "corps"]
    for champ in ("siren", "tva", "adresse"):
        assert D.IDENTITE[champ] in D.PAPIER_ENTETE["pied"], champ


def test_le_dossier_dit_qu_il_ne_produit_aucun_justificatif():
    """Une attestation se demande à l'organisme qui la délivre. Un module qui
    laisserait croire qu'il la produit ferait attendre un document qui ne
    viendra pas."""
    note = _etat()["note"]
    assert "ne le produit pas" in note or "il ne le produit pas" in note, note
    assert "aucun client" in note, note


# ══════════════════════════════════════════════════════════════════════════
# 5. UN DÉFAUT DE LA GARDE D'ACCÈS, TROUVÉ PAR UNE MUTATION
# ══════════════════════════════════════════════════════════════════════════

def test_deux_routes_sur_un_meme_chemin_ne_se_cachent_pas_l_une_l_autre():
    """DÉFAUT RÉEL DANS LA POLITIQUE D'ACCÈS, ET IL A ÉTÉ TROUVÉ ICI.

    `/api/admin/dossier-entreprise` porte DEUX routes : un GET qui lit et un
    POST qui corrige. `_acces_api_reels()` écrasait son entrée à chaque tour de
    boucle, si bien que la protection retenue était celle de la DERNIÈRE règle
    rendue par Flask. Remplacer `@admin_required` par `@login_required` sur le
    GET ne faisait donc rien lever : le POST portait encore le bon décorateur,
    et la politique déclarait l'ensemble conforme. Une porte sur deux qui ferme
    ne ferme pas.

    ON RETIENT DÉSORMAIS LA PROTECTION LA PLUS FAIBLE — celle qui décrit ce
    qu'un appelant peut réellement atteindre. Et la mutation qui retire
    `@admin_required` fait maintenant ce qu'elle aurait toujours dû faire :
    empêcher le démarrage.

    LA RÈGLE MONTE UNE VRAIE APPLICATION À DEUX ROUTES plutôt que de rapiécer
    celle du site. Une première rédaction remplaçait `app.url_map` et
    `app.view_functions` en place : elle passait ou tombait selon ce qui avait
    tourné avant elle, ce qui est le contraire d'une mesure.
    """
    import flask

    import app as A
    from auth import admin_required, login_required

    essai = flask.Flask("essai_jumelle")

    @essai.route("/api/admin/jumelle")
    @login_required
    def _lit():                                       # pragma: no cover
        return ""

    @essai.route("/api/admin/jumelle", methods=["POST"], endpoint="ecrit")
    @admin_required
    def _ecrit():                                     # pragma: no cover
        return ""

    releve = A._acces_api_reels(essai)
    assert releve == {"/api/admin/jumelle": "client"}, (
        "la vue fermée masque la vue ouverte : %s" % releve)

    # ET LA POLITIQUE LE VOIT : sous /api/admin/, « client » est un écart.
    import acces
    assert acces.verifier_api(releve), (
        "la politique accepte une route /api/admin/ ouverte à tout compte")
    # LE TÉMOIN : la même application, les deux routes fermées, ne fait aucun
    # écart — sans lui, la règle serait verte devant une politique qui refuse
    # tout.
    assert acces.verifier_api({"/api/admin/jumelle": "admin"}) == []


# ── L'ÉCRAN DU DOSSIER ────────────────────────────────────────────────────
# POURQUOI CETTE PAGE EXISTE, ET CE QUE SON ABSENCE COÛTAIT. Les cinq
# attestations partent SANS DATE — le module ne sait pas ce que l'entreprise
# détient et ne l'invente pas. Tant qu'aucun écran ne permettait de les
# porter, quatre des six déclarations des formulaires ne pouvaient JAMAIS être
# assumées : la preuve manquait, et rien ne permettait de la déclarer. Le
# module était complet et la fonction inatteignable.

def _page_dossier():
    with open(os.path.join(ICI, "admin-dossier-entreprise.html"),
              encoding="utf-8") as f:
        return f.read()


def test_la_page_offre_UN_CHAMP_PAR_DATE_de_chaque_attestation():
    """Sans eux, la chaîne entière est morte : rien ne peut être prouvé."""
    page = _page_dossier()
    # ON MESURE LA CIBLE PRODUITE, pas la façon de l'écrire. La première
    # version de cette règle attendait un littéral exact ; le script bâtit la
    # cible par concaténation, sur deux lignes — la règle échouait sur sa
    # propre attente, pas sur un défaut de la page.
    assert "attestations.'" in page, (
        "aucun champ ne vise la table des attestations")
    for champ in ("delivree_le", "valable_jusqu_au"):
        assert "'." + champ + '"' in page, "aucun champ ne porte %s" % champ
    assert page.count("data-de-champ") >= 2, "les champs ne sont pas relevés"
    # Et les deux champs sont bien ceux que `appliquer()` sait corriger.
    for champ in ("delivree_le", "valable_jusqu_au"):
        assert champ in D.CHAMPS_CORRIGIBLES["attestations"], champ


def test_la_page_montre_l_etat_des_SIX_declarations():
    page = _page_dossier()
    assert "couvertures" in page, "la page n'affiche pas la couverture"
    for etat in ("prouvee", "incomplete", "sans_preuve_interne"):
        assert etat in page, "l'état %s n'est jamais rendu" % etat


def test_la_page_ne_dit_JAMAIS_qu_une_declaration_sera_pre_remplie():
    """Le dossier prouve ; il ne remplit pas. L'écran doit le dire, et ne
    jamais laisser croire l'inverse."""
    page = _page_dossier()
    assert "pré-remplie" in page, "la page ne dit pas ce qu'elle ne fera pas"
    bas = page.lower()
    for promesse in ("remplira les déclarations", "coche pour vous",
                     "signe à votre place"):
        assert promesse not in bas, promesse


def test_un_refus_de_correction_est_DIT_et_non_avale_en_enregistre(admin):
    """CETTE RÈGLE A ÉTÉ REPRISE : sa première version mesurait l'ORDRE DU CODE.

    Elle vérifiait que l'examen des refus précédait le message de succès dans
    la page. C'était vrai — et la page lisait pourtant le mauvais champ :
    `dossier.corrections_refusees`, que la route laisse TOUJOURS vide puisque
    l'état est recalculé à partir des seules corrections retenues. Une date
    illisible répondait « Enregistré ». La règle passait, le défaut vivait.

    Elle mesure donc deux choses : ce que la route RÉPOND, et le champ que la
    page LIT — les deux doivent être le même.
    """
    r = admin.post("/api/admin/dossier-entreprise",
                   json={"corrections": {
                       "attestations.T3.valable_jusqu_au": "31/12/2027"}},
                   headers=ORIGINE)
    assert r.status_code == 200, r.status_code
    j = r.get_json()
    assert j["ok"] is True
    assert [x["motif"] for x in j["refusees"]] == ["date_illisible"], j["refusees"]
    # ET LE CHAMP QUE LA PAGE LIT EST CELUI-LÀ — LU DANS LE CODE, PAS DANS UN
    # COMMENTAIRE. Une mutation qui remettait l'ancien champ n'a rien fait
    # tomber : `j.refusees` figurait encore dans le commentaire qui explique
    # pourquoi c'est ce champ-là. La règle cherchait donc sa propre prose.
    page = _page_dossier()
    assert "var ref = j.refusees" in page, (
        "la page ne LIT pas le champ où la route met les refus")
    i, k = page.index("var ref = j.refusees"), page.index("'Enregistré.'")
    assert i < k and "de-msg ko" in page[i:k], (
        "le succès est annoncé sans examiner les refus")
    # On efface la correction d'essai pour ne rien laisser derrière.
    admin.post("/api/admin/dossier-entreprise",
               json={"corrections": {"attestations.T3.valable_jusqu_au": ""}},
               headers=ORIGINE)


def test_les_comptes_ne_servent_JAMAIS_un_nombre_seul():
    """« 2 valides » ne dit rien sans « sur 5 ». Et un ABSENT n'est pas un
    PÉRIMÉ : les deux se relancent auprès d'organismes différents."""
    page = _page_dossier()
    assert "a.valides.length + ' / ' + a.total" in page, (
        "le compte des attestations valides est servi sans son dénominateur")
    for mot in ("Périmées", "Absentes"):
        assert mot in page, "%s n'est pas compté à part" % mot


def test_la_page_du_dossier_est_fermee_a_l_administration(connecte, anonyme):
    for c in (anonyme, connecte):
        r = c.get("/admin/dossier-entreprise", headers=ORIGINE)
        assert r.status_code in (302, 401, 403), r.status_code


def test_l_administrateur_atteint_la_page_et_elle_porte_son_guide(admin):
    r = admin.get("/admin/dossier-entreprise", headers=ORIGINE)
    assert r.status_code == 200, r.status_code
    corps = r.get_data(as_text=True)
    assert "Dossier d'entreprise" in corps
    with open(os.path.join(ICI, "nav.js"), encoding="utf-8") as f:
        nav = f.read()
    assert 'GUIDES["/admin/dossier-entreprise"]' in nav, (
        "la page tombe sur le guide générique")
