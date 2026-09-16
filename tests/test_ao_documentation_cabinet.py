# -*- coding: utf-8 -*-
"""UNE FICHE TECHNIQUE, UN GUIDE, UNE NORME — RANGÉS, PUIS RETROUVÉS PARCE QUE
CE MARCHÉ-CI LES EXIGE.

DEUX DÉFAUTS, MESURÉS LE 16 SEPTEMBRE 2026, ET LE SECOND EST LE PLUS COÛTEUX.

1. L'ÉTAGÈRE REFUSAIT LA DOCUMENTATION. Sur neuf noms de fichiers qu'un
   cabinet conserve — fiche technique, guide, norme, catalogue, méthodologie,
   retour d'expérience, CV, références, référentiel — SEPT étaient refusés.
   La raison : les dix rayons suivaient les PIÈCES d'un dossier de
   candidature, et une norme n'est pas une pièce. Elle est pourtant la matière
   avec laquelle un mémoire technique s'écrit.

2. LA RECHERCHE NE VISAIT PAS CE MARCHÉ-CI. Sur une étagère de quinze
   documents portant TOUS sur le centre de données — le cas d'un cabinet
   spécialisé — la recherche remontait UN des quatre documents qui répondent
   au CCTP. Sept des huit places allaient au désamiantage, à la fiscalité
   locale, au plan de formation. La fiche du groupe froid N+1, la norme
   EN 50600 et la convention BIM étaient écartées : les trois que l'acheteur
   exige.

   LA CAUSE. La requête portait l'OBJET de la consultation et le nom de nos
   rayons. L'objet dit le DOMAINE ; il ne dit pas ce que CE marché exige. Sur
   une étagère où les quinze documents sont du domaine, le domaine ne
   distingue plus rien.

APRÈS : 9 des 9 types se rangent, et 4 des 4 documents utiles remontent —
en tête.

ET UN TROISIÈME TIERS, PARCE QUE CES DOCUMENTS NE SONT PAS DE NOUS. Une norme
appartient à son organisme, une fiche produit à son fabricant. Le risque n'est
pas la confidentialité d'un client — c'est le droit d'auteur, et le régime de
publication n'y peut rien : marquer publiable une norme EN 50600 ne donne pas
le droit de la recopier. La barrière est donc dans la consigne, au moment
d'écrire, et non dans le rangement.
"""
import io
import os
import re
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc                                                     # noqa: E402
import ao_extraction                                             # noqa: E402
import ao_redaction as R                                         # noqa: E402
import dossier_cabinet                                           # noqa: E402
import rag_store                                                 # noqa: E402

import pytest                                                    # noqa: E402

from test_ao_dossier_marche_rediction import DOCUMENTS           # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
#  1. CE QUI SE RANGE — neuf types, et pas seulement les pièces d'un dossier.
# ═══════════════════════════════════════════════════════════════════════════
RANGEABLES = {
    "fiche-technique-groupe-froid-carrier.pdf":
        "Cabinet / Fiches techniques & documentation produit",
    "catalogue-onduleurs-schneider.pdf":
        "Cabinet / Fiches techniques & documentation produit",
    "notice-de-montage-groupe-electrogene.pdf":
        "Cabinet / Fiches techniques & documentation produit",
    "guide-anssi-hygiene-informatique.pdf":
        "Cabinet / Normes, guides & référentiels",
    "norme-EN-50600-2-3.pdf": "Cabinet / Normes, guides & référentiels",
    "uptime-institute-tier-standard.pdf":
        "Cabinet / Normes, guides & référentiels",
    "referentiel-iso-27001.pdf": "Cabinet / Normes, guides & référentiels",
    "methodologie-de-commissionnement.pdf":
        "Cabinet / Mémoires techniques & notes méthodologiques",
    "retour-experience-pue-datacenter.docx":
        "Cabinet / Mémoires techniques & notes méthodologiques",
    # ET LES PIÈCES CONTINUENT DE SE RANGER COMME AVANT : la documentation
    # s'AJOUTE, elle ne remplace pas. Sans ces deux lignes, une régression qui
    # ferait tomber la reconnaissance des pièces passerait inaperçue ici.
    "cv-jean-dupont.pdf": "Cabinet / Moyens humains, CV & organigramme",
    "organigramme-2026.pdf": "Cabinet / Moyens humains, CV & organigramme",
}


