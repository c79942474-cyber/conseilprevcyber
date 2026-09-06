# -*- coding: utf-8 -*-
"""Les QUATRE formulaires de l'État, remplis de ce qui est déjà écrit ailleurs.

CE QUE CE FICHIER TIENT. Répondre à une consultation, c'est déposer quatre
imprimés du ministère de l'économie qui redemandent les mêmes informations :
DC1 (lettre de candidature) et DC2 (déclaration du candidat) au dossier de
candidature, ATTRI1 (acte d'engagement) et DC4 (déclaration de sous-traitance)
au dossier d'offre. L'acheteur, l'objet, les lots, la dénomination, le SIRET,
le signataire y figurent deux, trois ou quatre fois — et ce sont les recopies
d'un formulaire à l'autre qui produisent les incohérences dont les offres
meurent.

LES RUBRIQUES SONT RELEVÉES SUR LES FORMULAIRES, PAS RECONSTITUÉES. Les cadres
cités dans les libellés (A, B1, K1, L…) sont ceux des imprimés eux-mêmes, lus
dans leur version publiée : ATTRI1 va de A à D, DC4 de A à N. C'est ce qui rend
mesurable la question « ce report couvre-t-il le formulaire ? » — autrement,
il n'y aurait rien à comparer.

CE QUE CE MODULE NE FERA JAMAIS, ET CES RÈGLES LE TIENNENT :
  · il ne PRODUIT aucun formulaire — un fac-similé serait refusé, ou pire,
    accepté et faux ;
  · il ne PRÉ-REMPLIT aucune déclaration — une case cochée par un programme
    est une déclaration que personne n'a faite ;
  · il n'INVENTE rien sur un tiers — un DC4 parle d'une AUTRE entreprise que
    celle dont on tient la fiche ;
  · il ne COMPTE PAS comme manquant ce qui n'est pas dû.
"""
import html
import io
import json
import os
import re
import subprocess
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc as A                                                # noqa: E402

FICHE = {
    "raison_sociale": "Bureau d'études Essai", "forme_juridique": "SAS",
    "siret": "80295478500019", "adresse": "5 rue de l'Essai",
    "courriel": "contact@essai.example",
    "representant_nom": "A. Dupont", "representant_qualite": "Président",
}

RC = """RÈGLEMENT DE LA CONSULTATION
Pouvoir adjudicateur : Communauté d'agglomération de l'Essai.
Objet du marché : maîtrise d'œuvre pour un centre de données régional.
Référence de la consultation : 2026-MOE-014.
La consultation est allotie en 3 lots.
"""

# LA SAISIE QUI LÈVE LA CONDITION DU DC4. Elle est nommée ici, une fois : une
# règle qui l'oublierait mesurerait une pièce sans objet en croyant mesurer un
# formulaire.
AVEC_SOUS_TRAITANCE = {"dc4.sous_traitance": "oui — lot 3, génie climatique"}

FORMULAIRES = ("dc1", "dc2", "acte_engagement", "dc4")


def _rempli(**kw):
    an = A.analyser([{"nom": "01_RC.pdf", "texte": RC}])
    return A.remplir(fiche=FICHE, analyse=an, **kw)


def _piece(r, cle):
    for p in r["pieces"]:
        if p["cle"] == cle:
            return p
    raise AssertionError("pièce absente du remplissage : %s" % cle)


def _par_cle(p):
    return {l["cle"]: l for l in p["rubriques"]}


# ══════════════════════════════════════════════════════════════════════════
# 1. LES QUATRE FORMULAIRES SONT LÀ, ET ILS SE REMPLISSENT
# ══════════════════════════════════════════════════════════════════════════

def test_les_quatre_formulaires_de_l_Etat_entrent_dans_le_meme_report():
    """DC1 et DC2 y étaient ; ATTRI1 n'avait aucune rubrique et DC4 était
    absent du module tout entier. Un dossier d'offre qu'on croit préparé parce
    que l'écran ne montre que la candidature est pire qu'un écran vide."""
    r = _rempli(saisies=AVEC_SOUS_TRAITANCE)
    for cle in FORMULAIRES:
        p = _piece(r, cle)
        assert p["voie"] == "remplir", (cle, p["voie"])
        assert p["mesurable"] is True, cle
        assert p["total"] >= 5, (cle, p["total"])
    assert [_piece(r, c)["dossier"] for c in FORMULAIRES] == [
        "candidature", "candidature", "offre", "offre"]


