# -*- coding: utf-8 -*-
"""DÉPOSER UNE FOIS, SERVIR À TOUS LES DOSSIERS SUIVANTS.

CE QUI ÉTAIT EN CAUSE. Le § 14 a deux zones de dépôt : les pièces de
l'acheteur, et les nôtres. Celles de l'acheteur changent à chaque
consultation, et c'est leur nature. Les nôtres — organigramme, CV, moyens,
certifications, références, note méthodologique — sont les MÊMES d'un dossier
à l'autre, et il fallait pourtant les redéposer à chaque fois : elles vivaient
le temps d'une page.

L'ÉTAGÈRE N'EST PAS UN SECOND MAGASIN, et c'est la décision qui commande tout
le reste. Elle EST la famille « CONSEILPREV — pièces du cabinet » de la base de
connaissance, déjà lue par `ao_extraction.chercher_au_fonds` (qui remplit) et
par `ao_redaction.chercher_au_fonds_cabinet` (qui rédige). Un troisième
magasin aurait demandé de le brancher dans les deux — et un branchement qu'on
oublie est une étagère qui a l'air pleine et ne sert à rien.

LE DÉFAUT QUE LA MESURE DE BOUT EN BOUT A ATTRAPÉ, ET QUI SERAIT PARTI SANS
ELLE. Le branchement était juste, les règles du tour précédent étaient vertes,
et l'apport réel était NUL : sur une étagère portant un organigramme, des
certifications et une note méthodologique, la recherche ramenait ZÉRO extrait.
La requête était bâtie sur ce que la pièce doit DÉMONTRER — le vocabulaire de
l'acheteur — et l'étagère parle un autre langage. Trois causes empilées, toutes
mesurées : la requête mal visée, les accents, le pluriel des noms de rayons.
De 0 à 3 sources et 1 833 caractères.
"""
import io
import os
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc                                                     # noqa: E402
import ao_extraction                                             # noqa: E402
import ao_redaction                                              # noqa: E402
import dossier_cabinet as DC                                     # noqa: E402
import rag_store                                                 # noqa: E402
import rgpd                                                      # noqa: E402
from conftest import ORIGINE                                     # noqa: E402

import pytest                                                    # noqa: E402


#: CE QU'ON RANGE DANS LES RÈGLES : de vrais documents du cabinet, dans un
#: vrai magasin. Un magasin double aurait caché exactement le défaut qu'on
#: vient de corriger — il rend tout ce qui porte le bon thème, quelle que soit
#: la requête, et la requête était précisément ce qui manquait.
ETAGERE = [
    ("organigramme-conseilprev.txt", "internal",
     u"Organigramme CONSEILPREV. L'equipe compte 14 ingenieurs dont 4 "
     u"architectes systemes industriels et 2 auditeurs ISO 27001."),
    ("certifications-qse.txt", "internal",
     u"Certifications du cabinet : ISO 9001 depuis 2019, ISO 27001 depuis "
     u"2022, qualification OPQIBI 1201 pour la maitrise d'oeuvre."),
    ("memoire-technique-methodologie.txt", "public",
     u"Note methodologique de conception : releve de l'existant, "
     u"dimensionnement thermique, redondance N+1, mise en service."),
]

RC_X = (u"REGLEMENT DE LA CONSULTATION\nAcheteur : Communaute "
        u"d'agglomeration de X.\nObjet de la consultation : maitrise d'oeuvre "
        u"pour un centre de donnees de 12 MW.\nLe candidat produit un memoire "
        u"technique et une note sur ses moyens.\n")
RC_Y = (u"REGLEMENT DE LA CONSULTATION\nAcheteur : Metropole de Y.\n"
        u"Objet de la consultation : audit de securite des systemes "
        u"industriels.\nLe candidat produit un memoire technique.\n")


def _magasin(contenu=ETAGERE):
    mag = rag_store.MemoryRagStore()
    for nom, vis, texte in contenu:
        DC.ranger(mag, nom, texte.encode("utf-8"),
                  ao_dc.piece_du_cabinet(nom), visibilite=vis)
    return mag


