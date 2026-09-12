# -*- coding: utf-8 -*-
"""Le SIRET tranché, et les trois chiffres d'affaires sourcés.

CE QUE L'ARITHMÉTIQUE NE POUVAIT PAS FAIRE. Deux SIRET circulaient pour ce
cabinet — « 494 530 157 00036 » et « 494 530 157 00010 ». Les DEUX commencent
par le bon SIREN et les DEUX passent la clé de Luhn : le calcul ne pouvait pas
départager. Seul le gérant le pouvait, et il l'a fait le 12/09/2026. La clé
reste vérifiée à l'import, mais pour ce qu'elle est — un garde-fou de frappe,
pas une vérification d'identité.

POURQUOI LES MONTANTS PORTENT LEUR SOURCE. Le DC2 demande le chiffre
d'affaires global des trois derniers exercices, et l'acheteur peut le
confronter à la liasse. Les trois montants retenus sont ceux qu'établissent
les comptes annuels : 7 496 € (attestation BDO Rennes, exercice clos le
31/12/2025), 21 800 € (attestation BDO, exercice clos le 31/12/2024) et
79 328 € (colonne 31/12/2023 du compte de résultat 2024, corroborée par les
soldes intermédiaires de gestion du même document).

POURQUOI LE RANG SE CALCULE. Écrire « ca_n1 = … » figerait le rang : au jour
de la clôture 2026, il faudrait décaler trois valeurs à la main, et rien ne
dirait qu'on a oublié. Les exercices sont donc une liste datée, et n1/n2/n3
en sont le rang — sans jamais lire l'horloge, pour que deux appels le même
jour rendent la même fiche.

MESURE : l'identité passe de 12 à 16 champs sur 22, et les quatre formulaires
de l'État de 7 à 13 valeurs posées.
"""
import re

import pytest

import ao_dc
import ao_formulaires
import dossier_entreprise as D


RC = """RÈGLEMENT DE LA CONSULTATION
Pouvoir adjudicateur : COMMUNAUTÉ D'AGGLOMÉRATION DE VAL-D'EUROPE
Objet du marché : construction d'un centre de données de 12 MW — lot 2, CVC.
Référence de la consultation : 2026-DC-0142
"""

QUATRE = (("dc1", "dc1"), ("dc2", "dc2"), ("dc4", "dc4"),
          ("attri1", "acte_engagement"))


@pytest.fixture(scope="module")
def analyse():
    return ao_dc.analyser([{"nom": "RC.txt", "texte": RC}])


def _poser(fiche, analyse):
    r = ao_dc.remplir(fiche=fiche, analyse=analyse)
    total, detail = 0, {}
    for modele, cle in QUATRE:
        _, rap = ao_formulaires.remplir_document(
            modele, ao_formulaires.valeurs_pour(r, cle))
        detail[modele] = [p["rubrique"] for p in rap["places"]]
        total += len(rap["places"])
    return total, detail


# ═══════════════════════════════════════════════════════════════════════════
#  1. LE SIRET
# ═══════════════════════════════════════════════════════════════════════════

def test_le_siret_porte_le_siren_et_passe_sa_cle():
    """Une faute de frappe sur quatorze chiffres ne se voit pas à l'œil."""
    siren = re.sub(r"\D", "", D.IDENTITE["siren"])
    siret = re.sub(r"\D", "", D.IDENTITE["siret"])
    assert len(siret) == 14, siret
    assert siret.startswith(siren), (siret, siren)
    assert D._luhn(siret), "clé de contrôle fausse : %s" % siret


def test_un_siret_incoherent_empeche_le_module_de_demarrer():
    """LE TÉMOIN NÉGATIF DE LA GARDE. Sans lui, `_verifier_identite` pourrait
    ne rien vérifier du tout et la règle ci-dessus resterait verte."""
    vrai = D.IDENTITE["siret"]
    for faux in ("494 530 157 00037",      # clé fausse
                 "123 456 789 00014",      # autre SIREN
                 "494 530 157 0003"):      # treize chiffres
        D.IDENTITE["siret"] = faux
        try:
            with pytest.raises(AssertionError):
                D._verifier_identite()
        finally:
            D.IDENTITE["siret"] = vrai
    D._verifier_identite()          # la vraie valeur passe