@pytest.mark.parametrize("nom", sorted(RANGEABLES))
def test_chaque_type_de_document_du_cabinet_TROUVE_son_rayon(nom):
    """SEPT DE CES ONZE ÉTAIENT REFUSÉS. Le refus disait « son nom ne le
    rattache à aucune des pièces à produire » — et c'était vrai, et c'était
    hors sujet : on ne remet pas un guide ANSSI à un acheteur."""
    d = dossier_cabinet.destination(ao_dc.piece_du_cabinet(nom), nom)
    assert not d["refus"], "%s : %s" % (nom, d["dit"])
    assert d["rayon"] == RANGEABLES[nom], (nom, d["rayon"])


def test_tous_les_rayons_de_documentation_EXISTENT_dans_la_famille():
    """UN RAYON MAL ORTHOGRAPHIÉ RANGE DANS LE VIDE. Le document part au
    magasin, l'écran dit « rangé », et aucune recherche ne le retrouve jamais —
    la panne la plus silencieuse de toute la chaîne."""
    famille = set(rag_store.themes_famille(rag_store.FAMILLE_CABINET))
    for rayon, _motifs in ao_dc.DOCUMENTATION_MOTIFS:
        assert rayon in famille, (
            "« %s » n'est pas un rayon de la famille du cabinet" % rayon)
    for rayon in R.FONDS_DOCUMENTATION:
        assert rayon in famille, rayon


def test_ce_qui_n_est_NI_piece_NI_documentation_est_refusé_ET_orienté():
    """LE REFUS DOIT DIRE LES DEUX VOIES. Il n'en nommait qu'une — « la pièce
    qu'il fournit » — et laissait donc chercher un nom de pièce pour un
    document qui n'en est pas une."""
    nom = "photo-du-pot-de-depart.jpg"
    d = dossier_cabinet.destination(ao_dc.piece_du_cabinet(nom), nom)
    assert d["refus"] == "piece_inconnue"
    # LES DEUX VOIES SONT NOMMÉES, ET ON LES MESURE TOUTES DEUX. La première
    # version ne cherchait que les exemples de documentation — or c'est la
    # PHRASE qui annonce les deux voies qui porte le sens, et une mutation qui
    # la remplaçait par « la pièce qu'il fournit » laissait les exemples en
    # place : le refus redevenait trompeur et la règle restait verte.
    assert "ni la pièce" in d["dit"] and "ni la documentation" in d["dit"], (
        "le refus n'annonce pas les deux voies : %s" % d["dit"])
    assert "fiche-technique" in d["dit"] and "norme" in d["dit"], (
        "le refus ne donne aucun exemple de documentation : %s" % d["dit"])


def test_une_DPGF_ne_se_conserve_toujours_PAS():
    """LA DOCUMENTATION S'AJOUTE, ELLE N'OUVRE PAS LA PORTE. Une DPGF chiffrée
    pour ce marché-ci n'a rien à faire sur une étagère réutilisée ailleurs, et
    le motif « guides » ne doit pas la faire entrer par la bande."""
    nom = "dpgf-chiffree-2026.xlsx"
    d = dossier_cabinet.destination(ao_dc.piece_du_cabinet(nom), nom)
    assert d["refus"] == "ne_se_conserve_pas", d


def test_le_rangement_passe_le_NOM_a_la_destination():
    """LE FIL, ET PAS SEULEMENT SES DEUX BOUTS. `destination` peut reconnaître
    parfaitement la documentation et `ranger` ne pas lui donner le nom : le
    document serait refusé quand même, et les règles au-dessus resteraient
    vertes puisqu'elles appellent `destination` directement."""
    rag = rag_store.MemoryRagStore()
    r = dossier_cabinet.ranger(
        rag, "guide-anssi-hygiene-informatique.txt",
        b"Guide d'hygiene informatique de l'ANSSI, 42 mesures.",
        ao_dc.piece_du_cabinet("guide-anssi-hygiene-informatique.txt"),
        visibilite="internal")
    assert r["rayon"] == "Cabinet / Normes, guides & référentiels", r


def test_la_documentation_NOURRIT_les_brouillons_quel_que_soit_le_regime():
    """L'ÉCRAN NE DOIT PAS NIER UN APPORT RÉEL.

    `_nourrit` rendait `False` sur ces deux rayons — l'écran aurait donc dit
    qu'une norme rangée n'atteint aucun brouillon, alors que le rédacteur la
    lit sans filtre de publication. Une colonne qui nie un apport se paie deux
    fois : on range moins, et on relit moins ce qui sort."""
    for rayon in R.FONDS_DOCUMENTATION:
        assert dossier_cabinet._nourrit(rayon, "internal") is True, rayon
        assert dossier_cabinet._nourrit(rayon, "public") is True, rayon