def _piece_memoire(rc=None):
    a = ao_dc.analyser([{"nom": "RC.pdf", "texte": rc or RC_X,
                         "extension": ".pdf"}]) if rc else None
    r = ao_dc.remplir(fiche={"raison_sociale": "CONSEILPREV"}, analyse=a)
    piece = next(p for p in ao_redaction.pieces_redigeables(r)
                 if p["cle"] == "memoire_technique")
    return piece, a


# ══════════════════════════════════════════════════════════════════════════
#  1. LE POINT DE TOUT : UN DOSSIER À L'AUTRE, SANS REDÉPOSER
# ══════════════════════════════════════════════════════════════════════════

def test_un_document_range_UNE_FOIS_sert_a_DEUX_consultations():
    """LA RÈGLE QUI PORTE LA DEMANDE. Deux acheteurs différents, deux objets
    différents, et rien de redéposé entre les deux."""
    mag = _magasin()
    vus = []
    for rc in (RC_X, RC_Y):
        piece, a = _piece_memoire(rc)
        f = ao_redaction.chercher_au_fonds_cabinet(piece, mag, a)
        vus.append({s["titre"] for s in f["sources"]})
        assert len(f["bloc"]) > 900, len(f["bloc"])
    assert vus[0] == vus[1], vus
    assert len(vus[0]) == len(ETAGERE), vus[0]
    assert DC.etagere(mag)["total"] == len(ETAGERE)


def test_l_etagere_nourrit_AUSSI_le_remplissage_des_formulaires():
    """DEUX LECTEURS, PAS UN. Si l'étagère ne servait qu'à la rédaction, elle
    laisserait les formulaires aussi vides qu'avant — et c'est le remplissage
    qu'on fait à chaque dossier."""
    cible = {"corpus_cote": "cabinet", "piece": "dc2",
             "rubriques": [{"cle": "moyens",
                            "libelle": "Moyens humains, effectifs, outillage "
                                       "et certifications"}]}
    pieces = ao_extraction.chercher_au_fonds(cible, _magasin())
    assert pieces, "le fonds ne rend rien au remplissage"
    assert all(p.get("cote") == "cabinet" for p in pieces)


def test_sans_rien_de_range_l_apport_est_NUL():
    """LE TÉMOIN NÉGATIF DE TOUT LE TOUR. Sans lui, les règles ci-dessus
    passeraient sur un module qui rend toujours quelque chose."""
    piece, a = _piece_memoire(RC_X)
    f = ao_redaction.chercher_au_fonds_cabinet(piece, _magasin([]), a)
    assert f["sources"] == [] and f["absent"] == "aucun_extrait"


# ══════════════════════════════════════════════════════════════════════════
#  2. LA REQUÊTE VISE L'ÉTAGÈRE, PAS L'ACHETEUR
# ══════════════════════════════════════════════════════════════════════════

def test_la_requete_du_fonds_N_EST_PAS_celle_du_socle():
    """LE DÉFAUT QUI SERAIT PARTI SANS MESURE DE BOUT EN BOUT.

    `requete_socle` est bâtie sur ce que la pièce doit DÉMONTRER : pour un
    mémoire technique, « une réponse point par point aux critères de jugement
    pondérés ». C'est le vocabulaire de l'ACHETEUR — juste pour le socle
    documentaire, qui est fait d'extraits de règlements, et aveugle sur une
    étagère où l'on range des organigrammes."""
    piece, _a = _piece_memoire()
    socle = ao_redaction.requete_socle(piece)
    fonds = ao_redaction.requete_fonds(piece)
    assert socle != fonds
    assert "critères de jugement" in socle
    for mot in ("organigramme", "certifications", "méthodologiques"):
        assert mot.lower() in fonds.lower(), mot


def test_la_requete_porte_les_deux_graphies_accentuees():
    """LE MAGASIN NE DÉPLIE PAS LES ACCENTS : « méthodologiques » et
    « methodologique » sont deux termes sans rapport. Or l'extraction d'un PDF
    rend souvent un texte SANS accents — et le document restait introuvable."""
    fonds = ao_redaction.requete_fonds(_piece_memoire()[0])
    assert "méthodologiques" in fonds and "methodologiques" in fonds
    assert "qualifications" in fonds.lower()