def test_les_rubriques_couvrent_TOUS_les_cadres_des_deux_imprimes():
    """LA COUVERTURE SE MESURE CONTRE LE FORMULAIRE, pas contre elle-même.
    Compter les rubriques dirait seulement qu'il y en a beaucoup ; ce qu'on
    veut savoir, c'est si un cadre de l'imprimé n'a AUCUNE rubrique en face —
    car c'est exactement ce qui se déposerait vide.

    ATTRI1 : A (objet et ce que l'acte couvre), B1 (pièces visées,
    identification, prix), B2 (groupement), B3 (compte), B4 (avance),
    B5 (durée et reconductions), C (signature du titulaire), D (acheteur).
    DC4 : A (acheteur), B (objet), C (nature de la déclaration),
    D (soumissionnaire), E (sous-traitant), F (prestations),
    G (prix), H (paiement), I (durée), J (capacités), K1 (déclaration sur
    l'honneur), L (cessions et nantissements).
    """
    attendu = {
        "acte_engagement": {"A", "B1", "B2", "B3", "B4", "B5", "C", "D"},
        "dc4": {"A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K1", "L"},
    }
    for cle, cadres in attendu.items():
        vus = set()
        for rub in A.RUBRIQUES[cle]:
            for premier, second in re.findall(
                    r"\(cadres? ([A-Z0-9]+)(?: et ([A-Z0-9]+))?\)",
                    rub["libelle"]):
                vus.add(premier)
                if second:
                    vus.add(second)
        assert cadres - vus == set(), (
            "%s : aucun report en face du ou des cadres %s — ils se "
            "déposeraient vides" % (cle, sorted(cadres - vus)))


def test_les_quatre_formulaires_disent_LA_MEME_CHOSE_du_candidat():
    """LA RAISON D'ÊTRE DU MODULE, MESURÉE. Une dénomination ou un SIRET
    recopiés à la main sur quatre imprimés finissent par diverger — et une
    divergence entre deux pièces du même dossier se voit avant le prix.

    On ne vérifie pas que les rubriques EXISTENT : on compare les VALEURS
    rendues. Une rubrique qui aurait basculé en `saisie` ressortirait vide et
    ferait tomber cette règle, ce qui est le comportement voulu.
    """
    r = _rempli(saisies=AVEC_SOUS_TRAITANCE)
    partages = {
        "raison_sociale": {"dc1": "candidat", "dc2": "candidat",
                           "acte_engagement": "titulaire", "dc4": "titulaire"},
        "siret": {"dc1": "siret", "dc2": "siret",
                  "acte_engagement": "siret", "dc4": "titulaire_siret"},
    }
    for champ, ou in partages.items():
        valeurs = {}
        for piece, rub in ou.items():
            l = _par_cle(_piece(r, piece))[rub]
            assert l["statut"] == "rempli", (piece, rub, l["statut"])
            valeurs[piece] = l["valeur"]
        assert len(set(valeurs.values())) == 1, (champ, valeurs)
        assert valeurs["dc1"] == FICHE[champ], (champ, valeurs)

    # ET L'ACHETEUR RELEVÉ AU DOSSIER, LUI AUSSI, EST LE MÊME PARTOUT — avec
    # sa citation, pour être vérifié sur la pièce d'où il vient.
    acheteurs = {c: _par_cle(_piece(r, c))["acheteur"]
                 for c in ("dc1", "dc2", "acte_engagement", "dc4")}
    assert len({l["valeur"] for l in acheteurs.values()}) == 1, acheteurs
    for c, l in acheteurs.items():
        assert l["statut"] == "rempli", (c, l["statut"])
        assert l["citation"] and l["citation"]["texte"], c


# ══════════════════════════════════════════════════════════════════════════
# 2. CE QUI N'EST PAS DÛ N'EST PAS COMPTÉ COMME MANQUANT
# ══════════════════════════════════════════════════════════════════════════