# ═══════════════════════════════════════════════════════════════════════════
#  2. LES DÉSIGNATIONS DE CE MARCHÉ-CI.
# ═══════════════════════════════════════════════════════════════════════════
@pytest.fixture(scope="module")
def corpus():
    a = ao_dc.analyser(DOCUMENTS)
    return a, ao_extraction.corpus(DOCUMENTS, a)


def test_les_designations_du_marche_sont_RELEVEES(corpus):
    """CE QUI DISTINGUE CE MARCHÉ D'UN AUTRE DU MÊME DOMAINE."""
    _a, corp = corpus
    d = R.designations_du_marche(corp)
    for x in ("PUE", "BIM", "ANSSI", "HQE", "N+1", "2N"):
        assert x in d, ("« %s » figure dans le dossier et n'est pas relevé : "
                        "%s" % (x, d))


def test_un_TITRE_en_capitales_ne_donne_AUCUNE_designation():
    """LA MOITIÉ QUI FAIT MARCHER L'AUTRE. Sans le tri des titres, « CAHIER DES
    CLAUSES TECHNIQUES PARTICULIERES » livrerait quatre mots français qui
    figurent dans tous les dossiers — et la requête cesserait de distinguer
    quoi que ce soit, tout en paraissant travailler."""
    corp = {"pieces": [{"fichier": "T.pdf", "sigle": "T", "cote": "consultation",
                        "texte": "CAHIER DES CLAUSES TECHNIQUES "
                                 "PARTICULIERES APPLICABLES AU PRESENT "
                                 "MARCHE DE MAITRISE D OEUVRE"}]}
    assert R.designations_du_marche(corp) == [], R.designations_du_marche(corp)


def test_une_designation_AU_MILIEU_d_une_phrase_est_relevee():
    """ET L'AUTRE MOITIÉ : c'est bien la casse ENVIRONNANTE qui décide, pas la
    longueur du mot. « PUE » et « CAHIER » ont trois et six lettres ; ce qui
    les sépare est la phrase où ils se trouvent."""
    corp = {"pieces": [{"fichier": "T.pdf", "sigle": "T", "cote": "consultation",
                        "texte": "Le PUE cible en regime nominal est de 1,25 "
                                 "et la redondance attendue est N+1 sur la "
                                 "production de froid du batiment."}]}
    d = R.designations_du_marche(corp)
    assert "PUE" in d and "N+1" in d, d


def test_les_designations_sont_BORNEES():
    """UN DOSSIER PEUT EN PORTER CENT. La requête a un budget de six cents
    signes : sans borne ici, les désignations le rempliraient seules et
    chasseraient le nom des rayons — donc le CV et l'organigramme, que les
    désignations ne retrouvent jamais.

    CETTE RÈGLE ÉTAIT VERTE POUR RIEN. Elle mesurait le dossier d'essai, qui
    porte DIX désignations pour une borne de dix-huit : supprimer la borne n'y
    changeait rien, et la mutation est passée au travers. Une règle qui mesure
    un plafond doit le dépasser — on écrit donc un dossier qui en porte le
    triple.
    """
    articles = []
    for i in range(60):
        articles.append(
            "Article %d - Le titulaire respecte le referentiel XY%02d et "
            "atteint la valeur cible de l'indicateur ZZ%02d sur l'ensemble "
            "des installations concernees par le present marche." % (i, i, i))
    corp = {"pieces": [{"fichier": "T.pdf", "sigle": "T",
                        "cote": "consultation",
                        "texte": "\n\n".join(articles)}]}
    brut = R.designations_du_marche(corp, maxi=999)
    assert len(brut) > R.DESIGNATIONS_MAX, (
        "le dossier d'essai ne porte que %d désignations : il ne peut pas "
        "mesurer une borne de %d" % (len(brut), R.DESIGNATIONS_MAX))
    assert len(R.designations_du_marche(corp)) <= R.DESIGNATIONS_MAX