def test_la_requete_porte_aussi_le_SINGULIER():
    """MÊME CAUSE : « notes » et « note » sont deux termes. Les rayons sont
    nommés au pluriel, les documents s'intitulent au singulier."""
    fonds = ao_redaction.requete_fonds(_piece_memoire()[0])
    assert "notes" in fonds and "note " in fonds + " "


def test_la_requete_emporte_l_OBJET_de_la_consultation():
    """POUR QUE LES RÉFÉRENCES RAMENÉES SOIENT DU BON DOMAINE. Sans lui, une
    étagère bien fournie rendrait les mêmes extraits quel que soit le marché.

    CETTE RÈGLE A ATTRAPÉ UN DÉFAUT D'ORDRE. L'objet était ajouté EN DERNIER,
    après les rayons, leurs graphies sans accents et leurs formes au
    singulier — et la requête est bornée à 600 caractères. Le terme le plus
    discriminant de tous était donc le premier sacrifié par le budget."""
    piece, a = _piece_memoire(RC_X)
    q = ao_redaction.requete_fonds(piece, a)
    assert "centre de donnees" in q.lower()
    assert "centre de donnees" not in ao_redaction.requete_fonds(piece).lower()
    # ET IL SURVIT À LA COUPE : c'est tout l'objet de la correction.
    assert q.lower().index("centre de donnees") < 200, \
        "l'objet est relégué en fin de requête, là où le budget le coupe"


def test_la_requete_TIENT_dans_son_budget_sans_etre_tronquee():
    """LE DÉFAUT QUE J'AI CHASSÉ DEUX FOIS, ET QUI MÉRITE SA RÈGLE.

    La requête est bornée à 600 caractères. Première version : l'objet ajouté
    en dernier, donc coupé — le terme le plus discriminant disparaissait.
    Deuxième version : l'objet en tête, mais le vocabulaire des cinq rayons
    décliné en trois graphies derrière lui, si bien que la QUEUE était
    coupée — et les rayons « mémoires » et « références » avec elle. On
    déplaçait la troncature au lieu de la supprimer, et à chaque fois un
    document bien rangé redevenait introuvable.

    CE QUI LE RÈGLE : chaque moitié de la famille est interrogée avec SON
    vocabulaire, et les variantes ne portent que sur ce vocabulaire — pas sur
    le nom de la pièce ni sur l'objet, qu'il est inutile de décliner.

    LA RÈGLE MESURE LA MARGE, pas seulement l'absence de coupe : une requête
    à 599 caractères passerait, et se ferait tronquer au premier objet un peu
    long."""
    piece, a = _piece_memoire(RC_X)
    for lot in (ao_redaction.FONDS_NOUS, ao_redaction.FONDS_TIERS):
        q = ao_redaction.requete_fonds(piece, a, lot)
        assert len(q) < 500, \
            "la requête frôle le plafond de 600 : %d caractères" % len(q)
        # ET RIEN D'ESSENTIEL N'EST PERDU : l'objet ET le vocabulaire du lot.
        assert "centre de donnees" in q.lower()
        dernier = lot[-1].split("/", 1)[-1].split("&")[0].strip().lower()
        assert dernier.split()[0] in q.lower(), \
            "le dernier rayon du lot est tombé hors de la requête"


def test_la_requete_suit_les_rayons_et_ne_les_recopie_pas():
    """UNE TABLE DE MOTS ÉCRITE À LA MAIN SE DÉSACCORDERAIT du jour où un
    rayon change de nom — et la requête viserait un rayon qui n'existe plus,
    en silence."""
    import ao_redaction as R
    garde = R.FONDS_NOUS
    try:
        R.FONDS_NOUS = ("Cabinet / Flotte de véhicules électriques",)
        assert "véhicules" in R.requete_fonds(_piece_memoire()[0])
    finally:
        R.FONDS_NOUS = garde


# ══════════════════════════════════════════════════════════════════════════
#  3. OÙ VA CHAQUE DOCUMENT — ET CE QUI NE SE RANGE PAS
# ══════════════════════════════════════════════════════════════════════════

def test_chaque_piece_reconnue_a_une_DECISION():
    """UNE PIÈCE SANS DÉCISION SE RANGERAIT NULLE PART, en silence : le
    document serait accepté et invisible aux deux chercheurs."""
    sans = sorted(set(ao_dc.CABINET_MOTIFS)
                  - set(ao_dc.THEME_CABINET) - set(ao_dc.SANS_ETAGERE))
    assert not sans, "pièce(s) reconnue(s) sans décision d'étagère : %r" % sans


