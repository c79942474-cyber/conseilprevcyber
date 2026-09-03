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
import re
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


# COMMENT LES ACHETEURS NOMMENT LEURS PIÈCES. Ce ne sont pas des noms
# inventés pour la règle : c'est la sortie d'une plateforme de
# dématérialisation, où le numéro d'ordre précède le sigle et où le séparateur
# est un souligné.
CONVENTIONS = [
    ("01_RC.pdf", "rc"),
    ("02_CCAP.pdf", "ccap"),
    ("03_CCTP.pdf", "cctp"),
    ("04_DPGF.xlsx", "dpgf"),
    ("05_BPU.xlsx", "bpu"),
    ("CCAP_v2.pdf", "ccap"),
    ("RC-2026-014.pdf", "rc"),
    ("DCE_CCAG-MOE.pdf", "ccag"),
    ("06_acte_d_engagement.pdf", "ae"),
    ("07_repartition_MOE_AMO.xlsx", "repartition"),
]


def test_une_piece_se_reconnait_a_son_NOM_SEUL():
    """CE QUE CETTE RÈGLE A COÛTÉ, ET POURQUOI ELLE PASSE LE TEXTE À VIDE.

    En expression régulière, « _ » est un caractère de MOT : `\brc\b` ne
    s'accroche donc pas dans « 01_RC.pdf », ni `\bccap\b` dans « CCAP_v2.pdf ».
    Le nom du fichier — que ce module regarde EN PREMIER parce qu'il est
    « presque toujours juste » — ne reconnaissait RIEN sur la convention la
    plus répandue des plateformes acheteur.

    ET AUCUNE RÈGLE NE LE VOYAIT, parce que toutes passaient un texte. Le texte
    rattrapait : un CCAP contient « cahier des clauses administratives
    particulières », et l'identification sortait juste POUR UNE RAISON SANS
    RAPPORT avec la moitié qu'elle prétendait éprouver. La première règle du
    fichier exigeait même une confiance « forte » sur « 02_CCAP_lot_unique.pdf »
    — obtenue par le seul texte.

    Le texte est donc VIDE ici. C'est la seule façon d'éprouver le nom."""
    for nom, attendu in CONVENTIONS:
        i = A.identifier(nom, "", "." + nom.rsplit(".", 1)[-1])
        assert i["reconnue"], "« %s » n'est pas reconnu sur son nom seul" % nom
        assert i["code"] == attendu, (
            "« %s » est rangé en %s au lieu de %s" % (nom, i["code"], attendu))


def test_un_sigle_dans_un_mot_n_est_pas_un_sigle():
    """LA CONTREPARTIE. Élargir la frontière ne doit pas la supprimer : « rc »
    dans « parcours », « cct » dans « cctp », « ae » dans « caen » ne sont pas
    des sigles. Sans ce témoin, la règle précédente se satisferait d'un motif
    qui reconnaît tout."""
    for nom in ("parcours_de_projet.pdf", "note_recette.pdf",
                "presentation_caen.pdf", "aerien.pdf"):
        i = A.identifier(nom, "")
        assert not i["reconnue"], (
            "« %s » est pris pour %s : le sigle a été trouvé dans un mot"
            % (nom, i.get("code")))


def test_une_piece_PRESENTE_n_est_jamais_declaree_manquante():
    """LA CONSÉQUENCE, ET C'EST ELLE QUI SE PAIE. Ce module vend « ce qui
    manque » comme son information la plus utile. Une DPGF est un TABLEUR : pas
    de texte, donc pas de rattrapage — « 04_DPGF.xlsx » était rangé en
    « Calculs » par son extension, et la DPGF, POSÉE DANS LE DOSSIER, ressortait
    dans la liste des pièces absentes. Se tromper là est pire que se taire."""
    a = A.analyser([{"nom": n, "texte": "",
                     "extension": "." + n.rsplit(".", 1)[-1]}
                    for n, _ in CONVENTIONS])
    manquants = {m["code"] for m in a["manquantes"]}
    presentes = {c for _, c in CONVENTIONS}
    assert not (manquants & presentes), (
        "des pièces posées dans le dossier sont déclarées absentes : %s"
        % sorted(manquants & presentes))


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


