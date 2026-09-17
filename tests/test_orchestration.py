# -*- coding: utf-8 -*-
"""LES PATRONS AGENTIQUES — ce que ces règles MESURENT.

CE FICHIER N'EST PAS `test_orchestrateur_livrables.py`, ET CE N'EST PAS UN
DÉTAIL. Celui-là garde `orchestrateur_livrables`, qui ROUTE un sujet vers ses
thèmes. Celui-ci garde `orchestration`, qui CONDUIT les tours : planifier,
chercher par point, relire, recommencer sur ce qui manque. Deux modules, deux
fichiers, et le nom de chacun dit lequel.

LA DISCIPLINE QUE CES RÈGLES SUIVENT. Aucune ne vérifie « la boucle tourne » :
une boucle qui tourne sans rien améliorer est exactement le défaut que ce
module prétend corriger, et une règle qui se contenterait de la voir tourner
passerait pour une raison sans rapport avec ce qu'elle prétend. Chaque règle
compare donc un AVANT à un APRÈS, sur le même fonds.
"""
import pytest

import orchestration as O
import ingenierie_dc as I
import livrables
import rag_store


# ═══════════════════════════════════════════════════════════════════════════
#  LE FONDS D'ESSAI — douze documents, écrits pour cette mesure
# ═══════════════════════════════════════════════════════════════════════════
#
# AUCUN N'EST RECOPIÉ D'UNE SOURCE TIERCE, et leur contenu est choisi pour que
# la mesure soit DÉCIDABLE : on sait, en les écrivant, lequel répond à quel
# point du plan. Sans cela, « la recherche par point trouve plus » ne serait
# qu'un compte, et non une démonstration.

CORPUS = [
    ("Note methodologique conception.txt", "Cabinet / Mémoires & notes", "public",
     "Note methodologique de conception. Le contexte du projet est etabli avec "
     "la maitrise d'ouvrage. Le perimetre couvre les locaux techniques."),
    ("Cartographie zones conduits.txt", "ANSSI / Référentiels & qualification", "public",
     "Methode de cartographie des zones et conduits. Le decoupage en zones "
     "regroupe les equipements partageant un besoin de securite."),
    ("Niveaux SL cibles.txt", "ANSSI / Référentiels & qualification", "public",
     "Determination des niveaux de securite cibles SL-T. Les niveaux SL vont "
     "de 1 a 4."),
    ("Grille ecarts constates.txt", "Cabinet / Mémoires & notes", "public",
     "Grille de releve des ecarts constates. Chaque ecart constate est cote en "
     "gravite et en effort."),
    ("Priorisation recommandations.txt", "Cabinet / Mémoires & notes", "public",
     "Priorisation des recommandations. Les recommandations priorisees sont "
     "classees par le rapport gain sur effort."),
    ("Plan de reprise.txt", "Data center / Réalisation & gouvernance de projet", "public",
     "Plan de reprise d'activite. Les prochaines etapes apres validation sont "
     "l'essai a blanc puis l'essai en charge."),
]

#: CE QUE LA REQUÊTE UNIQUE NE VOIT PAS, nommé document par document.
#
# POURQUOI LES NOMMER PLUTÔT QUE LES COMPTER. Une règle qui affirme « la
# recherche par point atteint plus de documents » passe encore le jour où elle
# en atteint d'autres, au hasard. Nommer ceux-là force la règle à tomber si le
# gain change de nature — et ce sont précisément les deux qui répondent aux
# deux dernières sections du plan, celles que le budget de la requête unique
# sacrifiait.
RATTRAPES = ("Priorisation recommandations", "Plan de reprise")

TYPE = "synthese-62443"
SUJET = "Centre de données"


@pytest.fixture
def fonds():
    st = rag_store.MemoryRagStore()
    for nom, theme, vis, texte in CORPUS:
        st.ingest_bytes(nom, texte.encode("utf-8"), title=nom[:-4],
                        theme=theme, visibility=vis)
    return st


def _chercheur(store, mouchard=None):
    def chercher(requete, k, public_only):
        if mouchard is not None:
            mouchard.append({"requete": requete, "k": k,
                             "public_only": public_only})
        return store.search(requete, k=k, public_only=public_only)
    return chercher


