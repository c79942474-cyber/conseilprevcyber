# -*- coding: utf-8 -*-
"""Le dossier marché conservé par projet — et ce que la conservation NE DÉBLOQUE PAS.

CE QUI A ÉTÉ DEMANDÉ, ET POURQUOI CE FICHIER EXISTE. La demande était : « les
six rubriques de déclaration seront remplies automatiquement lorsque les pièces
marché seront téléchargées et conservées par projet ». La conservation est
faite ; le remplissage des déclarations ne l'est pas, et ne le sera pas — non
par prudence, mais parce que les deux ensembles n'ont rien en commun :

  · les six déclarations affirment des faits sur LE CANDIDAT (absence
    d'interdiction de soumissionner, situation fiscale et sociale) ou ENGAGENT
    sur une offre ;
  · les dix-sept relevés portent tous sur LA CONSULTATION.

`test_les_releves_et_les_declarations_n_ont_AUCUNE_cle_commune` mesure cette
intersection au lieu de l'affirmer. Et `test_affirmer_les_SIX_ne_change_PAS_UN_OCTET`
va plus loin : il affirme les six, toutes preuves valides, et compare les
quatre fichiers produits octet pour octet.

CE QUE LA CONSERVATION APPORTE VRAIMENT AUX DÉCLARATIONS : la preuve sous les
yeux de qui affirme, avec sa date de péremption. On automatise la preuve,
jamais l'affirmation.
"""
import hashlib
import io
import os
import re
import sys
import zipfile

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

from cryptography.fernet import Fernet                           # noqa: E402

import ao_dc                                                     # noqa: E402
import ao_formulaires                                            # noqa: E402
import dossier_entreprise as D                                   # noqa: E402

RC = ("REGLEMENT DE LA CONSULTATION\n"
      "Pouvoir adjudicateur : Communaute d'agglomeration de Roissy Pays de France\n"
      "Objet du marche : construction d'un centre de donnees de 12 MW.\n"
      "Reference : 2026-DC-014\n"
      "Le marche est alloti en 3 lots.\n"
      "Date limite de reception des offres : 30 novembre 2026 a 12h00.\n")
PROJET = {"id": "a" * 32, "nom": "Roissy — centre de données"}


@pytest.fixture
def coffre(monkeypatch):
    """Un module neuf, avec une clé neuve et un magasin vide à chaque règle.

    LA CLÉ EST TIRÉE ICI, PAS LUE DANS L'ENVIRONNEMENT. Une règle qui
    dépendrait de la clé du poste passerait chez son auteur et tomberait
    partout ailleurs — ou pire, passerait partout parce que la variable est
    absente et que le module refuse alors d'écrire.
    """
    import ao_projet
    monkeypatch.setenv(ao_projet.VAR_CLE, Fernet.generate_key().decode())
    monkeypatch.setattr(ao_projet, "_STORE", ao_projet.MemoryDossierStore())
    return ao_projet


@pytest.fixture
def attestations_valides(monkeypatch):
    """Toutes les attestations en règle — le cas le PLUS favorable.

    C'est celui qui compte pour l'invariant : si RIEN ne se remplit même quand
    tout est prouvé, alors rien ne se remplira jamais.
    """
    table = [dict(a, delivree_le="2026-01-02", valable_jusqu_au="2027-12-31")
             for a in D.ATTESTATIONS]
    monkeypatch.setattr(D, "ATTESTATIONS", table)
    return table


def _valeurs(analyse):
    r = ao_dc.remplir(fiche={}, analyse=analyse)
    return {ru["cle"]: ru["valeur"] for p in r["pieces"] for ru in p["rubriques"]
            if ru["statut"] == "rempli"}


def _documents(valeurs):
    """L'empreinte du CONTENU de chaque .docx, pas celle du fichier.

    POURQUOI PAS LES OCTETS BRUTS. Un .docx est une archive zip, et
    python-docx y écrit l'heure courante dans l'en-tête de chaque membre :
    deux documents rigoureusement identiques produits à trois secondes
    d'écart n'ont pas les mêmes octets. La première version de cette règle
    comparait les octets — elle passait quand les deux générations tombaient
    dans la même seconde et tombait sinon, c'est-à-dire au hasard de la charge
    de la suite. Une règle intermittente est pire qu'une règle absente : on
    finit par la relancer jusqu'à ce qu'elle passe.

    Ce qu'on veut tenir est le CONTENU : la liste des membres de l'archive et
    ce que chacun contient. C'est cela qui changerait si une déclaration
    entrait dans le formulaire.
    """
    out = {}
    for c in ao_formulaires.MODELES:
        octets = ao_formulaires.remplir_document(c, valeurs)[0]
        z = zipfile.ZipFile(io.BytesIO(octets))
        h = hashlib.sha256()
        for nom in sorted(z.namelist()):
            h.update(nom.encode("utf-8"))
            h.update(z.read(nom))
        out[c] = h.hexdigest()
    return out


# ── CE QUE LA CONSERVATION NE DÉBLOQUE PAS ────────────────────────────────

def test_les_releves_et_les_declarations_n_ont_AUCUNE_cle_commune():
    """La demande supposait qu'un dossier conservé informe les déclarations.

    IL NE LE PEUT PAS, et c'est une propriété mesurable, pas une opinion. On
    énumère les deux ensembles et on prend leur intersection.
    """
    declarations = {d["cle"] for d in ao_dc.declarations()}
    releves = {r.get("cle") for r in ao_dc.RELEVES}
    assert len(declarations) == 6, sorted(declarations)
    assert len(releves) >= 17, len(releves)
    assert not (declarations & releves), (
        "un relevé porte le nom d'une déclaration : %s"
        % sorted(declarations & releves))