# Un règlement de consultation tel qu'un extracteur le rend : les phrases sont
# coupées par la MISE EN PAGE, pas par leur auteur, et l'adresse de la
# plateforme voisine avec le mot « acheteur ».
RC_FORMULAIRE = """RÈGLEMENT DE LA CONSULTATION
Pouvoir adjudicateur : Communauté d'agglomération de la Vallée, 12 rue du Port.
Objet du marché : maîtrise d'œuvre pour la construction d'un centre de données
de 4 MW IT sur le site de la zone d'activités nord.
Procédure adaptée ouverte, en application des articles R. 2123-1 et suivants.
Allotissement : le marché est décomposé en deux lots.
Lot n° 1 – conception et suivi de réalisation des infrastructures techniques.
Profil d'acheteur : https://marches.vallee-agglo.fr/consultation/2026-014
Date et heure limites de réception des offres : 30 octobre 2026 à 12 h 00.
"""


def _valeurs(cle, texte=RC_FORMULAIRE, piece="rc"):
    r = [x for x in A.relever(piece, texte) if x["cle"] == cle]
    assert r, "le relevé « %s » n'existe pas" % cle
    return [c["valeur"] for c in r[0]["citations"] if c["valeur"]]


def test_les_cinq_lignes_qui_ouvrent_tout_formulaire_sont_relevees():
    """CE QUI MANQUAIT. Le DC1, le DC2 et l'acte d'engagement commencent tous
    les trois par les mêmes lignes : qui achète, quoi, en combien de lots,
    selon quelle procédure, et où l'on dépose. Aucune n'était relevée — le
    module savait dire ce que la rubrique ATTEND et n'avait rien à y mettre."""
    for cle in ("acheteur", "objet", "lots", "procedure", "plateforme"):
        assert _valeurs(cle), "« %s » ne rend aucune valeur" % cle


def test_une_valeur_ne_voyage_jamais_sans_sa_citation_et_sa_position():
    """UNE VALEUR SANS SA PHRASE D'ORIGINE EST UNE INTERPRÉTATION DÉGUISÉE. Ce
    qui se recopie dans une case de formulaire doit pouvoir se vérifier sur la
    pièce : la citation entière et sa position sont rendues à côté."""
    for r in A.relever("rc", RC_FORMULAIRE):
        for c in r["citations"]:
            if c.get("valeur"):
                assert c["texte"], (r["cle"], "valeur sans citation")
                assert c["valeur"] in c["texte"] or (
                    c["valeur"].lower() in c["texte"].lower()), (
                    "« %s » : la valeur %r n'est pas dans sa citation %r"
                    % (r["cle"], c["valeur"], c["texte"]))
                assert isinstance(c["position"], int) and c["part"] >= 0, r["cle"]


def test_le_nom_de_l_acheteur_n_est_pas_une_adresse_web():
    """DÉFAUT ÉPROUVÉ, PAS IMAGINÉ. Le motif acceptait « acheteur » nu et
    attrapait « Profil d'acheteur : https://… » : il proposait une adresse web
    comme nom de pouvoir adjudicateur — dans la case la plus visible du DC1."""
    for v in _valeurs("acheteur"):
        assert not v.lower().startswith("http"), (
            "l'acheteur proposé est une adresse : %r" % v)


def test_l_objet_survit_au_retour_a_la_ligne_de_la_mise_en_page():
    """UN SAUT DE LIGNE N'EST PAS UNE FIN DE PHRASE. L'objet du marché tient
    sur deux lignes dans le RC d'essai parce qu'un PDF le coupe là ; s'arrêter
    au saut rendait la moitié de l'objet — et un DC1 dont l'objet est amputé
    ne désigne plus le même marché."""
    v = _valeurs("objet")[0]
    assert "4 MW" in v and "zone" in v, (
        "l'objet s'arrête au saut de ligne : %r" % v)


