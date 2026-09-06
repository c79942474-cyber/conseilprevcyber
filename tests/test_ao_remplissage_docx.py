# -*- coding: utf-8 -*-
"""Le formulaire OFFICIEL est rempli dans son propre fichier — jamais redessiné,
jamais signé.

CE QUI SÉPARE CE MODULE D'UN FAC-SIMILÉ. Un formulaire redessiné par un
programme serait refusé par l'acheteur — ou pire, accepté et faux. Ici, on
ouvre le fichier du ministère, dans sa version, avec sa mise en page et sa date
de mise à jour, et l'on écrit dans les emplacements qu'il laisse vides. Ce qui
sort reste le formulaire officiel.

CES RÈGLES MESURENT LE DOCUMENT PRODUIT, pas le code qui le produit. Elles
l'ouvrent, le comparent au modèle paragraphe par paragraphe, et vérifient que
chaque valeur est sous LE BON intitulé. Vérifier qu'une valeur est « quelque
part dans le document » serait vert pour une valeur déposée dans le mauvais
cadre — c'est-à-dire pour la faute qui compte.

LE PIÈGE PROPRE AU DC4, ET IL EST RÉEL. Les cadres D et E portent les mêmes
intitulés mot pour mot — « Adresse électronique : », « Numéro SIRET… », « Nom
commercial et dénomination sociale… ». L'un identifie le TITULAIRE, l'autre le
SOUS-TRAITANT. Une ancre sans rang déposerait le SIRET du titulaire dans la
case du sous-traitant : une case pleine, plausible, et fausse.
"""
import io
import os
import shutil
import sys
import tempfile

import docx
import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc                                                     # noqa: E402
import ao_formulaires as F                                       # noqa: E402

RC = """RÈGLEMENT DE LA CONSULTATION
Pouvoir adjudicateur : Communauté d'agglomération de l'Essai.
Objet du marché : maîtrise d'œuvre pour un centre de données régional.
Référence de la consultation : 2026-MOE-014.
La consultation est allotie en 3 lots.
"""

FICHE = {"raison_sociale": "Bureau d'études Essai", "forme_juridique": "SAS",
         "siret": "80295478500019", "adresse": "5 rue de l'Essai, 75001 Paris",
         "courriel": "contact@essai.example",
         "representant_nom": "A. Dupont", "representant_qualite": "Président"}

SAISIES = {
    "dc4.sous_traitance": "oui — lot 3",
    "dc4.sous_traitant": "Froid Concept SARL — 59000 Lille — SIRET 51234567800021",
    "dc4.sous_traitant_pouvoir": "M. Martin, gérant",
    "dc4.prestations": "Génie climatique — lot 3",
    "dc4.montant": "TVA 20 % · 84 000 € HT",
    "dc4.compte": "Banque Essai — FR76 1234 5678 9012",
    "dc4.duree_sous_traitance": "8 mois",
}


def _net(s):
    return " ".join((s or "").replace("’", "'").split())


def _paras(source):
    return [_net(p.text) for p in docx.Document(source).paragraphs]


def _produit(saisies=None):
    an = ao_dc.analyser([{"nom": "01_RC.pdf", "texte": RC}])
    r = ao_dc.remplir(fiche=FICHE, analyse=an,
                      saisies=SAISIES if saisies is None else saisies)
    octets, rapport = F.remplir_document("dc4", F.valeurs_pour(r, "dc4"))
    assert octets, rapport
    return octets, rapport


@pytest.fixture(scope="module")
def document():
    octets, rapport = _produit()
    return _paras(io.BytesIO(octets)), _paras(F.chemin_modele("dc4")), rapport


# ══════════════════════════════════════════════════════════════════════════
# 1. CHAQUE VALEUR SOUS LE BON INTITULÉ — LE PIÈGE DES CADRES D ET E
# ══════════════════════════════════════════════════════════════════════════