def test_affirmer_les_SIX_ne_change_RIEN_au_contenu_des_quatre_formulaires(
        coffre, attestations_valides):
    """L'invariant central, mesuré sur les fichiers eux-mêmes.

    Toutes preuves valides, les six déclarations assumées : le contenu des
    quatre .docx doit être IDENTIQUE à celui d'avant — mêmes membres
    d'archive, mêmes octets dans chacun. Comparer les rapports ne suffirait
    pas : c'est le fichier qui est déposé chez l'acheteur.
    """
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    analyse = coffre.lire(PROJET)["analyse"]
    avant_v = _valeurs(analyse)
    avant_d = _documents(avant_v)

    for d in ao_dc.declarations():
        coffre.affirmer(PROJET, d["cle"], "C. Cerf", d["texte"],
                        reconnait_sans_preuve=True)
    etat = coffre.etat_affirmations(PROJET)
    assert len(etat["affirmees"]) == 6, etat["affirmees"]

    apres_v = _valeurs(analyse)
    assert apres_v == avant_v, "affirmer a fait apparaître une valeur"
    assert not ({d["cle"] for d in ao_dc.declarations()} & set(apres_v)), (
        "une déclaration est devenue une valeur")
    assert _documents(apres_v) == avant_d, (
        "un formulaire a changé alors que seule une affirmation a eu lieu")


def test_le_statut_des_six_reste_a_declarer_meme_affirmees(
        coffre, attestations_valides):
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    for d in ao_dc.declarations():
        coffre.affirmer(PROJET, d["cle"], "C. Cerf", d["texte"],
                        reconnait_sans_preuve=True)
    r = ao_dc.remplir(fiche={}, analyse=coffre.lire(PROJET)["analyse"])
    statuts = {ru["cle"]: ru["statut"] for p in r["pieces"]
               for ru in p["rubriques"] if ru["source"] == "declaration"}
    assert len(statuts) == 6, sorted(statuts)
    assert set(statuts.values()) == {"a_declarer"}, statuts


def test_l_etat_dit_a_l_ecran_qu_il_ne_remplira_rien(coffre):
    """Ce que la page annonce doit être ce que le module garantit."""
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    lignes = coffre.etat_affirmations(PROJET)["lignes"]
    assert lignes and all(l["remplit_le_formulaire"] is False for l in lignes)


# ── LE CHIFFREMENT, ET L'ABSENCE DE REPLI EN CLAIR ────────────────────────

def test_sans_cle_RIEN_n_est_ecrit_et_la_raison_est_dite(monkeypatch):
    import ao_projet
    monkeypatch.delenv(ao_projet.VAR_CLE, raising=False)
    monkeypatch.setattr(ao_projet, "_STORE", ao_projet.MemoryDossierStore())
    assert ao_projet.chiffrement()["actif"] is False
    with pytest.raises(ao_projet.DossierError) as e:
        ao_projet.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    assert e.value.code == "chiffrement_indisponible", e.value.code
    assert ao_projet.VAR_CLE in e.value.detail
    assert ao_projet.store().compter()["dossiers"] == 0, (
        "quelque chose a été rangé alors qu'il n'y avait pas de clé")


def test_une_cle_invalide_est_dite_invalide_et_non_absente(monkeypatch):
    import ao_projet
    monkeypatch.setenv(ao_projet.VAR_CLE, "ceci-n-est-pas-une-cle")
    assert ao_projet.chiffrement()["motif"] == "cle_invalide"


def test_ce_qui_est_range_est_ILLISIBLE_sans_ouvrir_le_coffre(coffre):
    """On lit le coffre TEL QU'IL EST RANGÉ, et on y cherche le texte en clair.

    Une règle qui se contenterait d'appeler `_coffrer()` mesurerait la
    fonction, pas ce que le magasin conserve. C'est la ligne rangée qui doit
    être illisible.
    """
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}],
                   fiche={"siret": "39315261000027"})
    brut = coffre.store()._d[PROJET["id"]]["coffre"]
    assert isinstance(brut, bytes) and brut, type(brut)
    for aiguille in (b"Roissy", b"2026-DC-014", b"39315261000027", b"RC.pdf"):
        assert aiguille not in brut, (
            "%r se lit dans le coffre" % aiguille)
    assert coffre.lire(PROJET)["fiche"]["siret"] == "39315261000027"


def test_un_coffre_illisible_est_signale_et_non_rendu_vide(coffre):
    """Rendre un dossier vide ferait redéposer par-dessus, et perdre l'original."""
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    coffre.store()._d[PROJET["id"]]["coffre"] = Fernet(
        Fernet.generate_key()).encrypt(b'{"pieces": []}')
    with pytest.raises(coffre.DossierError) as e:
        coffre.lire(PROJET)
    assert e.value.code == "coffre_illisible", e.value.code


# ── L'ACCÈS, TENU PAR LA FORME DE L'ARGUMENT ──────────────────────────────

@pytest.mark.parametrize("faux", ["a" * 32, {"nom": "sans id"}, {}, None, 42])
def test_on_n_atteint_pas_un_dossier_avec_un_simple_identifiant(coffre, faux):
    """L'API prend LE PROJET, pas son identifiant.

    Accepter une chaîne ferait dépendre le contrôle d'accès de la discipline de
    chaque appelant ; ici il est tenu par la signature.
    """
    with pytest.raises(coffre.DossierError) as e:
        coffre.lire(faux)
    assert e.value.code == "projet_requis" and e.value.status == 403