def test_l_adresse_de_la_plateforme_n_est_pas_coupee_au_premier_point():
    """Une adresse fausse est pire qu'une case vide : elle se recopie sans
    qu'on la relise. « https://marches » au lieu de
    « https://marches.vallee-agglo.fr/… » envoie déposer nulle part."""
    v = _valeurs("plateforme")
    assert v and v[0].endswith("2026-014"), "adresse tronquée : %r" % v
    assert not any(x == "https://marches" for x in v), (
        "une adresse tronquée est proposée à côté de la bonne : %r" % v)


def test_deux_citations_qui_disent_la_meme_valeur_sont_une_proposition():
    """« Profil d'acheteur : https://x » et « https://x » sont deux phrases et
    UNE SEULE adresse. Les rendre deux fois ferait croire à deux plateformes,
    et obligerait à choisir entre deux propositions identiques."""
    for cle in ("acheteur", "objet", "procedure", "plateforme"):
        v = _valeurs(cle)
        assert len(v) == len(set(v)), "« %s » se répète : %r" % (cle, v)


def test_une_piece_qui_ne_porte_pas_la_ligne_ne_l_invente_pas():
    """LE TÉMOIN. Sans lui, un motif qui capture n'importe quoi passerait les
    six règles précédentes."""
    for cle in ("acheteur", "objet", "lots", "procedure", "plateforme"):
        r = [x for x in A.relever("rc", "Texte sans aucune de ces mentions.")
             if x["cle"] == cle]
        if r:
            assert not r[0]["trouve"], (
                "« %s » trouve quelque chose dans un texte qui n'en parle pas"
                % cle)
            assert r[0]["note"], "« %s » ne dit pas qu'il n'a pas trouvé" % cle


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


# ═══════════════════════════════════════════════════════════════════════════
#  LE REMPLISSAGE DES PIÈCES — ce qui se recopie, ce qui ne se déclare jamais
# ═══════════════════════════════════════════════════════════════════════════
# LA LIGNE QUE CES RÈGLES TIENNENT. Un dossier de candidature, c'est quatorze
# pièces qui redemandent les mêmes vingt informations, et les recopier à la
# main est le travail qui produit les fautes de cohérence dont les
# candidatures meurent. Ce module les recopie donc — et il ne DÉCLARE rien :
# les DC1, DC2 et déclarations sur l'honneur portent des affirmations dont la
# fausseté est sanctionnée pénalement, et une case cochée par un programme est
# une déclaration que personne n'a faite.

FICHE = {
    "raison_sociale": "Bureau d'études Essai", "forme_juridique": "SAS",
    "siret": "80295478500019", "adresse": "5 rue de l'Essai",
    "representant_nom": "A. Dupont", "representant_qualite": "Président",
}

CCTP_AUTRE_OBJET = """CAHIER DES CLAUSES TECHNIQUES PARTICULIÈRES
Objet du marché : assistance à maîtrise d'ouvrage pour un centre de données.
Le PUE annuel engagé est de 1,25.
"""


def _rempli(fiche=None, avec_dossier=True, **kw):
    an = A.analyser([{"nom": "01_RC.pdf", "texte": RC_FORMULAIRE},
                     {"nom": "03_CCTP.pdf", "texte": CCTP_AUTRE_OBJET}]) \
        if avec_dossier else None
    return A.remplir(fiche=FICHE if fiche is None else fiche, analyse=an, **kw)


def _lignes(r):
    for p in r["pieces"]:
        for l in p["rubriques"]:
            yield p, l