# L'INTITULÉ ATTENDU DEVANT CHAQUE VALEUR, relevé sur le formulaire. C'est ce
# qui distingue « la valeur est dans le document » de « la valeur est au bon
# endroit » — et seule la seconde question a un intérêt.
DEVANT = {
    "titulaire": "Nom commercial et dénomination sociale",
    "titulaire_adresse": "Adresses postale et du siège social",
    "titulaire_courriel": "Adresse électronique :",
    "titulaire_siret": "Numéro SIRET",
    "titulaire_forme": "Forme juridique du soumissionnaire individuel",
    "sous_traitant": "Nom commercial et dénomination sociale",
    "sous_traitant_pouvoir": "(Indiquer le nom, prénom et la qualité",
    "prestations": "Nature des prestations sous-traitées :",
    "montant": "Montant des prestations sous-traitées :",
    "compte": "Nom de l'établissement bancaire",
    "duree_sous_traitance": "La durée du contrat de sous-traitance en nombre",
}


def test_chaque_valeur_est_ecrite_sous_son_propre_intitule(document):
    """« Présente dans le document » ne veut rien dire : une valeur déposée
    dans le mauvais cadre y serait présente aussi."""
    out, _mod, rapport = document
    par_rubrique = {x["rubrique"]: x for x in rapport["places"]}
    for rubrique, intitule in DEVANT.items():
        assert rubrique in par_rubrique, (
            "%s n'a pas été placée : %s" % (rubrique, rapport["non_places"]))
        i = par_rubrique[rubrique]["paragraphe"] + 1     # le bandeau décale
        avant = [t for t in out[max(0, i - 4):i] if t]
        assert avant, (rubrique, i)
        assert _net(intitule) in avant[-1], (
            "« %s » est écrite sous « %s » au lieu de « %s »"
            % (rubrique, avant[-1][:70], intitule))


def test_le_titulaire_va_au_cadre_D_et_le_sous_traitant_au_cadre_E(document):
    """LE PIÈGE DE CE FORMULAIRE, ET IL EST RÉEL. Les deux cadres portent les
    mêmes intitulés, mot pour mot. Une ancre sans rang mettrait l'identité du
    titulaire dans la case du sous-traitant : pleine, plausible, fausse — et
    un DC4 qui présente le titulaire comme son propre sous-traitant ne
    présente aucun sous-traitant."""
    out, _mod, rapport = document
    d = next(i for i, t in enumerate(out) if t.startswith("D - Identification"))
    e = next(i for i, t in enumerate(out) if t.startswith("E - Identification"))
    f = next(i for i, t in enumerate(out) if t.startswith("F - Nature"))
    assert d < e < f, (d, e, f)
    par_rubrique = {x["rubrique"]: x["paragraphe"] + 1
                    for x in rapport["places"]}
    for rubrique in ("titulaire", "titulaire_adresse", "titulaire_courriel",
                     "titulaire_siret", "titulaire_forme"):
        assert d < par_rubrique[rubrique] < e, (
            "« %s » est sortie du cadre D (¶%d, cadres D=%d E=%d)"
            % (rubrique, par_rubrique[rubrique], d, e))
    for rubrique in ("sous_traitant", "sous_traitant_pouvoir"):
        assert e < par_rubrique[rubrique] < f, (
            "« %s » n'est pas dans le cadre E (¶%d, cadres E=%d F=%d)"
            % (rubrique, par_rubrique[rubrique], e, f))
    # ET LES DEUX IDENTITÉS SONT BIEN DISTINCTES DANS LE DOCUMENT.
    assert out[par_rubrique["titulaire"]] != out[par_rubrique["sous_traitant"]]


# ══════════════════════════════════════════════════════════════════════════
# 2. ON N'ÉCRIT QUE DANS DU VIDE — L'INVARIANT, PAS L'INTENTION
# ══════════════════════════════════════════════════════════════════════════

def test_aucun_paragraphe_porteur_de_texte_n_est_ecrase(document):
    """C'est ce qui rend STRUCTURELLEMENT impossible d'écraser une mention
    légale, un intitulé de cadre ou une déclaration : elles portent du texte.
    Une liste noire de zones à éviter serait une énumération, donc oubliable ;
    ceci est un invariant."""
    out, mod, _r = document
    assert len(out) == len(mod) + 1, "le bandeau doit ajouter UN paragraphe"
    for i in range(1, len(out)):
        if out[i] == mod[i - 1]:
            continue
        assert F._emplacement_libre(mod[i - 1]), (
            "¶%d portait « %s » et a été écrasé par « %s »"
            % (i, mod[i - 1][:60], out[i][:60]))