# ═══════════════════════════════════════════════════════════════════════════
#  3. LE POINT DUR : L'ÉTAGÈRE PLEINE, OÙ LE DOMAINE NE DISTINGUE PLUS RIEN.
# ═══════════════════════════════════════════════════════════════════════════
DC = "centre de donnees"
MAT = "Cabinet / Moyens matériels & techniques"
QSE = "Cabinet / Qualifications, certifications & QSE"
RH = "Cabinet / Moyens humains, CV & organigramme"
DOC = "Cabinet / Fiches techniques & documentation produit"
NORM = "Cabinet / Normes, guides & référentiels"

# CE QUE CE CCTP-CI EXIGE : PUE 1,25 · N+1 · Tier III · BIM 2 · ANSSI · HQE.
UTILES = {
    "Guide ANSSI hygiene informatique": (NORM,
        "Guide d'hygiene informatique de l'ANSSI, 42 mesures. Segmentation "
        "des reseaux d'administration et cloisonnement de la gestion "
        "technique de batiment sur un %s." % DC),
    "Fiche technique groupe froid N+1": (DOC,
        "Groupes d'eau glacee en architecture N+1 pour %s, basculement sans "
        "perte de charge, compatible d'un PUE de 1,25." % DC),
    "Norme EN 50600 classes de disponibilite": (NORM,
        "La serie EN 50600 traite des infrastructures de %s. Les classes 1 a "
        "4 correspondent aux niveaux Tier de l'Uptime Institute." % DC),
    "Convention BIM niveau 2 CONSEILPREV": (MAT,
        "Notre convention BIM de niveau 2 pour les projets de %s : maquette "
        "IFC 4 remise a chaque phase, referent BIM designe." % DC),
}
# ONZE DOCUMENTS DU MÊME DOMAINE ET D'AUCUN SECOURS ICI. C'est eux qui
# prenaient sept des huit places.
INUTILES = {
    "Plaquette commerciale CONSEILPREV": (MAT,
        "CONSEILPREV, conseil en prevention. Nos bureaux de Lyon et "
        "Marseille, et nos projets de %s." % DC),
    "Note sur le raccordement HTA": (MAT,
        "Raccordement HTA d'un %s : demarches, delais de six a dix-huit "
        "mois." % DC),
    "Etude acoustique de voisinage": (MAT,
        "Etude acoustique autour d'un %s : propagation, ecrans, groupes "
        "electrogenes en limite de propriete." % DC),
    "Guide du desamiantage en site occupe": (QSE,
        "Desamiantage d'un batiment reconverti en %s : reperage, "
        "confinement, elimination." % DC),
    "Note sur la fiscalite locale des datacenters": (MAT,
        "Fiscalite d'un %s : taxe fonciere, CFE, IFER." % DC),
    "Retour d'experience sur un litige de chantier": (QSE,
        "Litige sur un chantier de %s : reception avec reserves, expertise "
        "judiciaire." % DC),
    "Fiche de poste technicien d'exploitation": (RH,
        "Fiche de poste du technicien d'exploitation d'un %s : rondes, "
        "releves, astreinte." % DC),
    "Note sur les baux et servitudes": (MAT,
        "Baux et servitudes d'un terrain accueillant un %s." % DC),
    "Guide de la maintenance des batteries": (MAT,
        "Maintenance des parcs de batteries d'onduleurs d'un %s." % DC),
    "Note sur le recrutement des exploitants": (RH,
        "Recrutement des equipes d'exploitation d'un %s." % DC),
    "Plan de formation interne 2026": (RH,
        "Plan de formation des equipes CONSEILPREV pour 2026, missions de "
        "%s incluses." % DC),
}


@pytest.fixture(scope="module")
def etagere_pleine():
    rag = rag_store.MemoryRagStore()
    for titre, (theme, texte) in list(UTILES.items()) + list(INUTILES.items()):
        rag.ingest_bytes(titre.replace(" ", "-") + ".txt",
                         texte.encode("utf-8"), title=titre, theme=theme,
                         visibility="internal")
    return rag


def _memoire(corpus):
    a, _corp = corpus
    r = ao_dc.remplir(fiche={"raison_sociale": "CONSEILPREV"}, analyse=a)
    return next(p for p in R.pieces_redigeables(r)
                if p["cle"] == "memoire_technique")


def test_l_etagere_d_essai_est_INDISCERNABLE_par_le_domaine(etagere_pleine):
    """LA GARDE QUI REND LES DEUX RÈGLES SUIVANTES VALIDES. Si un seul de ces
    quinze documents ne parlait pas du domaine, la recherche par domaine
    suffirait à trier — et l'on mesurerait un tri qui n'a pas lieu."""
    for titre, (_t, texte) in list(UTILES.items()) + list(INUTILES.items()):
        assert DC in texte, (
            "« %s » ne parle pas du domaine : l'étagère d'essai cesse de "
            "mesurer ce qu'elle prétend" % titre)