def test_aucune_declaration_sur_l_honneur_n_est_JAMAIS_pre_remplie():
    """LA LIGNE À NE PAS FRANCHIR, ET LA RAISON DE TOUT CE QUI PRÉCÈDE. Ces
    affirmations — ne pas entrer dans un cas d'exclusion, être à jour de ses
    obligations fiscales et sociales — engagent pénalement celui qui les signe.
    Une case cochée par un programme est une déclaration que personne n'a
    faite. Elles ressortent VIDES, au statut `a_declarer`, avec le texte exact
    de ce qui est affirmé, quelle que soit la richesse de la fiche."""
    fiche_pleine = {c["cle"]: "renseigné" for c in A.CHAMPS_CANDIDAT}
    fiche_pleine["siret"] = "80295478500019"
    for r in (_rempli(), _rempli(fiche=fiche_pleine)):
        decl = [l for _p, l in _lignes(r) if l["source"] == "declaration"]
        assert len(decl) >= 4, "trop peu de déclarations pour que la règle mesure"
        for l in decl:
            assert l["statut"] == "a_declarer", (l["cle"], l["statut"])
            assert l["valeur"] is None, (
                "la déclaration « %s » est pré-remplie : %r"
                % (l["cle"], l["valeur"]))
            assert (l.get("texte") or "").strip(), (
                "« %s » ne dit pas ce qui est affirmé — on signerait à "
                "l'aveugle" % l["cle"])


def test_le_texte_d_une_declaration_est_celui_de_la_piece_MOT_POUR_MOT():
    """DEUX RÉDACTIONS DE LA MÊME DÉCLARATION FINIRAIENT PAR NE PLUS DIRE LA
    MÊME CHOSE. Le texte affiché n'est pas réécrit : il est repris de ce que la
    pièce déclare contenir, et la règle refuse qu'il en diverge."""
    par_piece = {p["cle"]: p for p in A.DOSSIER_CANDIDATURE}
    for _p, l in _lignes(_rempli()):
        if l["source"] != "declaration":
            continue
        assert any(l["texte"] == c
                   for piece in par_piece.values()
                   for c in piece["contient"]), (
            "« %s » porte un texte de déclaration qui n'existe dans aucune "
            "pièce : il a été réécrit à côté" % l["cle"])


def test_une_piece_qui_porte_une_declaration_n_est_JAMAIS_dite_prete():
    """DÉFAUT ÉPROUVÉ DANS MON PROPRE CODE. `pret` était calculé sans regarder
    les déclarations, sous un commentaire qui affirmait le contraire : un DC1
    dont toutes les cases factuelles étaient remplies ressortait « prêt » avec
    sa déclaration sur l'honneur vierge. C'est une SIGNATURE qui rend une pièce
    prête, et personne ici ne signe."""
    fiche_pleine = {c["cle"]: "renseigné" for c in A.CHAMPS_CANDIDAT}
    fiche_pleine["siret"] = "80295478500019"
    r = _rempli(fiche=fiche_pleine)
    avec = [p for p in r["pieces"] if p["porte_declaration"]]
    assert avec, "aucune pièce ne porte de déclaration : la règle ne mesure rien"
    for p in avec:
        assert not p["pret"], (
            "« %s » est dite prête alors qu'il reste %d déclaration(s) à signer"
            % (p["nom"], p["compte"]["a_declarer"]))
    # ET LE TÉMOIN : « complète » doit, lui, pouvoir être vrai — sans quoi la
    # règle serait satisfaite par un module qui ne remplit jamais rien.
    assert any(p["complet"] for p in r["pieces"]), (
        "aucune pièce n'est complète : la distinction ne sépare rien")


def test_toute_valeur_remplie_porte_son_origine():
    """UNE VALEUR SANS ORIGINE SE RECOPIE SANS SE RELIRE, et c'est ainsi qu'un
    SIRET d'une autre filiale finit sur un DC2. Trois origines, et elles ne
    s'équivalent pas : votre fiche, un relevé daté dans une pièce, un calcul
    dont la règle est nommée."""
    for _p, l in _lignes(_rempli()):
        if l["statut"] == "rempli" and l["source"] != "saisie":
            assert (l["origine"] or "").strip(), (
                "« %s » est remplie sans dire d'où elle vient" % l["cle"])