def test_le_DC4_est_sans_objet_tant_qu_aucune_sous_traitance_n_est_declaree():
    """Le DC4 n'existe QUE s'il y a sous-traitance : le formulaire lui-même le
    dit — il est fourni « soit au moment du dépôt de l'offre [...] soit en
    cours d'exécution ». Le compter comme un manque chez un candidat qui ne
    sous-traite rien afficherait vingt-trois manques qu'il ne faut pas
    combler."""
    p = _piece(_rempli(), "dc4")
    assert p["sans_objet"] is True
    assert p["conditionnelle"] is True
    assert p["mesurable"] is False
    assert p["complet"] is None and p["pret"] is None
    assert (p["sans_objet_aide"] or "").strip(), (
        "sans objet, mais sans dire pourquoi : elle ressemble à une pièce "
        "oubliée")
    # ET SES RUBRIQUES RESTENT AFFICHÉES : on doit pouvoir lire ce qu'un DC4
    # demande AVANT de savoir si l'on en dépose un.
    assert p["total"] == len(A.RUBRIQUES["dc4"]) >= 20, p["total"]


def test_les_rubriques_sans_objet_ne_comptent_dans_AUCUN_total():
    """Un chiffre faux se croit ; un chiffre absent se cherche. La règle
    mesure l'ÉCART entre les deux dénombrements — sans lui, elle resterait
    verte le jour où plus rien ne serait retranché."""
    r = _rempli()
    e = r["etat"]
    tout = sum(p["total"] for p in r["pieces"])
    compte = sum(p["total"] for p in r["pieces"] if not p["sans_objet"])
    assert e["rubriques"] == compte, (e["rubriques"], compte)
    assert tout - compte == len(A.RUBRIQUES["dc4"]), (tout, compte)
    assert e["sans_objet"] == [_piece(r, "dc4")["nom"]], e["sans_objet"]
    for cle in ("a_saisir", "non_trouvees", "a_declarer", "remplies"):
        assert e[cle] == sum(
            p["compte"][{"non_trouvees": "non_trouve", "remplies": "rempli"}
                        .get(cle, cle)]
            for p in r["pieces"] if not p["sans_objet"]), cle


def test_la_condition_renseignee_fait_entrer_le_DC4_au_decompte():
    """LE TÉMOIN DE LA RÈGLE PRÉCÉDENTE : une pièce qu'on ne compte jamais et
    une pièce qu'on ne compte pas encore ne se distinguent qu'ici."""
    avant = _rempli()["etat"]
    apres = _rempli(saisies=AVEC_SOUS_TRAITANCE)["etat"]
    assert apres["rubriques"] - avant["rubriques"] == len(A.RUBRIQUES["dc4"])
    assert apres["mesurables"] == avant["mesurables"] + 1
    assert apres["sans_objet"] == []
    assert _piece(_rempli(saisies=AVEC_SOUS_TRAITANCE), "dc4")["mesurable"]


# ══════════════════════════════════════════════════════════════════════════
# 3. RIEN N'EST INVENTÉ SUR UN TIERS
# ══════════════════════════════════════════════════════════════════════════

def test_le_sous_traitant_n_est_JAMAIS_pris_dans_la_fiche_du_candidat():
    """UN DC4 PARLE D'UNE AUTRE ENTREPRISE. Rien dans la fiche du candidat ne
    porte le SIRET de son sous-traitant, ni son adresse, ni son représentant.
    Brancher ces cases sur la fiche remplirait le formulaire avec l'identité
    du titulaire à la place de celle du sous-traitant — une faute que personne
    ne verrait, puisque les cases seraient pleines."""
    tiers = [r for r in A.RUBRIQUES["dc4"]
             if r["cle"].startswith("sous_traitant")]
    assert len(tiers) >= 2, [r["cle"] for r in tiers]
    for r in tiers:
        assert r["source"] == "saisie", (r["cle"], r["source"])
    # ET LE REPORT LE DIT : ces cases ressortent à saisir, jamais remplies.
    p = _piece(_rempli(saisies=AVEC_SOUS_TRAITANCE), "dc4")
    for r in tiers:
        l = _par_cle(p)[r["cle"]]
        assert l["statut"] == "a_saisir", (r["cle"], l["statut"], l["valeur"])
        assert (l["aide"] or "").strip(), r["cle"]