def test_rien_n_est_ecrit_dans_les_declarations_ni_dans_les_signatures(document):
    """La seconde barrière, et elle protège du BLANC là où la première protège
    du texte : les blocs de signature contiennent des lignes vides, qu'une
    ancre qui glisserait pourrait remplir."""
    out, mod, _r = document
    k = next(i for i, t in enumerate(out)
             if t.startswith("K1 - Le sous-traitant déclare sur l'honneur"))
    m = next(i for i, t in enumerate(out) if t.startswith("M - Acceptation"))
    assert k < m, (k, m)
    modifies = [i for i in range(1, len(out)) if out[i] != mod[i - 1]]
    assert modifies, "rien n'a été écrit : la règle ne mesure rien"
    assert [i for i in modifies if i >= k] == [], (
        "des valeurs ont été écrites dans la zone de déclaration ou de "
        "signature : %s" % [i for i in modifies if i >= k])


def test_une_ancre_qui_viserait_une_declaration_ne_place_RIEN():
    """LA SECONDE BARRIÈRE, ET LA SEULE MESURE QUI PROUVE QU'ELLE SERT.

    Une batterie de mutations a montré que la retirer ne faisait tomber
    AUCUNE règle : sur ce formulaire, l'invariant « on n'écrit que dans du
    vide » suffit à protéger les déclarations, qui portent du texte. Une
    barrière qu'aucune règle ne distingue est une barrière qu'on ne peut pas
    revendiquer — et qu'on supprimerait un jour en croyant nettoyer.

    Ce qu'elle protège, c'est le BLANC : le cadre K1 contient des lignes
    vides, et une ancre qui les viserait y écrirait. On le vérifie avec son
    témoin — sans la barrière, la valeur atterrit bien dans le bloc des
    déclarations.
    """
    paras = [pa.text for pa in docx.Document(F.chemin_modele("dc4")).paragraphs]
    interdits = F._zones_interdites(paras, "dc4")
    ancre = "K1 - Le sous-traitant déclare sur l’honneur"
    assert F._cible(paras, interdits, set(), ancre, 1) is None, (
        "une ancre visant la déclaration sur l'honneur a trouvé un "
        "emplacement : la barrière ne protège rien")
    sans = F._cible(paras, set(), set(), ancre, 1)
    assert sans is not None and sans in interdits, (
        "sans la barrière, cette ancre ne place rien non plus : la règle "
        "serait verte pour une raison sans rapport avec ce qu'elle mesure")


def test_le_remplissage_ne_franchit_jamais_l_intitule_du_cadre_suivant():
    """L'AUTRE ARRÊT, ET IL EST INERTE SUR CE FORMULAIRE-CI — la même batterie
    l'a montré : tous les cadres du DC4 offrent une ligne libre, si bien
    qu'aucune ancre ne cherche au-delà du sien.

    Il n'en est pas moins nécessaire, et il le deviendra visiblement avec les
    trois autres formulaires. On le mesure donc SUR LE MÉCANISME plutôt que
    sur ce document : `_cible()` travaille sur une liste de paragraphes, et
    rien n'oblige à fabriquer un fichier Word pour éprouver une règle de
    parcours.
    """
    ancre = "Nature des prestations sous-traitées :"
    # Le premier emplacement libre est DERRIÈRE l'intitulé du cadre suivant.
    barre = [ancre, "(une note qui occupe la place)",
             "G - Prix des prestations sous-traitées", ""]
    assert F._cible(barre, set(), set(), ancre, 1) is None, (
        "la valeur a franchi l'intitulé du cadre suivant et se serait "
        "déposée dans un cadre qui ne l'attend pas")
    # LE TÉMOIN : le même cas sans cadre interposé place bien la valeur.
    libre = [ancre, "(une note qui occupe la place)", "(une seconde note)", ""]
    assert F._cible(libre, set(), set(), ancre, 1) == 3


