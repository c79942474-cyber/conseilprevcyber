"""Le dossier marché du client, et la réponse — ce qui est cité, ce qui est tu.

CE QUI EST ÉPROUVÉ. Les propriétés qui font qu'une analyse de dossier de
consultation est honnête, et qu'un dossier de candidature est complet :

  · une pièce NON RECONNUE reste non reconnue — la ranger au plus proche
    ferait chercher des pénalités dans un CCTP, et conclure qu'il n'y en a
    pas ;
  · ce qui n'est pas trouvé est DÉCLARÉ non trouvé, jamais supposé absent ;
  · toute citation porte sa position, pour être vérifiée sur la pièce ;
  · l'absence d'une pièce essentielle est une ALERTE, pas une ligne de plus ;
  · les formulaires de candidature ne se génèrent pas, et le module le dit.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc as A  # noqa: E402


RC = """RÈGLEMENT DE LA CONSULTATION
Référence : 2026-014-DC
La date et heure limites de réception des offres sont fixées au 12 septembre
2026 à 12 h 00 sur la plateforme de dématérialisation.
Critères de jugement : valeur technique 60 %, prix des prestations 40 %.
Le groupement conjoint avec mandataire solidaire est imposé.
La visite du site est obligatoire ; une attestation de visite sera jointe.
Les variantes ne sont pas autorisées.
"""

CCAP = """CAHIER DES CLAUSES ADMINISTRATIVES PARTICULIÈRES
Article 3 - Ordre de priorité des pièces contractuelles : acte d'engagement,
CCAP, CCTP, annexes.
Article 9 - Pénalités de retard : 1/1000 du montant par jour calendaire.
Article 14 - Il est dérogé à l'article 13 du CCAG-MOE.
Assurance responsabilité civile professionnelle exigée pendant l'exécution.
"""

CCTP = """CAHIER DES CLAUSES TECHNIQUES PARTICULIÈRES
Le PUE annuel engagé est de 1,25 au taux de charge nominal.
Le niveau de disponibilité visé correspond au Tier III.
"""


def _dossier(*pieces):
    return A.analyser([{"nom": n, "texte": t} for n, t in pieces])


# ── L'identification, et son honnêteté ─────────────────────────────────────

def test_une_piece_est_identifiee_sur_son_nom_et_son_contenu():
    i = A.identifier("02_CCAP_lot_unique.pdf", CCAP)
    assert i["code"] == "ccap"
    assert i["confiance"] == "forte"
    assert i["indices"]


def test_une_piece_non_reconnue_reste_non_reconnue():
    """LE DÉFAUT QUE CETTE RÈGLE EMPÊCHE. Ranger au plus proche ferait chercher
    des pénalités dans un CCTP pris pour un CCAP — et conclure qu'il n'y en a
    pas, ce qui est la pire des réponses."""
    i = A.identifier("divers.pdf", "un texte quelconque sans marqueur")
    assert i["reconnue"] is False
    assert i["code"] is None
    assert "au plus proche" in i["pourquoi"]


def test_l_identification_porte_toujours_ses_indices():
    """Un classement qu'on ne peut pas contester est un classement qu'on croit
    sur parole — et cette fonction se trompera un jour."""
    for nom, texte in (("RC.pdf", RC), ("CCAP.pdf", CCAP), ("CCTP.pdf", CCTP)):
        i = A.identifier(nom, texte)
        assert i["indices"], nom


def test_une_identification_douteuse_propose_les_autres_pistes():
    """Une confiance faible sans alternative laisse le lecteur devant un
    verdict qu'il ne sait pas corriger."""
    i = A.identifier("annexe.xlsx", "", ".xlsx")
    assert i["confiance"] == "faible"
    assert i["code"] == "calculs"


def test_un_tableur_sans_marqueur_est_range_par_son_extension_a_confiance_faible():
    i = A.identifier("bilan.xlsx", "", ".xlsx")
    assert i["reconnue"] and i["confiance"] == "faible"