def test_tous_les_rayons_visés_existent_dans_la_famille():
    """UN RAYON MAL ORTHOGRAPHIÉ RANGE LE DOCUMENT HORS DE PORTÉE des deux
    chercheurs, et rien ne le dit : la recherche ramène simplement zéro."""
    famille = set(rag_store.themes_famille(rag_store.FAMILLE_CABINET))
    hors = sorted(set(ao_dc.THEME_CABINET.values()) - famille)
    assert not hors, hors


def test_trois_pieces_ne_se_conservent_PAS_et_disent_pourquoi():
    """UNE DPGF EST CHIFFRÉE POUR CE MARCHÉ-CI ; une déclaration sur l'honneur
    est signée pour un acheteur nommé ; un questionnaire tiers appartient à
    celui qui le fournit. Les conserver ferait proposer les prix d'un marché
    dans un autre."""
    for cle in ("dpgf", "honneur", "tiers"):
        d = DC.destination(cle)
        assert d["rayon"] == "" and d["refus"] == "ne_se_conserve_pas"
        assert len(d["dit"]) > 40, cle


def test_un_fichier_mal_nomme_est_refusé_ET_orienté():
    """« PAS RECONNU » ET « NE SE CONSERVE PAS » NE SE SOIGNENT PAS PAREIL :
    l'un demande de renommer, l'autre ne se soigne pas. Les confondre ferait
    chercher une faute de nommage là où il n'y en a pas."""
    d = DC.destination(None)
    assert d["refus"] == "piece_inconnue"
    assert "Renommez-le" in d["dit"]


def test_la_destination_est_PURE():
    """CE QUI DÉCIDE DU RAYON D'UN DOCUMENT doit se mesurer sans magasin."""
    assert DC.destination("organigramme")["rayon"] == \
        "Cabinet / Moyens humains, CV & organigramme"


# ══════════════════════════════════════════════════════════════════════════
#  4. LE PLAFOND, ET CE QU'IL DIT QUAND IL REFUSE
# ══════════════════════════════════════════════════════════════════════════

def test_l_etagere_refuse_au_dela_du_plafond_et_NOMME_ce_qu_il_y_a_dessus():
    """« QUINZE SUR QUINZE » SANS DIRE LESQUELS laisse supprimer au hasard."""
    mag = rag_store.MemoryRagStore()
    for i in range(DC.MAX_DOCUMENTS):
        DC.ranger(mag, "references-%02d.txt" % i,
                  (u"References du cabinet, lot %d, operations comparables."
                   % i).encode("utf-8"), "references")
    assert DC.etagere(mag)["places"] == 0
    with pytest.raises(DC.EtagereError) as exc:
        DC.ranger(mag, "organigramme.txt", b"Organigramme du cabinet.",
                  "organigramme")
    assert exc.value.code == "etagere_pleine" and exc.value.status == 409
    assert str(DC.MAX_DOCUMENTS) in exc.value.detail
    # CE QU'IL FAUT VRAIMENT : POUVOIR CHOISIR LEQUEL RETIRER.
    #
    # LA PREMIÈRE VERSION CHERCHAIT « references-00 », c'est-à-dire le NOM DE
    # FICHIER. Les documents se rangent désormais sous un intitulé dérivé, et
    # cette règle tombait — alors que ce qu'elle mesure était mieux servi
    # qu'avant. Elle a pourtant servi : elle a attrapé un intitulé qui rendait
    # les quinze IDENTIQUES, ce qui est aussi inutile que de ne rien nommer.
    # On mesure donc la propriété elle-même : les noms cités sont DISTINCTS.
    cites = [x.strip() for x in
             exc.value.detail.split(" : ", 1)[1].rstrip(".").split(", ")]
    assert len(cites) >= 5, cites
    assert len(set(cites)) == len(cites), (
        "le refus nomme plusieurs fois la même chose : on ne peut toujours "
        "pas choisir lequel retirer — %s" % cites)