def test_une_declaration_ne_peut_pas_etre_ecrite_meme_si_une_ancre_la_designe():
    """LA TROISIÈME BARRIÈRE, POSÉE EN AMONT DES DEUX AUTRES. `valeurs_pour()`
    ne retient que le statut « rempli » ; une déclaration est toujours
    `a_declarer` et sans valeur. Elle ne peut donc pas entrer dans le
    document, même si la table d'ancres la nommait."""
    an = ao_dc.analyser([{"nom": "01_RC.pdf", "texte": RC}])
    r = ao_dc.remplir(fiche=FICHE, analyse=an, saisies=SAISIES)
    vals = F.valeurs_pour(r, "dc4")
    piece = [p for p in r["pieces"] if p["cle"] == "dc4"][0]
    declarations = [l["cle"] for l in piece["rubriques"]
                    if l["source"] == "declaration"]
    assert declarations, "aucune déclaration : le témoin de la règle a disparu"
    for cle in declarations:
        assert cle not in vals, cle
    # ET LE TÉMOIN POSITIF : ce qui est « rempli » passe, sinon la règle
    # serait verte devant une fonction qui ne rend jamais rien.
    assert vals.get("titulaire") == FICHE["raison_sociale"], vals


# ══════════════════════════════════════════════════════════════════════════
# 3. LE MODÈLE EST ÉPINGLÉ — UN FICHIER QUI A BOUGÉ FAIT REFUSER
# ══════════════════════════════════════════════════════════════════════════

def test_le_modele_du_depot_est_bien_celui_qui_a_ete_ancre():
    """Les ancres sont des phrases de CE fichier-ci. Un formulaire mis à jour
    les déplace, les reformule ou les supprime — et le remplissage écrirait à
    côté, sans rien signaler."""
    etat = F.modeles_disponibles()
    assert etat["manquants"] == [] and etat["alteres"] == [], etat
    assert "dc4" in etat["prets"]
    assert F.empreinte(F.chemin_modele("dc4")) == F.MODELES["dc4"]["empreinte"]


def test_un_modele_altere_fait_refuser_le_remplissage(tmp_path, monkeypatch):
    """ON PROVOQUE L'ALTÉRATION plutôt que de constater l'accord. Vérifier que
    l'empreinte concorde aujourd'hui ne dit rien de ce qui arriverait demain :
    seule cette règle prouve que la garde REFUSE."""
    faux = tmp_path / "modeles"
    faux.mkdir()
    shutil.copy(F.chemin_modele("dc4"), str(faux / "DC4.docx"))
    with io.open(str(faux / "DC4.docx"), "ab") as f:
        f.write(b"\n")                       # un octet suffit
    monkeypatch.setattr(F, "DOSSIER_MODELES", str(faux))
    octets, rapport = F.remplir_document("dc4", {"titulaire": "Essai"})
    assert octets is None
    assert rapport["ok"] is False and rapport["motif"] == "modele_altere"
    assert rapport["trouvee"] != rapport["attendue"]
    assert F.modeles_disponibles()["alteres"] == ["dc4"]


def test_un_modele_absent_est_dit_absent_et_non_altere(tmp_path, monkeypatch):
    """Les confondre enverrait chercher une corruption là où il n'y a qu'un
    fichier à déposer — et c'est exactement l'état des trois autres
    formulaires tant qu'ils ne sont pas fournis en .docx."""
    vide = tmp_path / "aucun"
    vide.mkdir()
    monkeypatch.setattr(F, "DOSSIER_MODELES", str(vide))
    octets, rapport = F.remplir_document("dc4", {"titulaire": "Essai"})
    assert octets is None and rapport["motif"] == "modele_absent"
    etat = F.modeles_disponibles()
    assert etat["manquants"] == ["dc4"] and etat["alteres"] == []


# ══════════════════════════════════════════════════════════════════════════
# 4. LE DOCUMENT DIT CE QU'IL EST, ET LE RAPPORT DIT CE QUI MANQUE
# ══════════════════════════════════════════════════════════════════════════

def test_le_document_porte_en_tete_qu_il_n_est_ni_signe_ni_verifie(document):
    """Un document qui circule sans dire cela finirait par être déposé tel
    quel. Le bandeau est POSÉ DEVANT le formulaire, jamais inséré dans un
    cadre : le formulaire officiel n'est pas altéré, il est précédé."""
    out, _mod, _r = document
    assert out[0] == _net(F.BANDEAU), out[0][:80]
    for mot in ("NON SIGNÉ", "NON VÉRIFIÉ", "PROJET"):
        assert mot in F.BANDEAU, mot