# ── Les relevés : des citations, pas des interprétations ───────────────────

def test_la_date_limite_est_rendue_en_citation_avec_sa_position():
    """« Remise avant le 12/09/2026 à 12 h 00 » se vérifie ; « délai de
    remise : 12 septembre » a déjà perdu l'heure, et l'heure fait perdre des
    consultations."""
    a = _dossier(("RC.pdf", RC))
    r = [x for x in a["pieces"][0]["releves"] if x["cle"] == "date_limite"][0]
    assert r["trouve"]
    c = r["citations"][0]
    assert "12 h 00" in c["texte"] or "12 septembre" in c["texte"]
    assert isinstance(c["position"], int)
    assert 0 <= c["part"] <= 100


def test_ce_qui_n_est_pas_trouve_est_declare_non_trouve():
    """Jamais supposé absent : « non trouvé » veut dire « allez le lire
    vous-même », et c'est la seule réponse honnête."""
    a = _dossier(("RC.pdf", "RÈGLEMENT DE LA CONSULTATION\nRien d'autre."))
    manquants = [x for x in a["pieces"][0]["releves"] if not x["trouve"]]
    assert manquants
    for x in manquants:
        # La note est vérifiée comme TEXTE avant d'être fouillée : vidée, elle
        # ferait échouer cette règle sur un TypeError obscur au lieu de dire
        # ce qui manque.
        assert isinstance(x["note"], str) and x["note"].strip(), x["cle"]
        assert "n'a pas vu" in x["note"] or "non trouvé" in x["note"].lower()
        assert not x["citations"]


def test_les_criteres_et_leur_ponderation_sont_releves():
    """La pondération dit où placer l'effort : un mémoire technique à 60 % ne
    se rédige pas comme un mémoire à 20 %."""
    a = _dossier(("RC.pdf", RC))
    r = [x for x in a["pieces"][0]["releves"] if x["cle"] == "criteres"][0]
    assert r["trouve"]
    assert "60" in " ".join(c["texte"] for c in r["citations"])


def test_les_derogations_au_ccag_sont_relevees():
    """C'est là que le risque se déplace vers le titulaire, souvent en trois
    lignes à la fin du document."""
    a = _dossier(("CCAP.pdf", CCAP))
    r = [x for x in a["pieces"][0]["releves"] if x["cle"] == "derogations"][0]
    assert r["trouve"]


def test_les_performances_engagees_du_cctp_sont_relevees():
    """Un PUE engagé sans méthode de preuve est une clause invérifiable — pour
    le titulaire d'abord, à qui il reviendra de démontrer qu'il l'a tenu."""
    a = _dossier(("CCTP.pdf", CCTP))
    r = [x for x in a["pieces"][0]["releves"] if x["cle"] == "performances"][0]
    assert r["trouve"]


def test_chaque_releve_porte_son_piege_meme_quand_il_ne_trouve_rien():
    """Le piège est ce qui reste utile quand le relevé échoue : il dit quoi
    chercher à la main."""
    a = _dossier(("RC.pdf", "RÈGLEMENT DE LA CONSULTATION"))
    for x in a["pieces"][0]["releves"]:
        assert len(x["piege"]) > 30, x["cle"]


# ── Ce qui manque — l'information la plus utile ────────────────────────────

def test_les_pieces_absentes_du_dossier_sont_nommees():
    """Un dossier sans CCAP ni règlement de consultation n'est pas un dossier,
    et c'est le genre de constat qu'on fait trois jours avant la remise si
    personne ne le fait le premier jour."""
    a = _dossier(("CCTP.pdf", CCTP))
    absents = {m["code"] for m in a["manquantes"]}
    assert {"rc", "ccap", "ae"} <= absents, absents