def _titres(hits):
    return {h.get("title") for h in hits}


# ═══════════════════════════════════════════════════════════════════════════
#  1. LE GAIN — ET IL SE MESURE CONTRE LE CODE D'AVANT, PAS DANS L'ABSOLU
# ═══════════════════════════════════════════════════════════════════════════

def test_la_recherche_par_point_atteint_des_documents_que_la_requete_unique_NE_VOIT_PAS(fonds):
    """LA RÈGLE QUI PORTE LE MODULE.

    Elle n'exécute pas « l'ancien code » de mémoire : elle appelle
    `livrables.retrieval_query`, qui EST la requête que la plateforme composait
    — et compose encore pour les chemins qui n'ont pas de plan.
    """
    q = livrables.retrieval_query(TYPE, {"secteur": SUJET})
    avant = _titres(fonds.search(q, k=8, public_only=True))

    plan = O.plan_du_livrable(TYPE)
    apres = _titres(O.documenter(plan, _chercheur(fonds), sujet=SUJET)["extraits"])

    # LE SURENSEMBLE STRICT, et pas seulement « plus grand ».
    assert avant - apres == set(), \
        "la recherche par point a PERDU des documents : %s" % (avant - apres)
    assert len(apres) > len(avant)
    # ET LES DOCUMENTS RATTRAPÉS SONT CEUX QU'ON ATTENDAIT.
    for titre in RATTRAPES:
        assert titre not in avant, \
            "« %s » n'est plus rattrapé : la requête unique le voit déjà, " \
            "cette mesure ne prouve plus rien" % titre
        assert titre in apres, "« %s » n'est pas rattrapé" % titre


def test_chaque_point_du_plan_recoit_SON_appui_et_pas_un_paquet_en_vrac(fonds):
    """CE QUI DISTINGUE UNE RECHERCHE PAR POINT D'UNE RECHERCHE PLUS LARGE.

    Ramener plus d'extraits ne sert à rien si l'on ne sait pas lequel appuie
    quoi : c'est le rapprochement que le rédacteur refaisait de tête. La règle
    exige donc l'ATTRIBUTION, pas le volume.
    """
    plan = O.plan_du_livrable(TYPE)
    d = O.documenter(plan, _chercheur(fonds), sujet=SUJET)
    attendus = {
        "Écarts constatés": "Grille ecarts constates",
        "Recommandations priorisées": "Priorisation recommandations",
        "Prochaines étapes": "Plan de reprise",
        "Cartographie zones & conduits": "Cartographie zones conduits",
    }
    par_point = {q["point"]: {x["titre"] for x in q["documents"]}
                 for q in d["points"]}
    for point, doc in attendus.items():
        assert point in par_point, "le plan a perdu le point « %s »" % point
        assert doc in par_point[point], \
            "« %s » n'est pas attribué à « %s » (il a : %s)" \
            % (doc, point, par_point[point])


def test_un_seul_document_peut_appuyer_PLUSIEURS_points():
    """LE DÉFAUT QUE CETTE RÈGLE A FAIT TOMBER, ET QUI ÉTAIT LE MIEN.

    Un dédoublonnage GLOBAL attribuait une note méthodologique au premier
    point qu'elle touchait, et déclarait les autres « à écrire ». Le document
    annonçait alors au client qu'il lui manquait une matière qu'il possède —
    la pire façon de se tromper, puisqu'elle le fait travailler pour rien.
    """
    plan = O.planifier(["Le contexte", "Les moyens", "Les suites"])
    unique = [{"doc_id": "d1", "title": "Note unique", "content": "une note",
               "score": 0.9}]
    d = O.documenter(plan, lambda r, k, po: list(unique))
    assert d["resume"]["couverts"] == 3, \
        "un document qui répond aux trois points n'en couvre que %d" \
        % d["resume"]["couverts"]
    assert d["resume"]["a_ecrire"] == 0