def test_le_bandeau_seul_ne_touche_a_RIEN_d_autre_dans_le_formulaire():
    """LA MESURE QUI LE PROUVE, ET C'EST UNE CORRECTION. La règle précédente
    comparait le document REMPLI au modèle et exigeait qu'ils soient
    identiques après le bandeau — elle tombait pour les valeurs écrites,
    c'est-à-dire pour une raison sans rapport avec ce qu'elle prétendait
    mesurer. Ce qu'il fallait comparer, c'est un document SANS VALEUR : là,
    l'écart doit être exactement d'un paragraphe, en tête, et rien d'autre.
    """
    octets, rapport = F.remplir_document("dc4", {})
    assert rapport["ok"] and rapport["places"] == [], rapport
    sans = _paras(io.BytesIO(octets))
    modele = _paras(F.chemin_modele("dc4"))
    assert sans[0] == _net(F.BANDEAU)
    assert sans[1:] == modele, (
        "le bandeau seul a modifié %d autre(s) paragraphe(s)"
        % sum(1 for a, b in zip(sans[1:], modele) if a != b))


def test_sans_bandeau_le_formulaire_ressort_octet_pour_octet_inchange():
    """LE TÉMOIN NÉGATIF de la règle précédente : sans bandeau ni valeur, le
    document produit doit être le modèle. Sans lui, la comparaison ne dirait
    pas si c'est le bandeau qui ajoute le paragraphe ou le remplissage."""
    octets, _r = F.remplir_document("dc4", {}, bandeau=None)
    assert _paras(io.BytesIO(octets)) == _paras(F.chemin_modele("dc4"))


def test_le_rapport_nomme_ce_qui_n_a_PAS_ete_place():
    """Un formulaire rendu sans dire ce qui manque se lit comme un formulaire
    complet. On provoque une ancre introuvable et on mesure que le rapport la
    nomme au lieu de la perdre."""
    garde = list(F.ANCRES["dc4"])
    try:
        F.ANCRES["dc4"] = garde + [{"rubrique": "titulaire",
                                    "ancre": "Un intitulé qui n'existe pas"}]
        _octets, rapport = _produit()
        manques = [x["rubrique"] for x in rapport["non_places"]]
        assert manques == ["titulaire"], rapport["non_places"]
        assert rapport["non_places"][0]["motif"] == "emplacement_introuvable"
    finally:
        F.ANCRES["dc4"] = garde
    assert _produit()[1]["non_places"] == [], "la table n'a pas été remise"


def test_une_rubrique_sans_valeur_est_ignoree_et_non_placee_a_vide(document):
    """Écrire une chaîne vide dans une case la ferait passer pour renseignée.
    Ce qui n'a pas de valeur ressort dans `ignores`, avec son motif."""
    _out, _mod, rapport = document
    ancrees = {a["rubrique"] for a in F.ANCRES["dc4"]}
    traitees = {x["rubrique"] for x in
                rapport["places"] + rapport["non_places"] + rapport["ignores"]}
    assert traitees == ancrees, ancrees - traitees
    for x in rapport["ignores"]:
        assert x["motif"] == "sans_valeur", x
    for x in rapport["places"]:
        assert str(x["valeur"]).strip(), x


def test_le_rapport_dit_quelle_version_du_formulaire_a_ete_remplie(document):
    """Le formulaire porte lui-même sa date de mise à jour en dernière page.
    La rendre permet de dire au client quelle version il dépose — et de
    constater qu'elle a vieilli."""
    out, _mod, rapport = document
    assert rapport["maj"] == "12/10/2023", rapport["maj"]
    assert any(rapport["maj"] in t for t in out), (
        "la date annoncée par la table ne figure pas dans le document : "
        "elle a été recopiée au lieu d'être relevée sur le formulaire")
    assert "ministère" in rapport["source"], rapport["source"]


# ══════════════════════════════════════════════════════════════════════════
# 5. LA ROUTE — CE QUI SORT DU SERVEUR EST BIEN LE FORMULAIRE OFFICIEL
# ══════════════════════════════════════════════════════════════════════════

ORIGINE = {"Origin": "http://localhost"}
CORPS = {"modele": "dc4", "fiche": FICHE, "saisies": SAISIES}