def test_une_valeur_venue_du_dossier_arrive_avec_sa_citation():
    """CE QUI SE RECOPIE DOIT POUVOIR SE VÉRIFIER SUR LA PIÈCE. Une valeur
    relevée sans sa phrase ni sa position est une interprétation déguisée."""
    vus = 0
    for _p, l in _lignes(_rempli()):
        if l["source"] == "consultation" and l["statut"] == "rempli":
            vus += 1
            assert l["citation"], "« %s » : valeur sans citation" % l["cle"]
            assert l["citation"]["texte"] and l["citation"]["fichier"], l["cle"]
            assert l["valeur"].lower() in l["citation"]["texte"].lower(), (
                "« %s » : la valeur n'est pas dans sa citation" % l["cle"])
    assert vus >= 3, "trop peu de valeurs relevées pour que la règle mesure"


def test_deux_pieces_qui_se_contredisent_ne_s_ecrasent_pas_en_silence():
    """L'OBJET DU RC ET CELUI DU CCTP DIFFÈRENT PARFOIS D'UN MOT QUI CHANGE LE
    PÉRIMÈTRE. La valeur retenue est celle de la pièce qu'on ouvre en premier ;
    l'autre est rendue comme une DIVERGENCE. Écraser en silence ferait remplir
    un DC1 sur un périmètre que le CCTP contredit."""
    r = _rempli()
    div = [l for _p, l in _lignes(r) if l["divergences"]]
    assert div, ("la divergence entre le RC et le CCTP sur l'objet n'est pas "
                 "signalée")
    for l in div:
        assert l["valeur"] and l["valeur"] not in [d["valeur"]
                                                   for d in l["divergences"]]
        assert "tranche" in (l["message"] or "").lower(), l["cle"]


def test_ce_qui_n_est_pas_trouve_dit_OU_le_trouver():
    """« À saisir » sans dire où chercher est une impasse polie. Chaque champ
    de fiche non renseigné rend la phrase qui dit sur quel document il se lit —
    Kbis, liasse fiscale, avis de situation INSEE."""
    r = _rempli(fiche={})
    manquants = [l for _p, l in _lignes(r) if l["source"] == "fiche"
                 and l["statut"] == "a_saisir"]
    assert len(manquants) >= 8, "trop peu de champs vides pour mesurer"
    for l in manquants:
        assert (l["message"] or "").strip(), (
            "« %s » ne dit pas où trouver la valeur" % l["cle"])


def test_un_releve_absent_du_dossier_ne_s_invente_pas():
    """SANS DOSSIER DÉPOSÉ, les rubriques qui viennent des pièces de l'acheteur
    restent VIDES et le disent — elles ne se remplissent pas d'un défaut."""
    r = _rempli(avec_dossier=False)
    assert r["sans_dossier"] is True
    cons = [l for _p, l in _lignes(r) if l["source"] == "consultation"]
    assert cons, "aucune rubrique ne vient de la consultation"
    for l in cons:
        assert l["statut"] == "non_trouve" and l["valeur"] is None, l["cle"]
        assert "pas vu" in (l["message"] or ""), (
            "« %s » laisse croire que l'information n'existe pas" % l["cle"])