def test_le_plafond_est_DECLARE_et_rendu_avec_l_etat():
    """UN NOMBRE EN DUR DANS UNE COMPARAISON NE SE DISCUTE PAS ; et l'écran
    doit pouvoir écrire « 3 sur 15 » sans le recopier."""
    assert 1 <= DC.MAX_DOCUMENTS <= 60
    e = DC.etagere(_magasin())
    assert e["plafond"] == DC.MAX_DOCUMENTS
    assert e["places"] == DC.MAX_DOCUMENTS - e["total"]


def test_l_etagere_ne_compte_QUE_la_famille_du_cabinet():
    """LA BASE PORTE BIEN AUTRE CHOSE — des normes, des guides, les CCTP
    d'autres consultations. Les compter ici remplirait l'étagère de documents
    qu'on n'y a jamais rangés, et le plafond refuserait le premier
    organigramme. Une mutation qui retire le filtre de famille a survécu tant
    que le magasin d'essai ne portait QUE des pièces du cabinet."""
    mag = _magasin()
    avant = DC.etagere(mag)["total"]
    mag.ingest_bytes("cctp-autre-consultation.txt",
                     u"Le titulaire fournit un PUE inferieur a 1,3.".encode("utf-8"),
                     title="CCTP d'une autre consultation",
                     theme="Data center / Appels d'offres & CCTP",
                     visibility="public")
    apres = DC.etagere(mag)
    assert apres["total"] == avant, \
        "un document hors de la famille du cabinet occupe une place"
    assert all(d["rayon"] in DC.rayons() for d in apres["documents"])


def test_sans_magasin_l_etagere_est_vide_ET_NOMMEE():
    """« ZÉRO DOCUMENT » ET « BASE NON JOINTE » NE SE LISENT PAS PAREIL : le
    premier se lit « vous n'avez rien rangé »."""
    e = DC.etagere(None)
    assert e["total"] == 0 and e["absent"] == "magasin_non_joint"


def test_sans_magasin_du_tout_on_ne_range_pas():
    with pytest.raises(DC.EtagereError) as exc:
        DC.ranger(None, "organigramme.txt", b"x", "organigramme")
    assert exc.value.code == "magasin_absent"


def test_on_ne_range_PAS_dans_une_etagere_qu_on_ne_voit_pas():
    """LE CAS QUE LA RÈGLE PRÉCÉDENTE NE TOUCHE PAS, et une mutation l'a dit.

    « Pas de magasin » est arrêté par la toute première garde. Le cas qui
    compte vraiment est le magasin PRÉSENT dont la lecture échoue : sans ce
    second refus, on rangerait sans connaître le plafond — donc sans plafond,
    et l'étagère grossirait en silence."""
    class Muet(object):
        def list_documents(self, limit=200, offset=0):
            raise RuntimeError("base injoignable")

        def ingest_bytes(self, *a, **k):        # pragma: no cover
            raise AssertionError("on a rangé dans une étagère illisible")

    mag = Muet()
    assert DC.etagere(mag)["absent"] == "base_injoignable"
    with pytest.raises(DC.EtagereError) as exc:
        DC.ranger(mag, "organigramme.txt", b"Organigramme.", "organigramme")
    assert exc.value.code == "etagere_illisible" and exc.value.status == 503


# ══════════════════════════════════════════════════════════════════════════
#  5. LE RÉGIME DE PUBLICATION — UN CHOIX, JAMAIS UN DÉFAUT MUET
# ══════════════════════════════════════════════════════════════════════════

def test_le_defaut_est_INTERNE_et_c_est_le_sens_prudent():
    """SE TROMPER VERS L'INTERNE coûte un brouillon plus maigre ; se tromper
    vers le publiable peut envoyer l'architecture d'un client chez un autre.
    Des deux erreurs, une seule se rattrape."""
    assert DC.VISIBILITE_DEFAUT == "internal"
    assert set(DC.VISIBILITES) == {"internal", "public"}
    for v in DC.VISIBILITES.values():
        assert v["nom"] and len(v["dit"]) > 40