def test_un_visiteur_anonyme_ne_remplit_aucun_formulaire(anonyme):
    """La route reçoit une fiche d'entreprise et rend un document nominatif."""
    for chemin, methode in (("/api/datacenter/marche/formulaire", "post"),
                            ("/api/datacenter/marche/formulaires", "get")):
        r = getattr(anonyme, methode)(chemin, json=CORPS, headers=ORIGINE)
        assert r.status_code in (401, 403), (chemin, r.status_code)


def test_la_route_rend_un_docx_ouvrable_et_rempli(connecte):
    """ON OUVRE CE QUE LE SERVEUR A RENDU. Vérifier le type MIME dirait
    seulement que l'en-tête est juste ; un fichier tronqué le porterait
    aussi."""
    r = connecte.post("/api/datacenter/marche/formulaire", json=CORPS,
                      headers=ORIGINE)
    assert r.status_code == 200, r.data[:200]
    assert "wordprocessingml" in r.headers["Content-Type"], r.headers
    assert "non-signe" in r.headers.get("Content-Disposition", "")
    paras = _paras(io.BytesIO(r.data))
    assert paras[0] == _net(F.BANDEAU)
    assert FICHE["raison_sociale"] in paras, "la fiche n'est pas entrée"
    assert FICHE["siret"] in paras, "le SIRET n'est pas entré"


def test_la_route_dit_dans_un_en_tete_ce_qui_n_a_pas_ete_place(connecte):
    """Un téléchargement ne rend pas de JSON, et la page a besoin de dire ce
    qui manque : sans cela, un formulaire partiel se lirait comme complet."""
    import json as _json
    r = connecte.post("/api/datacenter/marche/formulaire", json=CORPS,
                      headers=ORIGINE)
    etat = _json.loads(r.headers["X-Remplissage"])
    assert etat["places"] >= 10, etat
    assert etat["maj"] == "12/10/2023", etat
    assert isinstance(etat["non_places"], list)
    assert isinstance(etat["ignores"], list)


def test_un_modele_inconnu_est_refuse_en_400_et_les_choix_sont_dits(connecte):
    """Refuser sans dire ce qui est possible ferait deviner le nom du
    formulaire."""
    r = connecte.post("/api/datacenter/marche/formulaire",
                      json=dict(CORPS, modele="dc9"), headers=ORIGINE)
    assert r.status_code == 400, r.status_code
    j = r.get_json()
    assert j["error"] == "modele_inconnu"
    assert "dc4" in j["disponibles"]


def test_la_route_ne_declare_rien_meme_avec_une_fiche_complete(connecte):
    """LA LIGNE À NE PAS FRANCHIR. Aucune des affirmations du cadre K1 ne doit
    apparaître comme cochée ou reprise dans le document produit : leur
    fausseté est sanctionnée pénalement, et une case remplie par un programme
    est une déclaration que personne n'a faite."""
    r = connecte.post("/api/datacenter/marche/formulaire", json=CORPS,
                      headers=ORIGINE)
    produit = _paras(io.BytesIO(r.data))
    modele = _paras(F.chemin_modele("dc4"))
    k = next(i for i, t in enumerate(produit)
             if t.startswith("K1 - Le sous-traitant déclare sur l'honneur"))
    assert produit[k:] == modele[k - 1:], (
        "la zone des déclarations et des signatures a été touchée par la "
        "route")


def test_l_etat_des_modeles_distingue_pret_absent_et_altere(connecte):
    """La page ne devine pas : un bouton proposé pour un modèle absent
    produirait une erreur au clic, un bouton caché ferait croire que la
    fonction n'existe pas."""
    r = connecte.get("/api/datacenter/marche/formulaires", headers=ORIGINE)
    assert r.status_code == 200
    j = r.get_json()
    assert j["etat"]["prets"] == ["dc4"], j["etat"]
    assert set(j["etat"]) == {"prets", "manquants", "alteres"}
    # L'EMPREINTE NE SORT PAS. Elle sert à refuser un fichier modifié ; la
    # publier n'aide personne et invite à la reproduire.
    assert "empreinte" not in j["modeles"]["dc4"], j["modeles"]["dc4"]
    assert j["modeles"]["dc4"]["maj"] == "12/10/2023"
    assert "NON SIGNÉ" in j["bandeau"]