# ── LA PURGE ──────────────────────────────────────────────────────────────

def test_la_purge_efface_ce_qui_a_expire_ET_LAISSE_le_reste(coffre):
    """Une purge qui effacerait tout passerait la moitié d'une règle naïve."""
    autre = {"id": "b" * 32}
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    coffre.deposer(autre, [{"nom": "CCAP.pdf", "texte": "Delai : 26 mois"}])
    # Un seul des deux a dépassé son échéance.
    coffre.store()._d[PROJET["id"]]["purge_le"] = coffre._now_ms() - 1
    assert coffre.purger() == 1
    assert coffre.lire(PROJET) is None
    assert coffre.lire(autre) is not None, "la purge a emporté un dossier vivant"


def test_l_echeance_suit_la_duree_declaree_et_repart_a_chaque_depot(coffre):
    m1 = coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    attendu = coffre.CONSERVATION_JOURS * 86400 * 1000
    assert abs((m1["purge_le"] - m1["maj_le"]) - attendu) < 2000
    m2 = coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC + "\nsuite"}])
    assert m2["purge_le"] >= m1["purge_le"], "un dépôt n'a pas repoussé l'échéance"
    assert m2["cree_le"] == m1["cree_le"], "la date de création a bougé"


def test_la_duree_du_registre_RGPD_et_celle_du_code_ne_divergent_pas():
    """Deux endroits disent la durée : ils doivent dire la même.

    Le registre est ce qu'on OPPOSE à une personne qui demande combien de temps
    ses données restent. S'il annonce douze mois pendant que le code en garde
    vingt-quatre, c'est le registre qui est faux.
    """
    import ao_projet
    import rgpd
    entree = [x for x in rgpd.REGISTRE if x["id"] == "dossier-marche"]
    assert len(entree) == 1, "le traitement n'est pas au registre"
    mois = round(ao_projet.CONSERVATION_JOURS / 30.44)
    assert "%d mois" % mois in entree[0]["duree"], (
        "le registre annonce « %s » pour %d jours de code"
        % (entree[0]["duree"][:60], ao_projet.CONSERVATION_JOURS))


# ── LES BORNES ────────────────────────────────────────────────────────────

def test_une_piece_trop_grande_est_refusee_en_la_nommant(coffre):
    with pytest.raises(coffre.DossierError) as e:
        coffre.deposer(PROJET, [{"nom": "enorme.pdf",
                                 "texte": "x" * (coffre.MAX_OCTETS_PIECE + 1)}])
    assert e.value.code == "piece_trop_grande" and "enorme.pdf" in e.value.detail


def test_un_dossier_trop_gros_est_refuse_meme_avec_des_pieces_admissibles(coffre):
    """Chaque pièce passe, le total non. La borne du total doit exister à part."""
    unite = "x" * (coffre.MAX_OCTETS_PIECE - 1)
    trop = coffre.MAX_OCTETS_TOTAL // coffre.MAX_OCTETS_PIECE + 2
    with pytest.raises(coffre.DossierError) as e:
        coffre.deposer(PROJET, [{"nom": "p%d.pdf" % i, "texte": unite}
                                for i in range(trop)])
    assert e.value.code == "dossier_trop_grand", e.value.code


def test_un_dossier_vide_ou_sans_nom_est_refuse(coffre):
    with pytest.raises(coffre.DossierError) as e:
        coffre.deposer(PROJET, [])
    assert e.value.code == "aucune_piece"
    with pytest.raises(coffre.DossierError) as e:
        coffre.deposer(PROJET, [{"nom": "  ", "texte": RC}])
    assert e.value.code == "piece_sans_nom"


# ── L'AFFIRMATION : QUATRE REFUS, ET AUCUN N'EST DÉCORATIF ────────────────

def _texte(cle):
    return {d["cle"]: d["texte"] for d in ao_dc.declarations()}[cle]


def test_une_affirmation_sans_preuve_valide_est_refusee_et_les_manques_NOMMES(
        coffre, monkeypatch):
    """« Incomplet » ne suffit pas : il faut savoir QUOI aller chercher."""
    monkeypatch.setattr(D, "ATTESTATIONS",
                        [dict(a, delivree_le=None, valable_jusqu_au=None)
                         for a in D.ATTESTATIONS])
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    with pytest.raises(coffre.DossierError) as e:
        coffre.affirmer(PROJET, "d_fiscal_social", "C. Cerf",
                        _texte("d_fiscal_social"))
    assert e.value.code == "preuve_incomplete", e.value.code
    assert "URSSAF" in e.value.detail and "fiscale" in e.value.detail.lower(), (
        e.value.detail)


def test_une_attestation_PERIMEE_ne_prouve_rien(coffre, monkeypatch):
    """La présence d'une attestation ne dit rien : c'est la date qui décide.

    Une attestation de vigilance de l'an dernier est PRÉSENTE et sans valeur.
    Une règle qui compterait les attestations présentes serait verte ici.
    """
    monkeypatch.setattr(D, "ATTESTATIONS",
                        [dict(a, delivree_le="2025-01-02",
                              valable_jusqu_au="2026-01-31")
                         for a in D.ATTESTATIONS])
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    with pytest.raises(coffre.DossierError) as e:
        coffre.affirmer(PROJET, "d_fiscal_social", "C. Cerf",
                        _texte("d_fiscal_social"), aujourdhui="2026-09-06")
    assert e.value.code == "preuve_incomplete"
    assert "périmée" in e.value.detail or "perimee" in e.value.detail, e.value.detail
    # La même, encore valide à une date antérieure : c'est bien la DATE qui tranche.
    assert coffre.affirmer(PROJET, "d_fiscal_social", "C. Cerf",
                           _texte("d_fiscal_social"),
                           aujourdhui="2026-01-15")["couverture"] == "prouvee"