def test_un_SIRET_faux_est_refuse_avec_SA_raison():
    """UN CONTRÔLE NE VALIDE PAS UNE VALEUR, IL ÉCARTE UNE FAUTE DE FRAPPE. Un
    SIRET syntaxiquement juste peut être celui d'une autre société ; un SIRET
    dont la clé ne tombe pas est faux à coup sûr, et il vaut mieux l'apprendre
    ici que dans la lettre de rejet."""
    assert A.controler("siret", "80295478500019") == (True, None)
    for faux, attendu in (("80295478500011", "clé de contrôle"),
                          ("802954785000", "quatorze"),
                          ("8029547850001A", "chiffres")):
        ok, pourquoi = A.controler("siret", faux)
        assert ok is False and attendu in pourquoi, (faux, pourquoi)
    # LA POSTE EST L'EXCEPTION CONNUE : ses établissements ne satisfont pas la
    # clé de Luhn. La règle générale les refuserait à tort, et on ferait
    # corriger un numéro juste.
    #
    # LE NUMÉRO D'ESSAI DOIT ÉCHOUER À LUHN, sans quoi la règle est verte pour
    # une raison sans rapport avec ce qu'elle prétend. Ma première version
    # employait 35600000000048, qui passe Luhn tout seul : retirer l'exception
    # ne faisait rien tomber, et la mutation l'a montré.
    assert not A._luhn("35600000009075"), (
        "le numéro d'essai passe la clé générale : il n'éprouve pas "
        "l'exception")
    ok, _ = A.controler("siret", "35600000009075")
    assert ok is True, "un SIRET de La Poste est refusé à tort"
    # ET L'EXCEPTION A SA PROPRE RÈGLE — la somme des quatorze chiffres est un
    # multiple de cinq. Sans ce témoin, l'exception accepterait n'importe quel
    # numéro commençant par 356000000, faute de frappe comprise.
    ok, pourquoi = A.controler("siret", "35600000000016")
    assert ok is False and "multiple de cinq" in pourquoi, (
        "l'exception La Poste est un trou : elle accepte %r" % pourquoi)
    r = _rempli(fiche=dict(FICHE, siret="80295478500011"))
    mauvais = [l for _p, l in _lignes(r) if l["statut"] == "invalide"]
    assert mauvais and all(l["message"] for l in mauvais), (
        "un SIRET faux passe sans être signalé")


def test_ce_qui_se_deduit_le_dit_et_suit_la_regle_ecrite():
    """DÉDUIRE N'EST PAS INVENTER, à une condition : que la règle soit écrite
    et vérifiable. Le SIREN, ce sont les neuf premiers chiffres du SIRET ; la
    clé de TVA est (12 + 3 × (SIREN mod 97)) mod 97. La règle recalcule au lieu
    de recopier un résultat."""
    for siret in ("80295478500019", "35600000000048", "55208131766522"):
        d = A.derive({"siret": siret})
        siren = siret[:9]
        assert d["siren"]["valeur"] == siren
        attendu = "FR%02d%s" % ((12 + 3 * (int(siren) % 97)) % 97, siren)
        assert d["tva"]["valeur"] == attendu, (siret, d["tva"])
        for x in ("siren", "tva"):
            assert d[x]["regle"].strip(), "%s se déduit sans dire comment" % x
    assert A.derive({}) == {}, "quelque chose se déduit d'un SIRET absent"


def test_le_remplissage_ne_garde_rien_entre_deux_appels():
    """CETTE FONCTION NE CONSERVE RIEN : ni la fiche, ni l'analyse, ni les
    saisies. Un état retenu ferait ressortir, sur la consultation suivante, des
    valeurs de la précédente — et personne ne relit une case déjà remplie."""
    a = _rempli(fiche=FICHE)
    b = _rempli(fiche={})
    va = [l["valeur"] for _p, l in _lignes(a) if l["source"] == "fiche"]
    vb = [l["valeur"] for _p, l in _lignes(b) if l["source"] == "fiche"]
    assert any(va) and not any(vb), (
        "une valeur du premier appel survit au second")