def test_une_piece_essentielle_absente_leve_une_alerte_bloquante():
    a = _dossier(("CCTP.pdf", CCTP))
    bloquantes = [x for x in a["alertes"] if x["niveau"] == "bloquante"]
    assert bloquantes, a["alertes"]


def test_un_dossier_complet_ne_leve_pas_d_alerte_bloquante_de_piece():
    a = _dossier(("RC.pdf", RC), ("CCAP.pdf", CCAP), ("CCTP.pdf", CCTP),
                 ("AE.pdf", "ACTE D'ENGAGEMENT\nAprès avoir pris connaissance"))
    manquants_essentiels = [m for m in a["manquantes"]
                            if m["gravite"] == "bloquante"]
    assert not manquants_essentiels, manquants_essentiels


def test_les_alertes_sont_rangees_du_plus_grave_au_moins_grave():
    """Ce qui rend l'offre irrecevable d'abord, ce qui coûte cher ensuite."""
    a = _dossier(("CCAP.pdf", CCAP), ("inconnu.pdf", "rien"))
    rang = {"bloquante": 0, "attention": 1, "verifier": 2}
    n = [rang[x["niveau"]] for x in a["alertes"]]
    assert n == sorted(n), [x["niveau"] for x in a["alertes"]]


def test_une_meme_alerte_n_est_dite_qu_une_fois():
    """Deux CCAP déposés lèveraient deux fois l'alerte des pénalités, et le
    lecteur croirait à deux problèmes distincts."""
    a = _dossier(("CCAP1.pdf", CCAP), ("CCAP2.pdf", CCAP))
    textes = [x["texte"] for x in a["alertes"]]
    assert len(textes) == len(set(textes)), textes


def test_un_fichier_inconnu_leve_une_alerte_de_verification():
    a = _dossier(("mystere.pdf", "aucun marqueur ici"))
    assert any("pas été reconnus" in x["texte"] for x in a["alertes"]), a["alertes"]
    assert a["inconnues"]


# ── L'ordre de lecture ─────────────────────────────────────────────────────

def test_les_pieces_sont_rendues_dans_l_ordre_ou_on_les_ouvre():
    """Le règlement de consultation d'abord — il dit quoi remettre et quand.
    Un dossier techniquement parfait remis hors délai ne se lit pas."""
    a = _dossier(("CCTP.pdf", CCTP), ("RC.pdf", RC), ("CCAP.pdf", CCAP))
    rangs = [p["rang_lecture"] for p in a["pieces"]]
    assert rangs == sorted(rangs), [p["sigle"] for p in a["pieces"]]
    assert a["pieces"][0]["code"] == "rc"


def test_deux_pieces_ne_partagent_pas_un_rang_de_lecture():
    rangs = [p["rang_lecture"] for p in A.PIECES_MARCHE.values()]
    assert len(rangs) == len(set(rangs)), rangs


def test_une_piece_sans_texte_le_dit_au_lieu_de_paraitre_analysee():
    """Un plan DWG franchit l'analyse sans porter de texte. Rendre ses relevés
    tous « non trouvés » sans expliquer pourquoi laisserait croire que la
    pièce a été lue."""
    a = A.analyser([{"nom": "plan_masse.dwg", "texte": "",
                     "extension": ".dwg"}])
    assert a["pieces"][0].get("sans_texte")


# ── Le dossier de candidature ──────────────────────────────────────────────

def test_les_quatorze_pieces_de_la_candidature_sont_decrites():
    """La composition demandée par les acheteurs : formulaires, justificatifs
    et notes. En oublier une la fait manquer au dépôt."""
    cles = {p["cle"] for p in A.DOSSIER_CANDIDATURE}
    attendues = {"dc1", "dc2", "pouvoirs", "tiers", "honneur",
                 "repartition_competences", "conventions", "equipe",
                 "organigramme", "cv", "atd_atp", "references", "moyens",
                 "qse"}
    assert attendues <= cles, attendues - cles