def test_un_memoire_INTERNE_ne_nourrit_PAS_les_brouillons():
    """C'EST LA BARRIÈRE DE `ao_redaction`, VUE DEPUIS L'ÉTAGÈRE. La colonne
    de l'écran doit dire la même chose que le rédacteur fera."""
    mag = rag_store.MemoryRagStore()
    DC.ranger(mag, "memoire-client-A.txt",
              u"Architecture retenue chez le client A.".encode("utf-8"),
              "memoire_technique", visibilite="internal")
    ligne = DC.etagere(mag)["documents"][0]
    assert ligne["nourrit_les_brouillons"] is False
    piece, a = _piece_memoire(RC_X)
    f = ao_redaction.chercher_au_fonds_cabinet(piece, mag, a)
    assert f["sources"] == [], "un mémoire interne a atteint la rédaction"


def test_nos_moyens_nourrissent_les_brouillons_MEME_internes():
    """UN ORGANIGRAMME NE DÉCRIT AUCUN TIERS. Exiger « publiable » l'aurait
    rendu illisible — et c'est précisément ce qu'on range en interne et qu'on
    remet pourtant à chaque candidature."""
    mag = rag_store.MemoryRagStore()
    DC.ranger(mag, "organigramme.txt",
              u"Organigramme CONSEILPREV : 14 ingenieurs.".encode("utf-8"),
              "organigramme", visibilite="internal")
    assert DC.etagere(mag)["documents"][0]["nourrit_les_brouillons"] is True


def test_la_colonne_LIT_la_regle_de_ao_redaction_au_lieu_de_la_recopier():
    """DEUX TABLES DES MÊMES RAYONS AURAIENT DIVERGÉ, et la divergence se
    serait vue comme une colonne qui promet un apport que le rédacteur
    refuse."""
    garde = ao_redaction.FONDS_NOUS
    try:
        ao_redaction.FONDS_NOUS = ()
        assert DC._nourrit("Cabinet / Moyens humains, CV & organigramme",
                           "internal") is False
    finally:
        ao_redaction.FONDS_NOUS = garde
    assert DC._nourrit("Cabinet / Moyens humains, CV & organigramme",
                       "internal") is True


def test_un_regime_inconnu_est_refusé():
    with pytest.raises(DC.EtagereError) as exc:
        DC.ranger(_magasin([]), "organigramme.txt", b"x", "organigramme",
                  visibilite="secret")
    assert exc.value.code == "visibilite_inconnue"


# ══════════════════════════════════════════════════════════════════════════
#  6. LA ROUTE
# ══════════════════════════════════════════════════════════════════════════

def _poser(cl, nom, texte, vis="internal"):
    return cl.post("/api/datacenter/marche/cabinet",
                   data={"file": (io.BytesIO(texte.encode("utf-8")), nom),
                         "visibilite": vis},
                   content_type="multipart/form-data", headers=ORIGINE)


def test_la_route_range_et_rend_le_rayon(marche):
    r = _poser(marche, "organigramme-conseilprev.txt",
               u"Organigramme CONSEILPREV : 14 ingenieurs.")
    assert r.status_code == 200, r.data[:300]
    j = r.get_json()
    assert j["rayon"] == "Cabinet / Moyens humains, CV & organigramme"
    assert j["nourrit_les_brouillons"] is True
    assert j["etagere"]["total"] >= 1


def test_la_route_REFUSE_ce_qui_ne_se_conserve_pas_et_dit_pourquoi(marche):
    r = _poser(marche, "dpgf-lot-2.txt", u"Decomposition du prix global.")
    assert r.status_code == 400
    j = r.get_json()
    assert j["error"] == "ne_se_conserve_pas"
    assert "CETTE consultation" in j["message"]


def test_la_route_REFUSE_un_fichier_mal_nomme(marche):
    r = _poser(marche, "scan0012.txt", u"Un document quelconque.")
    assert r.status_code == 400
    assert r.get_json()["error"] == "piece_inconnue"


def test_la_route_rend_l_etagere_et_les_deux_regimes(marche):
    j = marche.get("/api/datacenter/marche/cabinet").get_json()
    assert j["ok"] and "etagere" in j
    assert set(j["visibilites"]) == {"internal", "public"}
    assert j["defaut"] == "internal"
    assert j["etagere"]["plafond"] == DC.MAX_DOCUMENTS