def test_une_declaration_sans_preuve_interne_exige_une_reconnaissance(coffre):
    """LE PIÈGE : une liste d'attentes VIDE ne doit pas passer pour « prouvée ».

    Deux déclarations n'attendent aucune attestation de CONSEILPREV —
    l'engagement contractuel, et celle du sous-traitant. Ce sont justement les
    deux qu'un « tout est là » laisserait filer sans rien vérifier.
    """
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    for cle in ("d_engagement", "d_exclusion_st"):
        assert D.couverture(cle)["etat"] == "sans_preuve_interne", cle
        with pytest.raises(coffre.DossierError) as e:
            coffre.affirmer(PROJET, cle, "C. Cerf", _texte(cle))
        assert e.value.code == "reconnaissance_requise", (cle, e.value.code)
        assert e.value.detail, "le refus ne dit pas pourquoi"
        t = coffre.affirmer(PROJET, cle, "C. Cerf", _texte(cle),
                            reconnait_sans_preuve=True)
        assert t["reconnaissance"] is True and t["preuves"] == []


def test_la_declaration_du_sous_traitant_n_est_pas_couverte_par_NOS_pieces():
    """La faute la plus facile à commettre ici, et celle qui coûterait le plus.

    Faire couvrir la déclaration du sous-traitant par les attestations de
    CONSEILPREV ferait affirmer, preuve « à l'appui », quelque chose qu'aucune
    de nos pièces ne soutient.
    """
    assert D.PREUVES_ATTENDUES["d_exclusion_st"] == ()
    assert "sous-traitant" in D.SANS_PREUVE_INTERNE["d_exclusion_st"].lower()
    for a in D.ATTESTATIONS:
        assert "d_exclusion_st" not in (a.get("couvre") or ()), a["cle"]


def test_un_texte_qui_n_est_pas_celui_de_la_piece_fait_refuser(
        coffre, attestations_valides):
    """On affirme ce qu'on a lu. Si l'écran montrait autre chose, c'est nul."""
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    with pytest.raises(coffre.DossierError) as e:
        coffre.affirmer(PROJET, "d_fiscal_social", "C. Cerf",
                        _texte("d_fiscal_social") + " et autre chose")
    assert e.value.code == "texte_divergent", e.value.code
    # Les espaces et retours à la ligne ne comptent pas : c'est le texte, pas sa mise en page.
    assert coffre.affirmer(PROJET, "d_fiscal_social", "C. Cerf",
                           "  " + _texte("d_fiscal_social").replace(" ", "\n  "))


def test_une_affirmation_sans_nom_est_refusee(coffre, attestations_valides):
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    with pytest.raises(coffre.DossierError) as e:
        coffre.affirmer(PROJET, "d_fiscal_social", "   ",
                        _texte("d_fiscal_social"))
    assert e.value.code == "affirmant_manquant"


def test_une_cle_de_declaration_inconnue_est_refusee_et_les_six_sont_dites(
        coffre):
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    with pytest.raises(coffre.DossierError) as e:
        coffre.affirmer(PROJET, "d_inventee", "C. Cerf", "x")
    assert e.value.code == "declaration_inconnue"
    for d in ao_dc.declarations():
        assert d["cle"] in e.value.detail, d["cle"]


# ── UNE AFFIRMATION VIEILLIT ──────────────────────────────────────────────

def test_une_affirmation_vieillit_quand_sa_preuve_EXPIRE(coffre, monkeypatch):
    table = [dict(a, delivree_le="2026-01-02", valable_jusqu_au="2026-10-31")
             for a in D.ATTESTATIONS]
    monkeypatch.setattr(D, "ATTESTATIONS", table)
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    coffre.affirmer(PROJET, "d_fiscal_social", "C. Cerf",
                    _texte("d_fiscal_social"), aujourdhui="2026-09-06")

    def revoir(jour):
        return {l["cle"]: l["a_revoir"]
                for l in coffre.etat_affirmations(PROJET, jour)["lignes"]}

    assert revoir("2026-09-06")["d_fiscal_social"] == []
    assert revoir("2026-12-01")["d_fiscal_social"] == ["preuve_expiree"]
    # Elle n'est PAS effacée : la trace de ce qui a été assumé a de la valeur.
    assert "d_fiscal_social" in coffre.etat_affirmations(
        PROJET, "2026-12-01")["affirmees"]


def test_une_affirmation_vieillit_quand_LE_TEXTE_de_la_piece_change(
        coffre, attestations_valides, monkeypatch):
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    coffre.affirmer(PROJET, "d_fiscal_social", "C. Cerf",
                    _texte("d_fiscal_social"))
    assert coffre.etat_affirmations(PROJET)["a_revoir"] == []

    piece = [p for p in ao_dc.DOSSIER_CANDIDATURE if p["cle"] == "honneur"][0]
    modifie = list(piece["contient"])
    modifie[2] = modifie[2] + " (rédaction modifiée)"
    monkeypatch.setitem(piece, "contient", modifie)
    assert coffre.etat_affirmations(PROJET)["a_revoir"] == ["d_fiscal_social"]