def test_une_saisie_propre_a_la_consultation_ne_va_pas_dans_la_fiche():
    """LES LOTS VISÉS OU LA FORME DU GROUPEMENT NE SONT PAS DE L'IDENTITÉ : ils
    changent à chaque consultation. Les ranger dans la fiche les reporterait,
    faux, sur la suivante."""
    cles = {c["cle"] for c in A.CHAMPS_CANDIDAT}
    saisies = [l for _p, l in _lignes(_rempli()) if l["source"] == "saisie"]
    assert saisies, "aucune rubrique propre à la consultation"
    for l in saisies:
        assert l["cle"] not in cles, (
            "« %s » est à la fois une saisie de consultation et un champ de "
            "fiche" % l["cle"])
    r = A.remplir(fiche=FICHE, saisies={"dc1.objet_candidature": "Lot n° 1"})
    vus = [l for _p, l in _lignes(r) if l["cle"] == "objet_candidature"]
    assert vus and vus[0]["valeur"] == "Lot n° 1" and vus[0]["statut"] == "rempli"


def test_chaque_rubrique_designe_quelque_chose_qui_existe():
    """LE CONTRÔLE DE STRUCTURE, ET IL A DÉJÀ SERVI. Une rubrique qui désigne un
    relevé SANS GROUPE DE CAPTURE est une case définitivement vide : la
    « Référence de la consultation » du DC1 ressortait « non relevée » sur un
    dossier qui la portait en toutes lettres. Rien ne plantait."""
    assert A._FAUTES == [], A._FAUTES
    par_releve = {r["cle"]: r for r in A.RELEVES}
    for piece, rubriques in A.RUBRIQUES.items():
        for r in rubriques:
            if r["source"] != "consultation":
                continue
            rel = par_releve[r["releve"]]
            assert any(re.compile(m).groups for m in rel["motifs"]), (
                "%s/%s vise « %s », qui cite sans capturer"
                % (piece, r["cle"], r["releve"]))


def test_le_document_emporte_dit_la_meme_chose_que_l_ecran():
    """UN DOCUMENT QUI DIVERGE DE L'ÉCRAN EST PIRE QU'AUCUN DOCUMENT : il
    circule, et c'est lui qu'on relit. Il est donc rendu par la MÊME fonction,
    et la règle vérifie que chaque valeur affichée s'y retrouve."""
    r = _rempli()
    md = A.markdown_remplissage(r)
    valeurs = [l["valeur"] for _p, l in _lignes(r)
               if l["valeur"] and l["source"] != "declaration"]
    assert len(valeurs) >= 8, "trop peu de valeurs pour mesurer"
    for v in valeurs:
        assert " ".join(v.split())[:120] in " ".join(md.split()), (
            "la valeur %r ne figure pas dans le document emporté" % v[:60])


def test_le_document_emporte_ne_signe_rien_non_plus():
    """LES PRÉ-REMPLIR DANS UN DOCUMENT EXPORTÉ SERAIT PIRE QUE DANS LA PAGE :
    le document circule, et il se signerait sans être lu. Les déclarations en
    sortent avec leur texte et une ligne de signature vierge."""
    md = A.markdown_remplissage(_rempli())
    assert "Date et signature" in md and "_____" in md, (
        "le document ne laisse pas de place à une signature")
    for _p, l in _lignes(_rempli()):
        if l["source"] == "declaration":
            assert l["texte"] in md, "le texte déclaré n'est pas dans le document"
    assert "ne déclare pas" in md.lower() or "jamais pré-remplies" in md.lower()


def test_une_valeur_a_rallonge_ne_casse_pas_le_tableau_emporte():
    """UN CARACTÈRE « | » DANS UNE RAISON SOCIALE CASSERAIT LE TABLEAU, et le
    document sortirait illisible sans que rien n'ait échoué."""
    md = A.markdown_remplissage(
        A.remplir(fiche=dict(FICHE, raison_sociale="A | B\nC")))
    lignes = [l for l in md.split("\n") if l.startswith("| ")]
    assert lignes, "aucun tableau"
    for l in lignes:
        assert l.count("|") - l.count("\\|") == 5 or l.count("|") <= 3, l