def test_la_piece_est_DEDUITE_du_nom_et_jamais_recue_de_la_page(marche):
    """UNE CLÉ TRANSMISE PAR LE NAVIGATEUR serait une clé qu'on peut se
    tromper en recopiant — et un mauvais rayon rend le document invisible aux
    deux chercheurs. Envoyer une clé ne doit donc RIEN changer."""
    r = marche.post("/api/datacenter/marche/cabinet",
                    data={"file": (io.BytesIO(b"Organigramme du cabinet."),
                                   "organigramme-x.txt"),
                          "piece": "memoire_technique", "cle": "references"},
                    content_type="multipart/form-data", headers=ORIGINE)
    assert r.status_code == 200
    assert r.get_json()["rayon"] == "Cabinet / Moyens humains, CV & organigramme"


def test_la_route_est_cadencee_et_admise_aux_gros_corps():
    """ELLE ÉCRIT DANS LA BASE DE CONNAISSANCE, comme l'envoi d'un document :
    même cadence, même exemption de taille."""
    src = io.open(os.path.join(ICI, "app.py"), encoding="utf-8").read()
    assert '"/api/datacenter/marche/cabinet": (20, 60)' in src
    i = src.index("_LARGE_BODY_PATHS")
    assert "/api/datacenter/marche/cabinet" in src[i:i + 400]


def test_le_journal_porte_le_rayon_ET_le_regime():
    """C'EST LE RÉGIME QUI DÉCIDE si ce document partira un jour chez un
    acheteur, et c'est la seule trace qu'on aura de la décision."""
    src = io.open(os.path.join(ICI, "app.py"), encoding="utf-8").read()
    i = src.index("marche.cabinet.ranger")
    assert "rayon=%s visibilite=%s" in src[i:i + 300]


# ══════════════════════════════════════════════════════════════════════════
#  7. LA PAGE, ET LE REGISTRE
# ══════════════════════════════════════════════════════════════════════════

def _js():
    return io.open(os.path.join(ICI, "ingenierie-dc.js"), encoding="utf-8").read()


def test_le_geste_n_est_offert_QUE_du_cote_cabinet():
    """LES PIÈCES DE L'ACHETEUR CHANGENT À CHAQUE CONSULTATION. Les ranger sur
    une étagère qui sert aux dossiers SUIVANTS ferait proposer le CCTP d'un
    marché dans un autre."""
    js = _js()
    i = js.index("aoEtagereGeste(")
    bloc = js[max(0, i - 400):i + 120]
    assert 'c[0] === "cabinet"' in bloc


def test_la_page_ne_range_que_les_fichiers_du_cote_cabinet():
    js = _js()
    i = js.index("var aRanger")
    bloc = js[i:i + 400]
    assert 'd.cote === "cabinet"' in bloc


def test_le_rangement_suit_l_analyse_et_ne_la_fait_pas_echouer():
    """RANGER D'ABORD ferait garder un document que l'analyse aurait ensuite
    refusé ; et un refus de rangement ne doit pas faire échouer une analyse
    qui, elle, a réussi.

    LA PREMIÈRE VERSION COMPARAIT DEUX `index` DE CHAÎNES, et une mutation
    remplaçant la garde `if (aRanger.length)` par `if (false)` a survécu : le
    texte restait au même endroit, seul son effet disparaissait. On lit donc
    la GARDE, pas seulement l'ordre."""
    js = _js()
    assert js.index("AO_ANALYSE = j.analyse") < js.index("aoEtagereBilan(aRanger")
    i = js.index("aoEtagereBilan(aRanger")
    assert "if (aRanger.length)" in js[i - 60:i], \
        "le rangement n'est plus conditionné à ce qu'il y ait à ranger"