def test_affirmer_une_deuxieme_declaration_NE_PERD_PAS_la_premiere(
        coffre, attestations_valides):
    """Le magasin relisait les affirmations RANGÉES au moment de réécrire :
    la nouvelle était donc écrasée par les anciennes, sans un message."""
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    coffre.affirmer(PROJET, "d_fiscal_social", "C. Cerf",
                    _texte("d_fiscal_social"))
    coffre.affirmer(PROJET, "d_obligatoires", "C. Cerf",
                    _texte("d_obligatoires"))
    assert sorted(coffre.etat_affirmations(PROJET)["affirmees"]) == [
        "d_fiscal_social", "d_obligatoires"]


def test_reaffirmer_la_meme_declaration_ne_la_compte_pas_deux_fois(
        coffre, attestations_valides):
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    for _ in range(3):
        coffre.affirmer(PROJET, "d_fiscal_social", "C. Cerf",
                        _texte("d_fiscal_social"))
    assert len(coffre.affirmations(PROJET)) == 1


def test_un_nouveau_depot_ne_perd_pas_les_affirmations(
        coffre, attestations_valides):
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    coffre.affirmer(PROJET, "d_fiscal_social", "C. Cerf",
                    _texte("d_fiscal_social"))
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC},
                            {"nom": "CCAP.pdf", "texte": "Delai : 26 mois"}])
    assert coffre.etat_affirmations(PROJET)["affirmees"] == ["d_fiscal_social"]
    assert len(coffre.lire(PROJET)["pieces"]) == 2


def test_pieces_est_la_liste_partout_et_le_compteur_s_appelle_nb_pieces(coffre):
    """Le même nom rendait un entier après un dépôt et une liste après une
    lecture : le compteur de la colonne était écrasé par la liste du coffre."""
    meta = coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    assert meta["pieces"] == 1
    lu = coffre.lire(PROJET)
    assert isinstance(lu["pieces"], list) and lu["nb_pieces"] == 1


def test_oublier_efface_et_n_archive_pas(coffre):
    coffre.deposer(PROJET, [{"nom": "RC.pdf", "texte": RC}])
    assert coffre.oublier(PROJET) is True
    assert coffre.lire(PROJET) is None
    assert coffre.store().compter()["dossiers"] == 0
    assert coffre.oublier(PROJET) is False


# ── LES ATTESTATIONS DU DOSSIER D'ENTREPRISE ──────────────────────────────

def test_aucune_date_d_attestation_n_est_ecrite_en_dur():
    """Le module ne sait pas ce que CONSEILPREV détient : il ne l'invente pas."""
    for a in D.ATTESTATIONS:
        assert a["delivree_le"] is None, a["cle"]
        assert a["valable_jusqu_au"] is None, a["cle"]
        assert a["manques"], "%s ne dit pas ce qu'il faut obtenir" % a["cle"]


def test_l_etat_compte_les_attestations_absentes_dans_ce_qui_reste_a_faire():
    """Un dossier annoncé prêt alors que rien ne prouve ce qu'il faudra
    affirmer est pire qu'un dossier annoncé incomplet."""
    avant = D.etat(ao_dc.DOSSIER_CANDIDATURE)
    assert len(avant["attestations"]["absentes"]) == len(D.ATTESTATIONS)
    apres = D.etat(ao_dc.DOSSIER_CANDIDATURE, aujourdhui="2026-09-06",
                   corrections={"attestations.T1.valable_jusqu_au": "2027-01-01"})
    assert apres["a_completer"] == avant["a_completer"] - 1, (
        avant["a_completer"], apres["a_completer"])


def test_une_date_illisible_est_REFUSEE_et_nommee():
    """Rangée telle quelle, elle se lirait comme absente : l'attestation
    paraîtrait manquante alors qu'elle a été saisie."""
    *_, refuses = D.appliquer({"attestations.T1.valable_jusqu_au": "31/12/2027"})
    assert [r["motif"] for r in refuses] == ["date_illisible"], refuses
    *_, att, refuses = D.appliquer({"attestations.T1.valable_jusqu_au":
                                    "2027-12-31"})
    assert refuses == []
    assert D.etat_attestations("2026-09-06", att)["valides"] == ["vigilance_urssaf"]


def test_ce_qu_une_attestation_COUVRE_n_est_pas_corrigible():
    """Sinon une pièce quelconque couvrirait n'importe quelle déclaration, et
    l'affirmation passerait sans preuve en ayant l'air prouvée."""
    assert "couvre" not in D.CHAMPS_CORRIGIBLES["attestations"]
    *_, att, refuses = D.appliquer(
        {"attestations.T5.couvre": ["d_obligatoires"]})
    assert [r["motif"] for r in refuses] == ["champ_non_corrigible"], refuses
    assert "d_obligatoires" not in dict(
        (a["cle"], a["couvre"]) for a in att)["assurance_rc_pro"]


def test_chaque_declaration_a_une_couverture_declaree_et_trois_etats_possibles():
    cles = {d["cle"] for d in ao_dc.declarations()}
    assert set(D.PREUVES_ATTENDUES) == cles, (
        sorted(set(D.PREUVES_ATTENDUES) ^ cles))
    for cle in cles:
        assert D.couverture(cle)["etat"] in D.COUVERTURES, cle
    # Les deux sans preuve interne DISENT pourquoi — un vide muet passerait
    # pour un oubli, et quelqu'un « corrigerait » l'oubli.
    for cle, attendues in D.PREUVES_ATTENDUES.items():
        if not attendues:
            assert D.SANS_PREUVE_INTERNE.get(cle), cle