def test_aucune_declaration_des_deux_nouveaux_formulaires_n_est_pre_remplie():
    """La fausseté d'une déclaration sur l'honneur est sanctionnée
    pénalement, et une case cochée par un programme est une déclaration que
    personne n'a faite."""
    r = _rempli(saisies=AVEC_SOUS_TRAITANCE)
    vues = 0
    for cle in ("acte_engagement", "dc4"):
        for l in _piece(r, cle)["rubriques"]:
            if l["source"] != "declaration":
                continue
            vues += 1
            assert l["statut"] == "a_declarer", (cle, l["cle"])
            assert l["valeur"] is None, (cle, l["cle"], l["valeur"])
            assert l["texte"].strip(), (cle, l["cle"])
    assert vues == 2, vues


# ══════════════════════════════════════════════════════════════════════════
# 4. CE QU'UNE SIGNATURE ENGAGE — DEUX CHOSES, ET LES CONFONDRE SERAIT FAUX
# ══════════════════════════════════════════════════════════════════════════

def test_l_avertissement_penal_ne_tombe_pas_sur_un_engagement_contractuel():
    """LE DÉFAUT QUE CETTE RÈGLE EMPÊCHE. Le message servi avec une
    déclaration était écrit en dur dans `remplir()` : « cette affirmation
    engage pénalement celui qui la signe ». Exact pour une déclaration
    d'absence d'interdiction de soumissionner — c'est un délit si elle est
    fausse. FAUX pour l'engagement de l'acte d'engagement, qui n'affirme aucun
    fait : il lie au prix, à la durée et aux pièces visées par renvoi.

    Écrit en dur, ce message aurait dit une chose fausse avec l'autorité de ce
    qui ne se discute pas.
    """
    r = _rempli(saisies=AVEC_SOUS_TRAITANCE)
    ae = [l for l in _piece(r, "acte_engagement")["rubriques"]
          if l["source"] == "declaration"][0]
    st = [l for l in _piece(r, "dc4")["rubriques"]
          if l["source"] == "declaration"][0]
    assert ae["engage"] == "contractuel", ae["engage"]
    assert st["engage"] == "penal", st["engage"]
    assert "pénal" not in ae["message"], ae["message"]
    assert "pénal" in st["message"], st["message"]
    assert ae["message"] != st["message"]
    assert ae["engage_nom"] != st["engage_nom"]
    # LES MESSAGES VIENNENT DE LA TABLE, pas d'une rédaction locale : deux
    # rédactions du même avertissement finiraient par ne plus dire la même
    # chose.
    for l in (ae, st):
        assert l["message"] == A.ENGAGEMENTS[l["engage"]]["message"]


def test_chaque_declaration_dit_laquelle_des_deux_natures_elle_engage():
    """Sans nature déclarée, le module devrait DEVINER — et deviner ici, c'est
    prévenir d'une sanction pénale au hasard."""
    for cle, rubriques in A.RUBRIQUES.items():
        for r in rubriques:
            if r["source"] == "declaration":
                assert r.get("engage") in A.ENGAGEMENTS, (cle, r["cle"])


# ══════════════════════════════════════════════════════════════════════════
# 5. LE TEXTE SIGNÉ EST CELUI QU'ON CROIT
# ══════════════════════════════════════════════════════════════════════════

def test_une_ligne_inseree_dans_contient_fait_tomber_le_chargement():
    """UN INDICE VALIDE N'EST PAS UN INDICE JUSTE, et c'est la faute que la
    borne ne voit pas. Une ligne insérée dans `contient` décale toutes les
    suivantes : l'indice reste dans les bornes, rien ne se lève, et le module
    ferait signer « Identification de l'acheteur » à la place d'une
    déclaration sur l'honneur. Chaque `reprend` porte donc un fragment du
    texte visé.

    ON PROVOQUE LE DÉCALAGE PLUTÔT QUE DE CONSTATER L'ACCORD. Vérifier que
    les témoins concordent aujourd'hui ne dit RIEN de ce qui arriverait
    demain : la garde vit au chargement du module, et une règle qui se
    contenterait de relire la table serait verte en même temps qu'elle.
    """
    piece = [p for p in A.DOSSIER_OFFRE if p["cle"] == "dc4"][0]
    garde = list(piece["contient"])
    try:
        piece["contient"] = ["Une ligne insérée en tête"] + garde
        fautes = A._verifier()
    finally:
        piece["contient"] = garde
    assert any("dc4/d_exclusion_st" in f and "témoin" in f for f in fautes), (
        "un décalage d'indice dans `contient` ne serait pas vu : %s" % fautes)
    assert A._verifier() == [], "la table n'a pas été remise en état"