def _node_ranger(reponses):
    """`aoEtagereRanger` EXÉCUTÉE, avec un faux `demander`.

    POURQUOI EXÉCUTER. La première version de cette règle cherchait
    `rates.push({nom: f.name` dans la source. Or il y en a DEUX — la branche
    du refus serveur et celle de la panne réseau — et la règle ne pouvait pas
    dire laquelle elle mesurait : une mutation vidant la première a survécu
    parce que la seconde satisfaisait encore la recherche."""
    import json as _json
    import subprocess
    src = _js()
    i = src.index("\n  function aoEtagereRanger(")
    p_, k = 1, src.index("{", i) + 1
    while p_:
        p_ += 1 if src[k] == "{" else (-1 if src[k] == "}" else 0)
        k += 1
    prog = src[i:k] + """
    var REPONSES = JSON.parse(process.env.REP);
    var n = 0;
    function $(){ return null; }
    function aoEtagereEtat(){}
    function demander() {
      var r = REPONSES[n++];
      if (r.reseau) return Promise.reject(new Error(r.reseau));
      return Promise.resolve({json: function(){ return Promise.resolve(r); }});
    }
    var fichiers = REPONSES.map(function (_r, i) {
      return {name: "fichier-" + i + ".txt"}; });
    aoEtagereRanger(fichiers, "internal").then(function (b) {
      process.stdout.write(JSON.stringify(b));
    });
    """
    out = subprocess.run(["/opt/node22/bin/node"], input=prog,
                         capture_output=True, text=True, timeout=60,
                         env=dict(os.environ, REP=_json.dumps(reponses)))
    assert out.returncode == 0, out.stderr[-1500:]
    return _json.loads(out.stdout)


def test_chaque_refus_de_rangement_porte_SON_nom_et_SON_motif():
    """« 2 SUR 5 RANGÉS » LAISSE CHERCHER lesquels et pourquoi. Trois issues,
    trois lignes : rangé, refusé par le serveur avec son motif, et coupé par
    le réseau — que l'on ne doit pas confondre avec un refus."""
    b = _node_ranger([
        {"ok": True, "rayon": "Cabinet / Moyens humains, CV & organigramme"},
        {"ok": False, "message": "Ce fichier n'est rattaché à aucune pièce."},
        {"reseau": "connexion interrompue"},
    ])
    assert [x["nom"] for x in b["ranges"]] == ["fichier-0.txt"]
    assert b["ranges"][0]["rayon"].startswith("Cabinet / ")
    assert [x["nom"] for x in b["refuses"]] == ["fichier-1.txt",
                                                "fichier-2.txt"]
    assert "rattaché à aucune pièce" in b["refuses"][0]["dit"], \
        "le motif rendu par le serveur est perdu"
    assert b["refuses"][1]["dit"], "une panne réseau ressort sans motif"


def test_les_documents_sont_ranges_UN_PAR_UN():
    """UN ENVOI GROUPÉ RENDRAIT UN SEUL VERDICT pour cinq documents : on ne
    saurait pas lequel a été refusé, ni pourquoi. La règle le mesure par le
    nombre de verdicts rendus, pas par la forme de l'envoi."""
    b = _node_ranger([{"ok": True, "rayon": "Cabinet / Assurances"}] * 4)
    assert len(b["ranges"]) == 4 and b["refuses"] == []


def test_l_ecran_montre_ce_qui_est_deja_range():
    """UNE ÉTAGÈRE DONT ON NE VOIT PAS LE CONTENU SE REMPLIT DE DOUBLONS."""
    js = _js()
    i = js.index("function aoEtagereEtat")
    bloc = js[i:i + 1200]
    assert "place(s) libre(s)" in bloc and "nourrissent les brouillons" in bloc


def test_l_ecran_dit_ce_que_chaque_regime_coute():
    """LE CHOIX DÉCIDE SI LE DOCUMENT PARTIRA CHEZ UN ACHETEUR. Un menu qui ne
    dit pas ce qu'il engage est un menu qu'on règle au hasard."""
    js = _js()
    i = js.index("function aoEtagereBrancher")
    bloc = js[i:i + 1400]
    assert "confidentialité d'un client" in bloc
    assert "JAMAIS dans un brouillon" in bloc


def test_l_etagere_est_DECLAREE_au_registre_RGPD():
    """ON CONSERVE DURABLEMENT DES DOCUMENTS DONT CERTAINS NOMMENT DES
    PERSONNES — un CV, un organigramme. Le traitement est réel, même si le
    « client » est nous."""
    e = next((x for x in rgpd.REGISTRE if x["id"] == "etagere-cabinet"), None)
    assert e is not None, "l'étagère n'est pas au registre"
    assert "CV" in e["donnees"]
    assert "ACHETEUR" in e["destinataires"]
    assert str(DC.MAX_DOCUMENTS) in e["duree"] or "quinze" in e["duree"]
    assert "interne" in e["securite"]