def test_la_garde_passe_VRAIMENT_a_l_import_et_pas_seulement_quand_on_l_appelle():
    """LA DIFFÉRENCE ENTRE UNE GARDE ET UNE FONCTION QUI EXISTE.

    La règle précédente appelle `_verifier_identite()` à la main : elle reste
    verte même si plus personne ne l'appelle au chargement. Mesuré — la
    mutation qui remplace l'appel final par `pass` y survivait. Un module qui
    démarre avec un SIRET faux envoie ce SIRET dans un DC1 déposé chez un
    acheteur, et aucune suite de tests ne tourne à ce moment-là.

    ELLE RÉEXÉCUTE LE FICHIER, avec un SIRET cassé injecté dans la source. Si
    la garde est branchée, l'exécution lève ; si elle a été débranchée, le
    module se charge tranquillement et la règle tombe.
    """
    source = open(D.__file__, encoding="utf-8").read()
    casse = source.replace('"siret": "494 530 157 00036",',
                           '"siret": "494 530 157 00037",')
    assert casse != source, (
        "l'ancre du SIRET a changé : cette règle ne teste plus rien")

    def _charger(texte):
        # `__file__` est fourni : le module s'en sert pour situer ses documents
        # d'origine, et son absence lèverait pour une raison sans rapport.
        espace = {"__name__": "_essai_dossier", "__file__": D.__file__}
        exec(compile(texte, D.__file__, "exec"), espace)

    with pytest.raises(AssertionError):
        _charger(casse)
    # LE TÉMOIN : la source INTACTE se charge sans lever. Sans lui, une règle
    # qui lèverait pour n'importe quelle raison passerait aussi.
    _charger(source)


def test_la_cle_de_luhn_ne_departage_PAS_les_deux_siret_qui_circulaient():
    """CE QUI JUSTIFIE D'AVOIR DEMANDÉ PLUTÔT QUE CALCULÉ.

    Si cette règle tombait — si l'un des deux échouait à la clé —, il aurait
    fallu trancher par le calcul et non par une déclaration. Elle constate
    que ce n'était pas possible, et c'est ce qui rend la question légitime.
    """
    assert D._luhn("49453015700036")
    assert D._luhn("49453015700010")


def test_le_siret_atteint_les_formulaires_qui_lui_ouvrent_une_case(analyse):
    """Détenir ne suffit pas : c'est le défaut qui tenait le SIREN prisonnier."""
    fiche = D.fiche_candidat()["fiche"]
    _, detail = _poser(fiche, analyse)
    porteurs = [f for f, cles in detail.items() if "siret" in cles]
    ouvrants = [m for m, _ in QUATRE
                if "siret" in {a["rubrique"] for a in ao_formulaires.ANCRES[m]}]
    assert ouvrants, "plus aucun formulaire n'ouvre de case SIRET"
    assert sorted(porteurs) == sorted(ouvrants), (porteurs, ouvrants)


# ═══════════════════════════════════════════════════════════════════════════
#  2. LES TROIS EXERCICES
# ═══════════════════════════════════════════════════════════════════════════

def test_chaque_montant_porte_la_source_qui_l_etablit():
    """Un chiffre d'affaires sans source ne se vérifie pas — et il part dans
    une déclaration que l'acheteur PEUT confronter à la liasse."""
    for x in D.EXERCICES:
        assert str(x.get("source") or "").strip(), x
        assert len(x["source"]) > 20, ("source trop courte pour désigner un "
                                       "document : %r" % x)
        assert str(x["annee"]) in x["source"] or "31/12/%s" % x["annee"] in x["source"], (
            "la source de l'exercice %s ne dit pas de quel exercice elle "
            "parle : %r" % (x["annee"], x["source"]))