# ══════════════════════════════════════════════════════════════════════════
# 6. CE REPORT N'EST PAS UN FORMULAIRE, ET IL LE DIT
# ══════════════════════════════════════════════════════════════════════════

def test_chaque_piece_designe_sa_famille_d_infobulles():
    """LE GLOSSAIRE TIENT DEUX FAMILLES SÉPARÉES — `piece_candidature` et
    `piece_offre` — et demander la mauvaise n'affiche RIEN. Pas une erreur :
    rien. La clé vient donc du module, où elle se mesure, plutôt que d'un
    littéral recopié dans le script, où elle ne se mesurerait pas."""
    gl = A.glossaire()
    r = _rempli(saisies=AVEC_SOUS_TRAITANCE)
    for p in r["pieces"]:
        assert p["glossaire"] in gl, (p["cle"], p["glossaire"])
        assert p["cle"] in gl[p["glossaire"]], (p["glossaire"], p["cle"])
        assert gl[p["glossaire"]][p["cle"]]["aide"].strip(), p["cle"]
    # LES DEUX FAMILLES SONT RÉELLEMENT UTILISÉES : sans ce témoin, la règle
    # resterait verte si toutes les pièces désignaient la même.
    assert {p["glossaire"] for p in r["pieces"]} == {"piece_candidature",
                                                     "piece_offre"}
    bloc = _js_source("aoRempliRendre")
    assert 'info(p.glossaire + ":" + p.cle)' in bloc, (
        "la page recopie une famille d'infobulles au lieu de la demander au "
        "module : les pièces d'offre n'auraient aucune bulle, sans erreur")


def test_le_report_dit_qu_il_ne_remplace_aucun_formulaire():
    """Un fac-similé de DC1 produit ici serait refusé — ou pire, accepté et
    faux. La réserve n'est pas une politesse : c'est ce qui empêche de
    déposer ce document À LA PLACE des imprimés."""
    note = A.NOTE_REMPLISSAGE
    assert "fac-similé" in note, note
    for sigle in ("DC1", "DC2", "DC4", "ATTRI1"):
        assert sigle in note, (sigle, note)
    md = A.markdown_remplissage(_rempli(saisies=AVEC_SOUS_TRAITANCE))
    assert note in md, "le document exporté sort sans sa réserve"


def test_l_export_separe_les_deux_dossiers_et_signale_ce_qui_est_sans_objet():
    """Ils ne se remettent ni au même moment ni, souvent, sur la même
    plateforme : vingt-trois pièces enchaînées sans séparation feraient
    déposer les unes pour les autres."""
    md = A.markdown_remplissage(_rempli())
    assert "\n## Dossier de candidature\n" in md
    assert "\n## Dossier d'offre\n" in md
    assert md.index("## Dossier de candidature") < md.index("## Dossier d'offre")
    assert "**Sans objet.**" in md, (
        "le DC4 sort de l'export sans dire qu'il est sans objet")
    # ET LE DÉCOMPTE DES PIÈCES PORTE SUR CE QUI EST MESURABLE. « 0 sur 23 »
    # comptait dans son dénominateur les pièces que ce module ne remplit pas :
    # le document et la page disaient deux choses différentes du même dossier.
    e = _rempli()["etat"]
    assert "| Pièces remplissables sans rien à compléter | %d sur %d |" % (
        e["pieces_completes"], e["mesurables"]) in md, md[:900]


# ══════════════════════════════════════════════════════════════════════════
# 7. CE QUE LA PAGE AFFICHE VRAIMENT — LA FONCTION EST EXÉCUTÉE, PAS RELUE
# ══════════════════════════════════════════════════════════════════════════