# ═══════════════════════════════════════════════════════════════════════════
#  2. LA FRONTIÈRE QUE LA BOUCLE NE FRANCHIT PAS
# ═══════════════════════════════════════════════════════════════════════════
#
# POURQUOI CES DEUX RÈGLES EXISTENT. « La boucle élargit la recherche quand
# elle ne trouve rien » est la forme la plus naturelle, la plus serviable — et
# ici, la forme exacte que prendrait la fuite : les extraits sont reproduits
# MOT POUR MOT dans un document qui sort du site. Un document interne rattrapé
# par obligeance serait recopié dans un livrable remis au client.

def test_aucun_tour_de_boucle_n_elargit_la_visibilite(fonds):
    """Le mouchard compte : toutes les recherches, TOUS LES TOURS.

    LE PLAN EST CHOISI POUR QU'IL Y AIT UN SECOND TOUR, et cette précaution
    n'est pas cosmétique : la première version de cette règle prenait deux
    points introuvables, l'arrêt sur stagnation coupait après un seul tour, et
    elle ne mesurait donc RIEN des relances — c'est-à-dire précisément du
    moment où une boucle serviable serait tentée d'ouvrir la visibilité.
    On mêle donc un point que le fonds documente — qui empêche la stagnation —
    à un point qu'il ignore, qui sera relancé.
    """
    mouchard = []
    plan = O.planifier(["Cartographie zones conduits",       # trouvable
                        "Sujet absent de ce fonds zzz"])     # jamais trouvé
    O.documenter(plan, _chercheur(fonds, mouchard), public_only=True)
    assert mouchard, "aucune recherche n'a été lancée — la règle ne mesure rien"
    assert len(mouchard) > len(plan), \
        "un seul tour (%d recherches pour %d points) : la règle ne mesure " \
        "pas ce que font les RELANCES" % (len(mouchard), len(plan))
    assert all(a["public_only"] is True for a in mouchard), \
        "une recherche a élargi la visibilité : %s" \
        % [a for a in mouchard if a["public_only"] is not True]


def test_un_document_INTERNE_qui_repondrait_au_plan_reste_hors_du_livrable(fonds):
    """Et le contrôle qui prouve que la mesure n'est pas vide."""
    fonds.ingest_bytes(
        "Secret client.txt",
        "Ecarts constates chez le client Alpha : mot de passe par defaut. "
        "Recommandations priorisees internes. Prochaines etapes "
        "confidentielles.".encode("utf-8"),
        title="Secret client", theme="Études de cas", visibility="internal")
    plan = O.plan_du_livrable(TYPE)

    ferme = _titres(O.documenter(plan, _chercheur(fonds),
                                 sujet=SUJET, public_only=True)["extraits"])
    assert "Secret client" not in ferme, "le document interne a fuité"

    # SANS CE CONTRÔLE, LA RÈGLE PASSERAIT AUSSI SI LE DOCUMENT ÉTAIT
    # SIMPLEMENT INTROUVABLE — c'est-à-dire pour une raison sans rapport avec
    # la confidentialité, qui est ce qu'elle prétend garder.
    ouvert = _titres(O.documenter(plan, _chercheur(fonds),
                                  sujet=SUJET, public_only=False)["extraits"])
    assert "Secret client" in ouvert, \
        "le document interne est introuvable même sans filtre : cette règle " \
        "ne prouve rien sur la confidentialité"


# ═══════════════════════════════════════════════════════════════════════════
#  3. LA TERMINAISON — ET LA BORNE N'EN EST PAS LA PREUVE
# ═══════════════════════════════════════════════════════════════════════════

def test_une_base_muette_arrete_la_boucle_AVANT_la_borne():
    """Sans cette règle, une base sans réponse ferait payer trois tours à
    chaque document produit, pour rien."""
    appels = []

    def muette(requete, k, public_only):
        appels.append(requete)
        return []

    plan = O.planifier(["Alpha beta", "Gamma delta", "Epsilon zeta"])
    O.documenter(plan, muette, tours_max=O.TOURS_MAX)
    # UN SEUL TOUR : trois points interrogés une fois, puis la stagnation
    # arrête. Trois tours pleins en feraient neuf.
    assert len(appels) == len(plan), \
        "%d recherches pour %d points : la boucle n'a pas vu la stagnation" \
        % (len(appels), len(plan))