def test_les_rangs_suivent_les_annees_et_non_l_ordre_d_ecriture():
    """LA RÈGLE DÉCISIVE DU RANG. Elle mélange délibérément l'ordre : si
    n1/n2/n3 étaient recopiés, ils suivraient la liste au lieu des dates."""
    melange = [{"annee": 2023, "ca": "79 328 €", "source": "s"},
               {"annee": 2025, "ca": "7 496 €", "source": "s"},
               {"annee": 2024, "ca": "21 800 €", "source": "s"}]
    r = D._rangs_exercices(melange)
    assert r == {"ca_n1": "7 496 €", "ca_n2": "21 800 €",
                 "ca_n3": "79 328 €"}, r


def test_un_exercice_neuf_decale_les_trois_rangs_sans_retouche():
    """CE QUE LE CALCUL DU RANG ACHÈTE. À la clôture 2026, une ligne s'ajoute
    et les trois rangs suivent seuls — c'est le geste qu'on aurait oublié."""
    avant = D._rangs_exercices(D.EXERCICES)
    apres = D._rangs_exercices(
        ({"annee": 2026, "ca": "42 000 €", "source": "s"},) + tuple(D.EXERCICES))
    assert apres["ca_n1"] == "42 000 €"
    assert apres["ca_n2"] == avant["ca_n1"]
    assert apres["ca_n3"] == avant["ca_n2"]
    assert "79 328 €" not in apres.values(), (
        "le quatrième exercice reste déclaré : le DC2 n'en demande que trois")


def test_moins_de_trois_exercices_laissent_le_rang_MANQUANT():
    """ELLE NE COMPLÈTE PAS. Recopier le montant précédent pour boucher le
    troisième rang ferait déclarer un chiffre d'affaires qui n'existe pas."""
    r = D._rangs_exercices([{"annee": 2025, "ca": "7 496 €", "source": "s"}])
    assert r == {"ca_n1": "7 496 €"}, r
    ident = dict(D.IDENTITE, exercices=({"annee": 2025, "ca": "7 496 €",
                                         "source": "s"},))
    etat = D.fiche_candidat(ident)
    manquants = {m["cle"] for m in etat["manques"]}
    assert {"ca_n2", "ca_n3"} <= manquants, manquants
    assert etat["fiche"]["ca_n1"] == "7 496 €"
    for m in etat["manques"]:
        if m["cle"] in ("ca_n2", "ca_n3"):
            assert m["ou_trouver"], m


def test_un_exercice_sans_montant_ne_prend_pas_de_rang():
    """Une année déclarée sans chiffre décalerait les rangs suivants si on la
    comptait — et ferait passer le CA de N-1 pour celui de N."""
    r = D._rangs_exercices([{"annee": 2025, "ca": "", "source": "s"},
                            {"annee": 2024, "ca": "21 800 €", "source": "s"}])
    assert r == {"ca_n1": "21 800 €"}, r


def test_les_annees_doivent_etre_distinctes_et_decroissantes():
    """LE TÉMOIN NÉGATIF DE LA GARDE SUR LES EXERCICES."""
    vrai = D.EXERCICES
    for faux in (({"annee": 2024, "ca": "1 €", "source": "aaaaaaaaaaaaaaaaaaaaa 2024"},
                  {"annee": 2025, "ca": "2 €", "source": "aaaaaaaaaaaaaaaaaaaaa 2025"}),
                 ({"annee": 2025, "ca": "1 €", "source": "aaaaaaaaaaaaaaaaaaaaa 2025"},
                  {"annee": 2025, "ca": "2 €", "source": "aaaaaaaaaaaaaaaaaaaaa 2025"})):
        D.EXERCICES = faux
        try:
            with pytest.raises(AssertionError):
                D._verifier_identite()
        finally:
            D.EXERCICES = vrai
    D._verifier_identite()


def test_un_montant_sans_source_empeche_le_module_de_demarrer():
    vrai = D.EXERCICES
    D.EXERCICES = ({"annee": 2025, "ca": "7 496 €", "source": ""},)
    try:
        with pytest.raises(AssertionError):
            D._verifier_identite()
    finally:
        D.EXERCICES = vrai
    D._verifier_identite()


# ═══════════════════════════════════════════════════════════════════════════
#  3. CE QUE TOUT CELA POSE SUR LE PAPIER
# ═══════════════════════════════════════════════════════════════════════════