def _carte_rendue(remplissage):
    """Le HTML que `aoRempliRendre` produit RÉELLEMENT, obtenu en l'exécutant.

    CHERCHER UNE CHAÎNE DANS LE FICHIER SERAIT VERT POUR UNE OCCURRENCE DANS
    UN COMMENTAIRE, et muet sur une erreur de rendu — un `esc(undefined)` ou
    une propriété absente ne se voient qu'en faisant tourner la fonction. Le
    DOM est réduit au strict nécessaire : cette fonction écrit dans UN élément
    et branche des écouteurs sur ce qu'elle vient d'écrire.
    """
    prog = (
        _js_source("esc", "info", "aoMenuDocs", "aoRempliRendre")
        + "\nvar AO_DOC = '';"
        + "\nvar AO_SAISIES = {};"
        + "\nvar AO_ETAT_CLASSE = { rempli: 'ok', a_saisir: 'att',"
          " a_declarer: 'dec', non_trouve: 'att', invalide: 'mal' };"
        + "\nvar CADRE = { glossaire: {} };"
        + "\nvar zone = { innerHTML: '', querySelectorAll: function () "
          "{ return []; } };"
        + "\nfunction $(s) { return s === '#ig-ao-rempli' ? zone : null; }"
        + "\nfunction aoBrancherMenu() {}"
        + "\nfunction aoExporter() {}"
        + "\nfunction aoFicheEnregistrer() {}"
        + "\nfunction aoRemplir() {}"
        + "\nglobal.document = { querySelectorAll: function () { return []; },"
          " querySelector: function () { return null; } };"
        + "\naoRempliRendre(JSON.parse(process.env.AO_REMPLI));"
        + "\nprocess.stdout.write(zone.innerHTML);\n")
    out = subprocess.run(
        ["node"], input=prog, capture_output=True, text=True, timeout=60,
        env=dict(os.environ, AO_REMPLI=json.dumps(remplissage)))
    assert out.returncode == 0, out.stderr[-2000:]
    return html.unescape(out.stdout)


def _js_source(*noms):
    """Les fonctions demandées, extraites de la source SERVIE, par comptage
    d'accolades — recopier leur corps ici éprouverait un script imaginaire."""
    src = io.open(os.path.join(ICI, "ingenierie-dc.js"), encoding="utf-8").read()
    out = []
    for nom in noms:
        i = src.index("\n  function %s(" % nom) + 1
        j = src.index("{", i)
        p, k = 1, src.index("{", i) + 1
        while p:
            if src[k] == "{":
                p += 1
            elif src[k] == "}":
                p -= 1
            k += 1
        out.append(src[i:k])
    return "\n".join(out)


def test_la_carte_d_une_piece_sans_objet_le_dit_sur_la_page():
    """Muette, elle ressemblerait à une pièce oubliée — et ses vingt-trois
    rubriques vides, à autant de manques."""
    h = _carte_rendue(_rempli())
    assert h.count('data-doc="') == 23, h[:300]
    assert "Sans objet — Sans sous-traitance déclarée" in h, (
        "le DC4 s'affiche sans dire qu'il est sans objet")
    # ET LE TÉMOIN NÉGATIF : la mention disparaît quand la condition est levée.
    assert "Sans objet —" not in _carte_rendue(_rempli(saisies=AVEC_SOUS_TRAITANCE))


def test_la_page_distingue_a_l_ecran_les_deux_natures_d_engagement():
    """Servir le même avertissement sur une déclaration sur l'honneur et sur
    l'engagement d'un acte d'engagement dirait une chose fausse."""
    h = _carte_rendue(_rempli(saisies=AVEC_SOUS_TRAITANCE))
    for nature in A.ENGAGEMENTS.values():
        assert nature["nom"] in h, nature["nom"]
    assert h.count(A.ENGAGEMENTS["contractuel"]["nom"]) == 1, (
        "l'engagement contractuel de l'ATTRI1 n'apparaît pas exactement une "
        "fois à l'écran")
    assert A.ENGAGEMENTS["penal"]["message"] in h
    assert A.ENGAGEMENTS["contractuel"]["message"] in h