def test_l_ordre_de_production_commence_par_ce_qui_a_un_delai():
    """C'est la seule chose qu'on ne rattrape pas la dernière nuit. Suivre
    l'ordre du règlement de consultation ferait commencer par les formulaires,
    qui se remplissent en une heure."""
    pieces = A.plan_reponse()["pieces"]
    natures = [p["nature"] for p in pieces]
    rang = {"justificatif": 0, "note": 1, "formulaire": 2}
    assert [rang[n] for n in natures] == sorted(rang[n] for n in natures), natures


def test_les_pieces_bloquantes_sont_nommees_a_part():
    """Traiter quatorze pièces avec la même urgence revient à n'en traiter
    aucune correctement."""
    p = A.plan_reponse()
    assert p["bloquantes"]
    assert len(p["bloquantes"]) < len(A.DOSSIER_CANDIDATURE)


def test_chaque_piece_dit_ce_qu_elle_contient_et_ce_qui_la_fait_ecarter():
    for p in A.DOSSIER_CANDIDATURE:
        assert p["contient"], p["cle"]
        assert len(p["piege"]) > 40, p["cle"]
        assert p["produit_par"], p["cle"]


def test_le_dc1_couvre_les_sept_rubriques_du_formulaire():
    """Identification, objet, candidature, présentation, groupement,
    engagements, mandataire. Une rubrique passée sous silence est une rubrique
    qu'on découvre en ouvrant l'imprimé."""
    c = " ".join(A.DOSSIER_CANDIDATURE[0]["contient"]).lower()
    assert A.DOSSIER_CANDIDATURE[0]["cle"] == "dc1"
    for mot in ("acheteur", "consultation", "candidature", "groupement",
                "engagements", "mandataire"):
        assert mot in c, mot


def test_le_dc2_couvre_les_trois_capacites_et_l_appui_sur_un_tiers():
    d = [p for p in A.DOSSIER_CANDIDATURE if p["cle"] == "dc2"][0]
    c = " ".join(d["contient"]).lower()
    for mot in ("aptitude", "économique", "technique", "s'appuie"):
        assert mot in c, mot
    assert "engagement" in d["piege"].lower()


def test_la_declaration_sur_l_honneur_cite_les_deux_series_d_interdictions():
    """Obligatoires et facultatives : ce sont deux séries distinctes du code
    de la commande publique, et la seconde s'oublie."""
    d = [p for p in A.DOSSIER_CANDIDATURE if p["cle"] == "honneur"][0]
    c = " ".join(d["contient"])
    assert "L. 2141-1" in c and "L. 2141-5" in c
    assert "L. 2141-7" in c and "L. 2141-11" in c


def test_les_references_exigent_six_operations_et_la_part_propre():
    """Compter une référence de groupement comme une référence propre se voit :
    un évaluateur qui reconnaît l'opération et n'y retrouve pas le candidat
    écarte la référence entière."""
    r = [p for p in A.DOSSIER_CANDIDATURE if p["cle"] == "references"][0]
    c = " ".join(r["contient"]).lower()
    assert "six" in c
    assert "groupement" in c
    assert r["bloquant"] is True


def test_les_pieces_a_delai_sont_signalees_avec_leur_delai():
    """C'est le délai d'obtention, pas la rédaction, qui fait rater les
    dépôts."""
    avec = A.plan_reponse()["avec_delai"]
    assert avec
    for x in avec:
        assert x["delai"] and len(x["delai"]) > 10, x


def test_le_groupement_multiplie_les_pieces_qui_se_produisent_par_membre():
    """L'oubli d'un seul membre rend la candidature incomplète pour tous."""
    p = A.plan_reponse(groupement=True)
    par_cle = {x["cle"]: x for x in p["pieces"]}
    assert "MEMBRE" in par_cle["dc2"]["en_groupement"].upper()
    assert "seul DC1" in par_cle["dc1"]["en_groupement"]