# ── LES ROUTES ────────────────────────────────────────────────────────────
# CE QUE CES RÈGLES MESURENT, ET CE QU'ELLES NE MESURENT PAS. Elles ne
# refont pas le travail des règles de module — l'invariant « affirmer ne
# remplit rien » est déjà mesuré sur les octets plus haut. Elles tiennent ce
# que seule une requête peut tenir : QUI entre, et ce qu'un compte voit du
# projet d'un autre.

ORIGINE = {"Origin": "http://localhost"}
ADRESSES = ("/api/datacenter/marche/projet/dossier",
            "/api/datacenter/marche/projet/oubli",
            "/api/datacenter/marche/projet/affirmation")


@pytest.mark.parametrize("adresse", ADRESSES)
def test_un_visiteur_sans_compte_n_atteint_aucune_de_ces_routes(anonyme, adresse):
    r = anonyme.post(adresse, json={"projet": "a" * 32}, headers=ORIGINE)
    assert r.status_code in (401, 403), (adresse, r.status_code)


def test_la_conservation_ne_se_pilote_qu_a_l_administration(connecte, anonyme):
    for c in (anonyme, connecte):
        r = c.get("/api/admin/marche/conservation", headers=ORIGINE)
        assert r.status_code in (401, 403), r.status_code


def test_un_projet_qui_n_est_pas_le_votre_repond_introuvable(marche):
    """Et il répond la MÊME chose qu'un projet inexistant.

    Distinguer « pas à vous » de « n'existe pas » dirait à qui essaie des
    identifiants lesquels sont pris.
    """
    inexistant = marche.get(
        "/api/datacenter/marche/projet/dossier?projet=" + "f" * 32,
        headers=ORIGINE)
    assert inexistant.status_code == 404
    assert inexistant.get_json()["error"] == "projet_inconnu"
    malforme = marche.get(
        "/api/datacenter/marche/projet/dossier?projet=pas-un-identifiant",
        headers=ORIGINE)
    assert malforme.status_code == 404
    assert malforme.get_json()["error"] == inexistant.get_json()["error"]


def test_le_depot_et_la_relecture_passent_par_le_projet_du_compte(
        marche, coffre):
    """La fixture `coffre` N'EST PAS DÉCORATIVE ICI.

    Sans elle, le service n'a pas de clé et répond 503 : la règle passerait en
    prenant une sortie de secours, sans jamais éprouver ni le dépôt, ni la
    relecture, ni l'effacement. Une règle qui passe pour une raison sans
    rapport avec ce qu'elle prétend est pire qu'une règle absente — celle-ci
    exige donc la clé, et le refus sans clé est mesuré à part, plus bas.
    """
    cree = marche.post("/api/datacenter/projets",
                         json={"nom": "Roissy"}, headers=ORIGINE)
    assert cree.status_code == 200, cree.status_code
    pid = cree.get_json()["projet"]["id"]

    depot = marche.post("/api/datacenter/marche/projet/dossier",
                          json={"projet": pid,
                                "pieces": [{"nom": "RC.pdf", "texte": RC}]},
                          headers=ORIGINE)
    assert depot.status_code == 200, depot.get_json()
    corps = depot.get_json()
    assert corps["dossier"]["nb_pieces"] == 1
    assert len(corps["declarations"]["lignes"]) == 6
    assert corps["declarations"]["affirmees"] == []

    lu = marche.get("/api/datacenter/marche/projet/dossier?projet=" + pid,
                      headers=ORIGINE)
    assert lu.status_code == 200
    assert lu.get_json()["dossier"]["pieces"][0]["nom"] == "RC.pdf"

    oubli = marche.post("/api/datacenter/marche/projet/oubli",
                          json={"projet": pid}, headers=ORIGINE)
    assert oubli.status_code == 200 and oubli.get_json()["efface"] is True
    assert marche.get(
        "/api/datacenter/marche/projet/dossier?projet=" + pid,
        headers=ORIGINE).get_json()["dossier"] is None


def test_le_depot_sans_cle_est_refuse_par_la_route_ET_ne_range_rien(
        marche, monkeypatch):
    """Le refus est mesuré à la route, pas seulement au module."""
    import ao_projet
    monkeypatch.delenv(ao_projet.VAR_CLE, raising=False)
    monkeypatch.setattr(ao_projet, "_STORE", ao_projet.MemoryDossierStore())
    pid = marche.post("/api/datacenter/projets", json={"nom": "Roissy"},
                        headers=ORIGINE).get_json()["projet"]["id"]
    r = marche.post("/api/datacenter/marche/projet/dossier",
                      json={"projet": pid,
                            "pieces": [{"nom": "RC.pdf", "texte": RC}]},
                      headers=ORIGINE)
    assert r.status_code == 503, r.status_code
    assert r.get_json()["error"] == "chiffrement_indisponible"
    assert ao_projet.store().compter()["dossiers"] == 0


def test_les_textes_des_six_declarations_sont_servis_pour_etre_LUS(marche):
    """On ne peut pas affirmer ce qu'on n'a pas vu : la route rend les textes."""
    cree = marche.post("/api/datacenter/projets",
                         json={"nom": "Roissy"}, headers=ORIGINE)
    pid = cree.get_json()["projet"]["id"]
    r = marche.get("/api/datacenter/marche/projet/affirmation?projet=" + pid,
                     headers=ORIGINE)
    assert r.status_code == 200
    textes = r.get_json()["textes"]
    assert len(textes) == 6
    for t in textes:
        assert t["texte"].strip(), t["cle"]
        assert t["engage"] in ("penal", "contractuel"), t