def test_la_stagnation_est_une_fonction_NOMMEE_et_pas_une_condition_noyee():
    """Une mutation qui neutralise l'arrêt doit faire tomber une règle qui le
    NOMME — sinon elle passerait pour un simple ajustement de borne."""
    assert O._stagnation(3, 3) is True, "un tour sans nouveauté doit arrêter"
    assert O._stagnation(4, 3) is False, "un tour qui apporte doit continuer"


def test_un_critique_qui_refuse_TOUJOURS_ne_fait_pas_boucler_indefiniment(fonds):
    """LE CAS PATHOLOGIQUE, et c'est celui qui compte : le critique n'est pas
    garanti raisonnable, et la boucle ne doit pas dépendre de sa bonne foi."""
    tours = []

    def rediger(plan, documentation, verdict, tour):
        tours.append(tour)
        return ""       # un texte vide : AUCUN point ne sera jamais couvert

    r = O.conduire(O.plan_du_livrable(TYPE), _chercheur(fonds), rediger,
                   sujet=SUJET, tours_max=O.TOURS_MAX)
    assert len(tours) <= O.TOURS_MAX, \
        "la boucle a fait %d tours pour une borne de %d" % (len(tours), O.TOURS_MAX)
    assert r["raison_arret"] in ("tours_max", "rien_de_plus_dans_la_base")


def test_la_boucle_garde_le_MEILLEUR_tour_et_pas_le_dernier(fonds):
    """Un tour peut rendre moins bien que le précédent. Garder le dernier
    ferait de la boucle un pari.

    ═══ POURQUOI LE PREMIER TOUR EST BON MAIS INCOMPLET ══════════════════
    La première version de cette règle rendait au tour 0 un texte couvrant
    TOUT le plan. La boucle s'arrêtait donc là — « plan couvert » — et le
    tour 1 n'existait jamais : une mutation qui remplaçait « garder le
    meilleur » par « garder le dernier » SURVIVAIT, puisqu'il n'y avait
    qu'un tour et que le dernier était le meilleur. La règle passait pour
    une raison sans rapport avec ce qu'elle prétend garder.

    Le tour 0 couvre donc le premier point SEULEMENT : la boucle continue,
    le tour 1 rend un texte vide, et l'on peut enfin mesurer lequel est
    conservé.
    """
    plan = O.plan_du_livrable(TYPE)[:2]
    partiel = "## %s\n%s" % (plan[0]["intitule"], "x" * 400)
    rendus = []

    def capricieux(plan_, documentation, verdict, tour):
        rendus.append(tour)
        return partiel if tour == 0 else "## Rien du tout\nvide"

    r = O.conduire(plan, _chercheur(fonds), capricieux, sujet=SUJET,
                   tours_max=3)
    assert len(rendus) >= 2, \
        "la boucle n'a fait qu'un tour : la règle ne mesure PAS le choix " \
        "entre deux tours"
    assert r["verdict"]["couverts"] == 1
    assert r["markdown"] == partiel, \
        "la boucle a gardé le tour le plus pauvre (%r)" % r["markdown"][:60]


# ═══════════════════════════════════════════════════════════════════════════
#  4. « LA BASE N'A RIEN » N'EST PAS « ON N'A PAS PU DEMANDER »
# ═══════════════════════════════════════════════════════════════════════════

def test_une_base_INJOIGNABLE_rend_inconnu_et_jamais_a_ecrire():
    """Dire au client que son fonds ne documente pas un point, alors que la
    recherche a échoué, le fait réécrire ce qu'il possède déjà."""
    def cassee(requete, k, public_only):
        raise RuntimeError("base injoignable")

    plan = O.planifier(["Alpha", "Beta"])
    d = O.documenter(plan, cassee)
    assert d["resume"] == {"total": 2, "couverts": 0, "a_ecrire": 0,
                           "inconnus": 2}
    assert "INDÉTERMINÉE" in d["lecture"]

    # ET LA BASE MUETTE, ELLE, DIT BIEN « À ÉCRIRE ». Sans ce second volet, la
    # règle passerait pour un module qui répondrait « inconnu » à tout.
    muette = O.documenter(plan, lambda r, k, po: [])
    assert muette["resume"]["a_ecrire"] == 2
    assert muette["resume"]["inconnus"] == 0