def test_SANS_le_dossier_la_recherche_ne_distingue_PAS(corpus, etagere_pleine):
    """LE DÉFAUT, TENU EN PLACE. Cette règle ne décrit pas un bug à corriger :
    elle fixe ce que vaut la recherche quand la route rédige SANS les documents
    du marché — et c'est un cas réel, celui d'un brouillon demandé avant tout
    dépôt. Elle empêche qu'on croie ce chemin équivalent à l'autre."""
    f = R.chercher_au_fonds_cabinet(_memoire(corpus), etagere_pleine,
                                    corpus[0], None)
    bons = [s for s in f["sources"] if s["titre"] in UTILES]
    assert len(bons) < len(UTILES), (
        "sans le dossier, la recherche trouverait tout : alors le dossier ne "
        "sert à rien et la règle suivante ne mesure rien")


def test_AVEC_le_dossier_la_recherche_remonte_CE_QUE_LE_MARCHE_EXIGE(
        corpus, etagere_pleine):
    """LA RÈGLE QUI PORTE TOUT LE TOUR.

    Quinze documents, tous du domaine ; quatre répondent à CE CCTP. Sans les
    désignations du marché, un seul remontait. On ne demande pas qu'il remonte
    « quelque chose » — on nomme les quatre."""
    _a, corp = corpus
    f = R.chercher_au_fonds_cabinet(_memoire(corpus), etagere_pleine,
                                    corpus[0], corp)
    titres = [s["titre"] for s in f["sources"]]
    manque = [t for t in UTILES if t not in titres]
    assert not manque, (
        "ces documents répondent au CCTP et ne remontent pas : %s — remontés "
        "à la place : %s" % (manque, titres))


def test_les_documents_UTILES_arrivent_EN_TETE(corpus, etagere_pleine):
    """L'ORDRE COMPTE AUTANT QUE LA PRÉSENCE. Le contexte se construit dans
    l'ordre et s'arrête au budget : un document utile classé huitième est un
    document absent, et l'écran le compterait pourtant comme une source."""
    _a, corp = corpus
    f = R.chercher_au_fonds_cabinet(_memoire(corpus), etagere_pleine,
                                    corpus[0], corp)
    tete = [s["titre"] for s in f["sources"][:len(UTILES)]]
    assert set(tete) == set(UTILES), (
        "les documents qui répondent au CCTP ne sont pas les premiers : %s"
        % tete)


# ═══════════════════════════════════════════════════════════════════════════
#  4. CE QUI N'EST PAS DE NOUS — la barrière est dans la consigne.
# ═══════════════════════════════════════════════════════════════════════════
def _ctx(corpus, rag):
    a, corp = corpus
    r = ao_dc.remplir(fiche={"raison_sociale": "CONSEILPREV"}, analyse=a)
    piece = _memoire(corpus)
    return R.contexte(r, a, piece, socle=None,
                      dossier=R.chercher_dossier(piece, corp),
                      fonds=R.chercher_au_fonds_cabinet(piece, rag, a, corp))


def test_la_documentation_est_REPEREE_comme_n_etant_pas_de_nous(
        corpus, etagere_pleine):
    ctx = _ctx(corpus, etagere_pleine)
    assert "Guide ANSSI hygiene informatique" in ctx["fonds_documentation"]
    assert "Norme EN 50600 classes de disponibilite" in \
        ctx["fonds_documentation"]
    # ET NOS PROPRES PIÈCES N'Y SONT PAS. Interdire de citer notre propre
    # convention BIM serait aussi faux que d'autoriser à recopier une norme.
    assert "Convention BIM niveau 2 CONSEILPREV" not in \
        ctx["fonds_documentation"], ctx["fonds_documentation"]


def test_la_consigne_INTERDIT_de_reproduire_un_texte_de_tiers(
        corpus, etagere_pleine):
    """CE QUI EST EN JEU. Le brouillon RECOPIE ses extraits et part dans le
    dossier remis à un acheteur. Un paragraphe de norme EN 50600 recopié là
    est une contrefaçon — et il se repère."""
    b = R.brief(_ctx(corpus, etagere_pleine))
    assert "NE REPRODUISEZ AUCUN PASSAGE" in b
    assert "CITEZ LA RÉFÉRENCE" in b
    # ET LA CONSIGNE NOMME LESQUELS. « certains de ces documents » sans dire
    # lesquels laisserait le modèle deviner, donc se tromper dans les deux sens.
    assert "Guide ANSSI hygiene informatique" in b.split(
        "NE SONT PAS DE NOUS")[1][:400], b.split("NE SONT PAS DE NOUS")[1][:400]