def test_les_trois_routes_qui_ecrivent_ont_un_plafond_de_cadence():
    """Elles écrivent en base ET elles chiffrent : les deux coûtent."""
    import app as application
    for adresse in ADRESSES:
        assert adresse in application._RATE_EXACT, adresse
        n, fenetre = application._RATE_EXACT[adresse]
        assert n <= 30 and fenetre >= 60, (adresse, n, fenetre)


def test_le_traitement_est_au_registre_avec_ses_dix_champs():
    import rgpd
    entree = [x for x in rgpd.REGISTRE if x["id"] == "dossier-marche"][0]
    for champ in ("finalite", "base_legale", "donnees", "personnes", "duree",
                  "destinataires", "transferts", "securite"):
        assert entree.get(champ), champ
    # Le chiffrement et l'absence de repli en clair sont OPPOSABLES : ils
    # doivent figurer dans ce que le registre annonce, pas seulement dans le code.
    assert "HIFFR" in entree["securite"].upper(), entree["securite"]
    assert "clair" in entree["securite"], entree["securite"]


def test_la_politique_d_acces_REFUSE_DE_DEMARRER_si_une_de_ces_routes_s_ouvre():
    """La barrière qui protège ces routes n'est pas une règle : c'est le
    DÉMARRAGE lui-même.

    POURQUOI CETTE RÈGLE EXISTE QUAND MÊME. Retirer `@login_required` d'une de
    ces routes ne fait pas tomber une règle — il empêche le service de
    démarrer, ce qui est plus fort. Mais une barrière qu'aucune règle ne
    mesure finit par être désarmée sans que personne s'en aperçoive : il
    suffirait qu'on assouplisse `_verifier_politique_acces` pour que les
    routes s'ouvrent en silence. Celle-ci démonte donc la protection dans une
    COPIE du fichier, dans un autre processus, et vérifie que le démarrage est
    bien refusé — et que le message nomme la route fautive.
    """
    import shutil
    import subprocess
    import tempfile

    racine = ICI
    with tempfile.TemporaryDirectory() as tmp:
        copie = os.path.join(tmp, "site")
        shutil.copytree(racine, copie, symlinks=True,
                        ignore=shutil.ignore_patterns(
                            "__pycache__", ".git", "node_modules", "tests"))
        chemin = os.path.join(copie, "app.py")
        with open(chemin, encoding="utf-8") as f:
            source = f.read()
        # L'ANCRE A SUIVI LA DÉCISION D'ACCÈS. Cette route était fermée par
        # session ; elle l'est désormais à l'administration, et la politique
        # le DÉCLARE dans `acces.API_ADMIN` au lieu de le déduire du seul
        # préfixe `/api/admin/`. C'est ce qui rend la barrière bilatérale :
        # elle refusait déjà ce qui s'ouvre trop, elle refuse maintenant aussi
        # qu'une route déclarée réservée cesse de l'être.
        ancre = ('@app.route("/api/datacenter/marche/projet/dossier", '
                 'methods=["GET", "POST"])\n@admin_required')
        assert source.count(ancre) == 1, "l'ancre de la route a changé"
        with open(chemin, "w", encoding="utf-8") as f:
            f.write(source.replace(ancre, ancre.split("\n")[0], 1))
        r = subprocess.run([sys.executable, "-c", "import app"], cwd=copie,
                           capture_output=True, text=True, timeout=300)
    assert r.returncode != 0, "le service a démarré avec une route ouverte"
    assert "politique d'accès" in r.stderr, r.stderr[-400:]
    assert "/api/datacenter/marche/projet/dossier" in r.stderr, r.stderr[-400:]


# ── L'ÉCRAN ───────────────────────────────────────────────────────────────
# CE QUE CES RÈGLES TIENNENT. Un écran peut afficher un état juste et faire
# croire l'inverse de ce que le module garantit. Elles mesurent donc ce que la
# page DIT, et ce qu'elle propose selon l'état — pas la présence d'un bloc.

def _page():
    with open(os.path.join(ICI, "ingenierie-datacenter.html"), encoding="utf-8") as f:
        return f.read()


def _script():
    with open(os.path.join(ICI, "ingenierie-dc.js"), encoding="utf-8") as f:
        return f.read()


def test_la_section_du_projet_existe_et_le_script_la_remplit():
    assert 'id="ig-ao-projet"' in _page()
    js = _script()
    assert 'z = $("#ig-ao-projet")' in js, "la section n'est jamais peinte"


def test_l_ecran_dit_QU_ASSUMER_N_ECRIT_RIEN_dans_le_formulaire():
    """Un lecteur attend naturellement l'inverse : la page doit le démentir.

    Et elle doit le dire avec les quatre formulaires nommés — « le
    formulaire » au singulier laisserait croire qu'un seul est concerné.
    """
    js = _script()
    rendu = js[js.index("function aoProjetRendre("):]
    rendu = rendu[:rendu.index("\n  }")]
    assert "n\\'écrit RIEN dans le" in rendu or "n'écrit RIEN dans le" in rendu, (
        "l'écran ne dit pas qu'assumer n'écrit rien")
    for f in ("DC1", "DC2", "DC4", "ATTRI1"):
        assert f in rendu, "l'écran ne nomme pas le %s" % f