def test_le_brief_de_la_piece_ne_confond_pas_les_deux(monkeypatch):
    """La consigne au modèle doit distinguer les deux, sinon il traite un
    point « qu'on n'a pas pu chercher » comme un point vide."""
    import ao_redaction as R
    piece = {"cle": "x", "nom": "Lettre de candidature", "bloquante": False,
             "contient": ["Le point vide", "Le point incertain"]}
    couv = {"points": [{"point": "Le point vide", "etat": "a_ecrire"},
                       {"point": "Le point incertain", "etat": "inconnu"}]}
    ctx = R.contexte({"pieces": [piece]}, None, piece, couverture=couv)
    assert ctx["points_sans_appui"] == ["Le point vide"]
    assert ctx["points_indetermines"] == ["Le point incertain"]
    b = R.brief(ctx)
    assert "Le point vide" in b and "n'a rien rendu" in b
    assert "Le point incertain" in b and "pas pu être interrogé" in b.replace(
        "PAS PU ÊTRE INTERROGÉ", "pas pu être interrogé")


# ═══════════════════════════════════════════════════════════════════════════
#  5. UNE SEULE GRAMMAIRE, DEUX PRODUCTEURS — LA RÈGLE ANTI-DOUBLON
# ═══════════════════════════════════════════════════════════════════════════
#
# CE QU'ELLE EMPÊCHE. `ingenierie_dc` sait déjà servir les extraits par tours,
# nommer les trous au rédacteur et rendre l'annexe. Un module qui réécrirait
# ces trois-là aurait deux vérités à maintenir, et la seconde divergerait en
# silence. Ces règles mesurent que la sortie de `orchestration` NOURRIT
# réellement les fonctions de `ingenierie_dc` — pas qu'elle leur ressemble.

@pytest.mark.parametrize("fonction", ["couverture_markdown",
                                      "extraits_pour_redaction"])
def test_les_fonctions_de_ingenierie_dc_s_appliquent_TELLES_QUELLES(fonds, fonction):
    """Sur un fonds qui COUVRE tout : ces deux-là doivent rendre du texte."""
    d = O.documenter(O.plan_du_livrable(TYPE), _chercheur(fonds), sujet=SUJET)
    assert d["resume"]["couverts"] == d["resume"]["total"], \
        "ce fonds ne couvre plus tout : la règle ne mesure plus ce qu'elle dit"
    sortie = getattr(I, fonction)(d)
    assert sortie, "« %s » ne rend rien sur la sortie de orchestration" % fonction


def test_consigne_manques_de_ingenierie_dc_NOMME_les_points_que_ce_module_declare(fonds):
    """CELLE-CI SE MESURE SUR UN FONDS QUI A DES TROUS, et c'est tout l'objet.

    La première version la prenait dans la même paramétrisation que les deux
    autres, sur un fonds qui couvre les six points : elle rendait la chaîne
    vide — ce qui est le comportement JUSTE — et la règle tombait en accusant
    le module. Une consigne de manques se mesure là où il y a des manques.
    """
    plan = O.planifier(["Cartographie zones conduits",       # trouvable
                        "Sujet totalement absent zzz"])      # jamais trouvé
    d = O.documenter(plan, _chercheur(fonds))
    assert d["resume"]["a_ecrire"] == 1, \
        "le fonds d'essai ne laisse plus exactement un trou : %s" % d["resume"]
    consigne = I.consigne_manques(d)
    assert "Sujet totalement absent zzz" in consigne
    assert "Cartographie zones conduits" not in consigne, \
        "un point COUVERT est nommé comme un manque"


def test_l_annexe_NOMME_les_documents_de_chaque_point(fonds):
    """Le rendu partagé doit vraiment recevoir de quoi écrire, pas une coquille."""
    d = O.documenter(O.plan_du_livrable(TYPE), _chercheur(fonds), sujet=SUJET)
    md = I.couverture_markdown(d)
    for titre in RATTRAPES:
        assert titre in md, "« %s » manque à l'annexe" % titre