def test_la_consigne_SE_TAIT_quand_aucun_document_de_tiers_n_est_joint(corpus):
    """UNE LIGNE DE PLUS DANS UNE CONSIGNE DÉJÀ LONGUE EST UNE LIGNE DE MOINS
    QU'ON LIT SUR LES AUTRES. L'interdit ne se pose que s'il y a lieu.

    LA PREMIÈRE VERSION NE MESURAIT RIEN. Son étagère ne portait qu'un
    organigramme que la recherche ne retrouvait pas : `fonds_cabinet` était
    vide, toute la section du brief était sautée, et l'interdit était donc
    absent quoi qu'on fasse. La mutation qui l'imposait sans raison a survécu.
    L'étagère porte maintenant un document QUI REMONTE — et rien qui soit d'un
    tiers.
    """
    rag = rag_store.MemoryRagStore()
    rag.ingest_bytes(
        "convention-bim.txt",
        "Notre convention BIM de niveau 2 : maquette IFC 4 remise a chaque "
        "phase, referent BIM designe parmi les intervenants cles du centre "
        "de donnees.".encode("utf-8"),
        title="Convention BIM niveau 2 CONSEILPREV",
        theme="Cabinet / Moyens matériels & techniques",
        visibility="internal")
    ctx = _ctx(corpus, rag)
    assert ctx["fonds_cabinet"], (
        "l'étagère d'essai ne remonte rien : la section du brief est sautée "
        "et cette règle ne mesure plus l'interdit")
    assert ctx["fonds_documentation"] == [], ctx["fonds_documentation"]
    assert "NE REPRODUISEZ AUCUN PASSAGE" not in R.brief(ctx)


def test_le_redacteur_DESCEND_le_corpus_jusqu_a_l_etagere():
    """LA LIGNE QUI RELIE, ET QU'AUCUNE AUTRE RÈGLE NE TOUCHE.

    `chercher_au_fonds_cabinet` peut accepter un corpus et `rediger` ne pas le
    lui passer : la recherche retomberait alors sur le domaine seul, les onze
    pièces sortiraient avec de la documentation hors sujet, et tout le reste
    des règles resterait vert — elles appellent la recherche directement."""
    src = io.open(os.path.join(ICI, "ao_redaction.py"), encoding="utf-8").read()
    corps = src.split("def rediger(", 1)[1].split("\ndef ")[0]
    m = re.search(r"chercher_au_fonds_cabinet\((.+?)\)", corps, re.S)
    assert m, corps[:900]
    assert "corpus_dossier" in m.group(1), (
        "le rédacteur n'envoie pas les documents du marché à l'étagère : la "
        "recherche retombe sur le domaine — %s" % m.group(1))


def test_les_trois_tiers_sont_DISJOINTS():
    """UN RAYON DANS DEUX TIERS SERAIT CHERCHÉ DEUX FOIS, SOUS DEUX RÈGLES DE
    PUBLICATION CONTRAIRES — et la plus permissive gagnerait, en silence."""
    n, t, d = set(R.FONDS_NOUS), set(R.FONDS_TIERS), set(R.FONDS_DOCUMENTATION)
    assert not (n & t) and not (n & d) and not (t & d), (n, t, d)


def test_la_documentation_se_lit_SANS_filtre_de_publication():
    """ET C'EST ASSUMÉ, PARCE QUE LE RISQUE EST D'UNE AUTRE NATURE. Le régime
    de publication répond à la confidentialité d'un client ; il ne donne aucun
    droit sur une norme. Exiger « publiable » aurait rendu l'étagère muette
    sur ce lot sans rien protéger."""
    src = io.open(os.path.join(ICI, "ao_redaction.py"), encoding="utf-8").read()
    corps = src.split("def chercher_au_fonds_cabinet(", 1)[1] \
               .split("\ndef ")[0]
    m = re.search(r"if doc:(.+?)\n        \S", corps, re.S)
    assert m, corps[-900:]
    assert "public_only=False" in m.group(1), m.group(1)