def test_sans_groupement_aucune_piece_ne_porte_de_mention_de_groupement():
    for x in A.plan_reponse(groupement=False)["pieces"]:
        assert "en_groupement" not in x, x["cle"]


# ── Ce que le module refuse de faire ───────────────────────────────────────

def test_le_module_annonce_qu_il_ne_signe_ni_ne_declare_rien():
    """Les formulaires portent des déclarations dont la fausseté est
    sanctionnée. Un générateur qui les remplirait produirait un document
    d'apparence officielle sur des faits que personne n'a vérifiés."""
    note = A.plan_reponse()["note"]
    assert "ne signe rien" in note.lower() or "ne déclare" in note.lower()
    assert "habilitée" in note


def test_le_reglement_de_consultation_l_emporte_sur_cette_liste():
    """La liste des pièces réellement exigées est celle de VOTRE consultation.
    Ne pas le dire ferait remettre un dossier complet au sens de ce module et
    incomplet au sens de l'acheteur."""
    assert "règlement de consultation" in A.plan_reponse()["note"].lower()


def test_l_analyse_annonce_qu_elle_ne_comprend_pas_ce_qu_elle_cite():
    r = A.analyser([{"nom": "RC.pdf", "texte": RC}])["reserve"].lower()
    assert "ne remplace pas la lecture" in r
    assert "ne comprend pas" in r


# ── Le rappel de consultation dans le plan de réponse ──────────────────────

def test_le_plan_reprend_la_date_et_les_criteres_de_l_analyse():
    """Deux points seulement, parce que ce sont les deux qui décident de la
    façon de répondre. Les recopier tous ferait un second rapport."""
    a = _dossier(("RC.pdf", RC))
    c = A.plan_reponse(a)["consultation"]
    assert set(c) == {"date_limite", "criteres"}, c


def test_sans_analyse_le_plan_dit_d_aller_lire_le_reglement():
    a = _dossier(("CCTP.pdf", CCTP))
    c = A.plan_reponse(a)["consultation"]
    assert "note" in c
    assert "règlement de consultation" in c["note"].lower()


def test_sans_analyse_du_tout_il_n_y_a_pas_de_rappel():
    assert A.plan_reponse(None)["consultation"] is None


# ── Le contrôle de chargement ──────────────────────────────────────────────

def test_toutes_les_expressions_regulieres_compilent():
    """Une expression invalide ferait échouer l'analyse au dépôt d'un
    document — au pire moment, sur un poste où personne ne peut la corriger.
    Le contrôle tourne au chargement ; celui-ci vérifie qu'il tourne."""
    assert A._verifier() == []


def test_le_controle_attrape_un_motif_invalide(monkeypatch):
    faux = [dict(r) for r in A.RELEVES]
    faux[0] = dict(faux[0], motifs=["("])
    monkeypatch.setattr(A, "RELEVES", faux)
    assert any("invalide" in f for f in A._verifier())


def test_le_controle_attrape_un_rang_de_lecture_en_double(monkeypatch):
    faux = {k: dict(v) for k, v in A.PIECES_MARCHE.items()}
    faux["cctp"]["rang_lecture"] = faux["ccap"]["rang_lecture"]
    monkeypatch.setattr(A, "PIECES_MARCHE", faux)
    assert any("double" in f for f in A._verifier())


# ── Le glossaire ───────────────────────────────────────────────────────────

def test_le_glossaire_couvre_les_pieces_de_marche_et_de_candidature():
    g = A.glossaire()
    assert set(g["piece_marche"]) == set(A.PIECES_MARCHE)
    assert set(g["piece_candidature"]) == {p["cle"] for p in A.DOSSIER_CANDIDATURE}


@pytest.mark.parametrize("famille", ["piece_marche", "piece_candidature"])
def test_aucune_infobulle_n_est_vide(famille):
    for cle, e in A.glossaire()[famille].items():
        assert len(e["aide"]) > 100, (famille, cle, len(e["aide"]))