def test_la_consigne_des_manques_se_TAIT_quand_tout_est_appuye():
    """Une consigne qui s'affiche toujours cesse d'être lue."""
    plan = O.planifier(["Alpha", "Beta"])
    tout = O.documenter(plan, lambda r, k, po: [
        {"doc_id": "d1", "title": "T", "content": "c", "score": 1.0}])
    assert I.consigne_manques(tout) == ""


# ═══════════════════════════════════════════════════════════════════════════
#  6. LE CRITIQUE — IL DOIT VOIR LE MINCE, PAS SEULEMENT L'ABSENT
# ═══════════════════════════════════════════════════════════════════════════

def test_une_section_MINCE_est_relevee_et_pas_seulement_une_section_absente():
    """« Mince » est le cas qui passait : une section présente, bien tournée,
    de trois lignes, sous un titre qui promettait une analyse."""
    plan = O.planifier(["Le contexte", "Les ecarts", "Les suites"])
    texte = ("## Le contexte\n" + "x" * 500
             + "\n\n## Les ecarts\ncourt.\n\n")   # « Les suites » : absente
    v = O.critiquer(plan, texte)
    etats = {p["intitule"]: p["etat"] for p in v["points"]}
    assert etats["Le contexte"] == "couvert"
    assert etats["Les ecarts"] == "mince"
    assert etats["Les suites"] == "absent"
    assert v["couverts"] == 1


def test_le_critique_apparie_un_titre_REFORMULE():
    """Le rédacteur reformule. Un appariement exact déclarerait « absent »
    toute section correctement écrite — un critique qui crie sur tout est un
    critique qu'on éteint."""
    plan = O.planifier(["Écarts constatés"])
    v = O.critiquer(plan, "## 4. Les écarts constatés sur site\n" + "x" * 400)
    assert v["points"][0]["etat"] == "couvert"


def test_la_marque_posee_par_le_MODELE_est_lue_par_le_critique():
    """« a_completer » était produit depuis toujours et n'était qu'affiché.
    C'est ici qu'il devient un verdict."""
    plan = O.planifier(["Nos effectifs"])
    texte = "## Nos effectifs\n[À COMPLÉTER — organigramme]\n" + "x" * 400
    v = O.critiquer(plan, texte)
    assert v["points"][0]["etat"] == "a_completer"


# ═══════════════════════════════════════════════════════════════════════════
#  7. LE VÉRIFICATEUR — ET LA RÈGLE QUI L'EMPÊCHE DE CRIER SUR TOUT
# ═══════════════════════════════════════════════════════════════════════════

def test_un_chiffre_qui_ne_vient_d_AUCUNE_source_est_signale():
    extraits = [{"content": "Le PUE mesure est de 1,42 sur le trimestre."}]
    orphelins = O.verifier_sources("Le PUE est de 1,42 et la puissance de "
                                   "400 kW.", extraits)
    assert "400" in orphelins
    assert "1.42" not in orphelins, \
        "une grandeur REPRISE d'un extrait est signalée : le contrôle crie " \
        "sur tout, il sera éteint"


def test_un_chiffre_venu_de_la_FICHE_du_projet_n_est_pas_signale():
    """Le client a saisi la puissance ; l'avoir reprise n'est pas l'avoir
    inventée."""
    o = O.verifier_sources("Une puissance de 400 kW.", [],
                           fiche={"perimetre": "Salle IT de 400 kW"})
    assert o == []


def test_les_tres_petits_entiers_ne_sont_PAS_signales():
    """« niveau 2 », « en 2 temps » : mesurés sur des brouillons, ils faisaient
    l'essentiel des signalements et aucun n'était une grandeur relevée."""
    assert O.verifier_sources("Le niveau 2 impose 2 mesures.", []) == []


# ═══════════════════════════════════════════════════════════════════════════
#  8. LES TROIS RÉGIMES DU FONDS CABINET, CONSERVÉS
# ═══════════════════════════════════════════════════════════════════════════