def test_les_trois_chiffres_d_affaires_arrivent_sur_le_DC2(analyse):
    fiche = D.fiche_candidat()["fiche"]
    _, detail = _poser(fiche, analyse)
    assert {"ca_n1", "ca_n2", "ca_n3"} <= set(detail["dc2"]), detail["dc2"]


def test_l_apport_du_siret_et_des_exercices_se_chiffre(analyse):
    """LA MESURE QUI JUSTIFIE CE TOUR, prise contre le dossier d'AVANT."""
    avant_id = dict(D.IDENTITE, siret=None)
    avant_id.pop("exercices", None)
    avant, det_a = _poser(D.fiche_candidat(avant_id)["fiche"], analyse)
    apres, det_b = _poser(D.fiche_candidat()["fiche"], analyse)
    assert apres - avant >= 6, (
        "porter le SIRET et les trois exercices ne rapporte que %d case(s) "
        "— %r" % (apres - avant, det_b))
    # ELLE N'ÉNUMÈRE PAS LES CASES GAGNÉES À LA MAIN. La première version
    # attendait quatre noms et en a trouvé cinq : l'acte d'engagement ouvre
    # aussi un « titulaire_siret », que je n'avais pas prévu. La règle avait
    # tort, pas le programme. Ce qui se mesure : chaque case gagnée vient d'un
    # des quatre champs ajoutés, et aucune ne vient d'ailleurs.
    ajoutes = ("siret", "ca_n1", "ca_n2", "ca_n3")
    gagnees = {c for f in det_a for c in set(det_b[f]) - set(det_a[f])}
    assert gagnees, "porter le SIRET et les exercices ne gagne aucune case"
    etrangeres = [c for c in gagnees
                  if not any(c == x or c.endswith("_" + x) for x in ajoutes)]
    assert not etrangeres, (
        "ces cases se remplissent sans rapport avec ce qui a été porté : %s"
        % sorted(etrangeres))
    assert {"ca_n1", "ca_n2", "ca_n3"} <= gagnees, sorted(gagnees)
    assert any(c == "siret" or c.endswith("_siret") for c in gagnees), sorted(gagnees)


def test_deux_appels_le_meme_jour_rendent_la_meme_fiche():
    """ELLE NE LIT PAS L'HORLOGE. Un `datetime.now()` dans le calcul du rang
    ferait rendre une fiche différente selon le jour où on la demande."""
    assert D.fiche_candidat() == D.fiche_candidat()

    # ELLE EXÉCUTE, ELLE NE LIT PAS LE TEXTE. La première version cherchait
    # « now( » dans le source de la fonction — et tombait sur sa PROPRE
    # docstring, qui explique pourquoi l'horloge est interdite. Une règle qui
    # constate un motif syntaxique se trompe de cible dans les deux sens :
    # elle attrape un commentaire, et laisserait passer `dt.date.today()`.
    #
    # ICI L'HORLOGE EST PIÉGÉE : si quoi que ce soit dans la chaîne la
    # consulte, l'appel lève au lieu de rendre une fiche.
    class _HorlogeInterdite(object):
        def __getattr__(self, nom):
            raise AssertionError(
                "le calcul de la fiche a consulté l'horloge (datetime.%s) : "
                "deux appels à des jours différents rendraient des documents "
                "différents" % nom)

    vrai = D.datetime
    D.datetime = _HorlogeInterdite()
    try:
        D._rangs_exercices(D.EXERCICES)
        D.fiche_candidat()
    finally:
        D.datetime = vrai


def test_la_correction_explicite_l_emporte_sur_le_rang_calcule():
    """LE RATTRAPAGE. Un exercice clos mais pas encore porté ici doit pouvoir
    être déclaré sans attendre une mise à jour du module."""
    ident = dict(D.IDENTITE, ca_n1="42 000 €")
    f = D.fiche_candidat(ident)["fiche"]
    assert f["ca_n1"] == "42 000 €"
    assert f["ca_n2"] == "21 800 €", (
        "la correction a écrasé les rangs qu'elle ne visait pas : %r" % f)