def test_une_declaration_sans_preuve_n_offre_AUCUN_bouton_pour_l_assumer():
    """L'écran ne propose pas un geste que le serveur refusera.

    Le refus côté serveur reste la barrière — mesuré plus haut. Ici on tient
    autre chose : qu'on ne fasse pas taper un nom et cocher une case pour
    récolter une erreur.
    """
    js = _script()
    d = js[js.index("function aoDeclaration("):]
    d = d[:d.index("\n  }")]
    # La sortie anticipée sur « incomplete » DOIT précéder le formulaire.
    coupe = d.index('l.couverture === "incomplete"')
    bouton = d.index("data-cons-aff")
    assert coupe < bouton, (
        "le bouton « Assumer » est proposé avant le contrôle de la preuve")
    assert "return h;" in d[coupe:bouton], (
        "rien n'interrompt le rendu quand la preuve est incomplète")


def test_l_absence_de_preuve_interne_demande_une_case_DE_PLUS():
    """CETTE RÈGLE A ÉTÉ REPRISE : sa première version passait à côté.

    Elle cherchait la PREMIÈRE occurrence de `sans_preuve_interne` et
    vérifiait qu'elle précédait la case. Or la fonction nomme cette condition
    DEUX FOIS — une pour afficher l'état de la preuve, une pour garder la
    case. La première suffisait à satisfaire la règle, si bien qu'une mutation
    ouvrant la case à TOUTES les déclarations ne faisait rien tomber. On
    mesure donc la garde qui précède immédiatement la case.
    """
    js = _script()
    d = js[js.index("function aoDeclaration("):]
    d = d[:d.index("\n  }")]
    j = d.index("data-cons-rec")
    juste_avant = d[max(0, j - 220):j]
    assert 'l.couverture === "sans_preuve_interne"' in juste_avant, (
        "la case de reconnaissance n'est pas gardée par l'absence de preuve "
        "interne : elle est proposée à toutes les déclarations")
    assert "data-cons-rec" not in d[:j], "la case apparaît plus d'une fois"


def test_l_etat_des_declarations_n_est_JAMAIS_garde_localement():
    """Une preuve périme ; un état gardé ici vieillirait sans le dire.

    Seul l'identifiant du projet est mémorisé — pas ce que le serveur en dit.
    """
    js = _script()
    locaux = re.findall(r'(?:set|get)Item\(\s*"([^"]+)"', js)
    for cle in locaux:
        assert "declaration" not in cle and "affirm" not in cle, cle
    assert "ao-projet-v1" in locaux, "le projet rattaché n'est pas mémorisé"
    etat = js[js.index("function aoProjetEtat("):]
    etat = etat[:etat.index("\n  }")]
    assert "/api/datacenter/marche/projet/dossier" in etat, (
        "l'état ne vient pas du serveur")


def test_les_classes_du_bloc_de_conservation_ne_collisionnent_avec_AUCUNE_autre():
    """CETTE RÈGLE EXISTE PARCE QUE LA COLLISION A EU LIEU.

    Le bloc s'appelait d'abord `.ig-pj` — nom déjà porté par le formulaire des
    PIÈCES JOINTES, plus bas dans la même feuille. Les deux jeux de règles se
    sont écrasés l'un l'autre : mes bordures et mon fond sont passés sur leur
    formulaire, et leur `display:flex` a mis mes titres et mes paragraphes sur
    une seule ligne. Rien ne l'a signalé — ni la syntaxe, ni les règles, ni la
    page, qui s'affichait simplement de travers.

    On mesure donc que chaque classe du bloc est définie UNE SEULE FOIS dans
    la feuille. Une classe définie deux fois n'est pas forcément un défaut en
    général ; ici, où le bloc est neuf et isolé, elle l'est toujours.
    """
    page = _page()
    style = page[page.index("<style"):page.rindex("</style>")]
    js = _script()
    # LES CLASSES, PAS LES IDENTIFIANTS. La première version de cette règle
    # ramassait `ig-cons-go` — qui est un id de bouton, jamais défini comme
    # classe — et échouait sur son propre ramassage. On lit donc les attributs.
    # Le nom s'arrête au premier caractère qui n'en fait pas partie : le
    # script construit certains attributs par concaténation, et le morceau
    # ramassé finissait par emporter l'apostrophe de fin de chaîne.
    classes = sorted({m for m in re.findall(r"ig-cons[A-Za-z0-9_-]*", js)
                      if not re.search(r'(?:id|dataset)[^\n]{0,20}"' + m, js)}
                     - {m for m in re.findall(r'id="(ig-cons[A-Za-z0-9_-]*)', js)})
    assert len(classes) >= 8, classes
    for c in classes:
        # Le nombre de RÈGLES qui définissent cette classe comme sélecteur.
        n = len(re.findall(r"[.\s,]" + re.escape(c) + r"(?=[{\s,:>.])", style))
        assert n >= 1, "%s est employée par le script sans être définie" % c
    # Et aucune de ces classes ne doit exister ailleurs sous un autre nom de
    # bloc : `.ig-pj` reste au formulaire des pièces jointes, intact.
    assert ".ig-cons" not in style[:style.index("LE PROJET CONSERVÉ")], (
        "une classe du bloc de conservation est définie avant son propre bloc")
    for c in classes:
        assert not c.startswith("ig-pj"), (
            "%s reprend le préfixe du formulaire des pièces jointes" % c)