def test_la_couverture_AO_conserve_LES_TROIS_regimes_de_visibilite():
    """Fondre les trois lots sous un seul `public_only` aurait sacrifié soit
    nos CV, soit la confidentialité d'un client."""
    import ao_redaction as R

    class Mouchard(object):
        def __init__(self):
            self.appels = []

        def search(self, q, k=5, public_only=True, theme=None, doc_ids=None):
            self.appels.append({"public_only": public_only,
                                "theme": tuple(theme or ())})
            return []

    piece = {"cle": "x", "nom": "Mémoire technique", "bloquante": False,
             "contient": ["Nos moyens humains", "Nos références"]}
    m = Mouchard()
    R.couverture_des_points(piece, m)
    assert m.appels, "aucune recherche : la règle ne mesure rien"
    regimes = {}
    for a in m.appels:
        regimes.setdefault(a["theme"], set()).add(a["public_only"])
    # CHAQUE LOT GARDE UN RÉGIME UNIQUE ET STABLE, sur tous les tours.
    for theme, vus in regimes.items():
        assert len(vus) == 1, \
            "le lot %s a été interrogé sous deux régimes : %s" % (theme, vus)
    # ET LES DEUX RÉGIMES COEXISTENT — sans quoi la règle passerait sur un
    # module qui aurait tout fermé, ou tout ouvert.
    assert {True, False} == {v for vus in regimes.values() for v in vus}, \
        "les trois lots ne portent plus deux régimes distincts"


# ═══════════════════════════════════════════════════════════════════════════
#  9. LE BRANCHEMENT — CE QUI Y A DROIT MAINTENANT, ET N'Y AVAIT PAS DROIT
# ═══════════════════════════════════════════════════════════════════════════

def test_les_quatre_vingt_dix_types_ont_TOUS_un_plan():
    """Le plan n'est pas inventé : il est déjà déclaré. Si un type perdait ses
    sections, il retomberait en silence sur la requête unique."""
    sans = [t["id"] for t in livrables.TYPES if not O.plan_du_livrable(t["id"])]
    assert sans == [], "%d type(s) sans plan : %s" % (len(sans), sans[:5])


def test_un_type_SANS_sections_retombe_sur_le_chemin_d_avant(monkeypatch):
    """Rendre un plan inventé serait pire que ne rien rendre : on chercherait
    point par point des points qui ne sont pas ceux du document."""
    faux = dict(livrables.get_type(TYPE))
    faux["sections"] = []
    monkeypatch.setattr(livrables, "get_type", lambda i: faux)
    assert O.plan_du_livrable(TYPE) == []


def test_le_chemin_SANS_phase_ni_code_recoit_desormais_une_couverture(fonds, monkeypatch):
    """LE DÉFAUT MESURÉ : `couverture_documentaire` ne servait qu'aux pièces
    portant phase ET code — un seul écran. Les quatre-vingt-dix types
    recevaient les extraits d'une requête générale."""
    import app as A
    monkeypatch.setattr(A, "rag", fonds)
    c = A._couverture_par_point(TYPE, {"secteur": SUJET}, None, True)
    assert c is not None, "aucune couverture sans phase ni code"
    assert c["resume"]["total"] == len(livrables.get_type(TYPE)["sections"])
    assert c["resume"]["couverts"] > 0


def test_avec_phase_et_code_c_est_le_registre_qui_COMMANDE(fonds, monkeypatch):
    """Une pièce de maîtrise d'œuvre a un contenu exigé plus précis que les
    sections d'un type. Le chemin nouveau sert les autres, il ne prend la
    place d'aucun."""
    import app as A
    monkeypatch.setattr(A, "rag", fonds)
    vus = {}

    def faux(phase, code, chercher, inputs=None, **kw):
        vus["appele"] = (phase, code)
        return {"points": [], "resume": {"total": 0, "couverts": 0,
                                         "a_ecrire": 0, "inconnus": 0},
                "lecture": "", "reserve": ""}

    monkeypatch.setattr(A.ingenierie_dc, "couverture_documentaire", faux)
    A._couverture_par_point(TYPE, {}, None, True, phase="APS", code="CCTP")
    assert vus.get("appele") == ("APS", "CCTP")


# ═══════════════════════════════════════════════════════════════════════════
#  10. LA TRACE — SANS ELLE, UN ReAct EST UN APPEL UNIQUE MIEUX RACONTÉ
# ═══════════════════════════════════════════════════════════════════════════

def test_la_relance_CHANGE_de_vocabulaire_et_la_trace_le_dit(fonds):
    """Reposer la même question compterait un tour pour rien.

    ═══ LE PLAN MÊLE UN POINT TROUVABLE À UN POINT INTROUVABLE ═══════════
    Pour la même raison que plus haut, et la première version de cette règle
    l'avait manquée : avec deux points introuvables, l'arrêt sur stagnation
    coupait après le tour 0, aucune RELANCE n'avait lieu, et une mutation qui
    supprimait le dédoublonnage des stratégies survivait — il n'y avait
    qu'une requête par point, donc jamais deux fois la même.

    Le point trouvable empêche la stagnation ; le point introuvable est alors
    réellement relancé, et c'est là que se mesure si la question a changé.
    """
    plan = O.planifier(["Cartographie zones conduits",       # trouvable
                        "Absent zzz"])                        # jamais trouvé
    t = O.Trace()
    O.documenter(plan, _chercheur(fonds), trace=t)
    requetes = [p["action"] for p in t.par_role("documentaliste") if p["action"]]
    assert t.tours() >= 2, \
        "un seul tour : la règle ne mesure PAS les relances (%s)" % requetes
    assert len(requetes) == len(set(requetes)), \
        "deux tours ont posé la MÊME requête : %s" % requetes


def test_la_trace_dit_QUELLE_strategie_a_trouve(fonds):
    """Sans cela, une règle ne pourrait que constater qu'on a trouvé — et la
    deuxième stratégie pourrait être morte sans que rien ne le dise."""
    d = O.documenter(O.plan_du_livrable(TYPE), _chercheur(fonds), sujet=SUJET)
    strategies = {q["trouve_par"] for q in d["points"] if q["trouve_par"]}
    assert strategies, "aucun point n'a de stratégie attribuée"
    assert strategies <= {n for n, _q in
                          O.strategies(O.plan_du_livrable(TYPE)[0], SUJET)}


def test_la_trace_refuse_un_role_inconnu():
    """Un rôle écrit de travers donnerait une trace qui nomme un acteur qui
    n'existe pas — et l'annexe du document le montrerait au client."""
    with pytest.raises(ValueError):
        O.Trace().noter("relecteur", "…", "", "")


# ═══════════════════════════════════════════════════════════════════════════
#  11. LA GARDE D'IMPORT, ÉPROUVÉE EN LUI DONNANT UNE FAUTE À TROUVER
# ═══════════════════════════════════════════════════════════════════════════
#
# POURQUOI INJECTER LA FAUTE. L'état correct est une liste vide : une règle qui
# se contenterait de `assert O._FAUTES == []` passerait aussi sur une garde
# désarmée. On lui donne donc quelque chose à trouver.

def test_la_garde_refuse_un_role_sans_interdit_ecrit(monkeypatch):
    roles = {c: dict(r) for c, r in O.ROLES.items()}
    roles["critique"]["interdit"] = ""
    monkeypatch.setattr(O, "ROLES", roles)
    with pytest.raises(RuntimeError) as e:
        O._verifier()
    assert "interdit" in str(e.value)


def test_la_garde_refuse_un_SECOND_role_qui_consommerait_un_modele(monkeypatch):
    """Le jour où l'on en branchera un second, ce sera une décision prise dans
    la table — pas un effet de bord ailleurs. Le coût du module se lit là."""
    roles = {c: dict(r) for c, r in O.ROLES.items()}
    roles["critique"]["modele"] = True
    monkeypatch.setattr(O, "ROLES", roles)
    with pytest.raises(RuntimeError) as e:
        O._verifier()
    assert "modele" in str(e.value) or "modèle" in str(e.value)


def test_seul_le_redacteur_consomme_un_modele():
    """LE FAIT QUI REND CE MODULE MESURABLE. Le planificateur, le
    documentaliste, le critique et le vérificateur sont déterministes : le
    gain principal ne coûte pas un jeton, et ces règles n'ont aucun modèle à
    simuler."""
    assert sorted(c for c, r in O.ROLES.items() if r["modele"]) == ["redacteur"]
