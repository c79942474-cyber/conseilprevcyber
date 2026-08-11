"""Le diagnostic express — les deux pans d'offre qu'il ne montrait pas.

CE QUI ÉTAIT EN CAUSE. Le diagnostic conduit le visiteur en quatre questions
jusqu'à un parcours recommandé. Il proposait quatorze pages — et parmi elles,
AUCUNE des trois d'ingénierie de centres de données, AUCUNE des neuf de
Conseil & transformation. Deux pans entiers de l'offre étaient invisibles à qui
suivait le parcours jusqu'au bout, y compris quand ils étaient la bonne réponse.

CE QUE CES TESTS ÉPROUVENT :

  1. le matériau — les entrées existent, les tables sont complètes, aucune ne
     pointe dans le vide ;
  2. que les blocs sont DÉCISIONNELS et non décoratifs : leur contenu et leur
     ordre changent avec les réponses, et chaque entrée porte son motif ;
  3. que le seuil réglementaire recopié dans la page n'a pas dérivé de
     datacenter.py — un seuil recopié qui dérive fait promettre une conformité
     qu'on ne pourra pas tenir.

Le COMPORTEMENT — quel bloc paraît pour quelles réponses, dans quel ordre — est
éprouvé dans le vrai document par recette_diagnostic.js. La leçon est acquise
ici : un test qui lit le source ne voit pas ce qui est devenu inatteignable.
"""
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import acces  # noqa: E402
import datacenter as dc  # noqa: E402

DC_PAGES = ["/strategie-durable-datacenter", "/datacenter",
            "/ingenierie-datacenter"]
CT_PAGES = ["/operating-model", "/maturite-ot", "/feuille-de-route",
            "/continuite-ot", "/gestion-des-changements", "/architecture-cible",
            "/formation", "/gouvernance-ia", "/relecture-contrat"]


def page():
    with open(os.path.join(ICI, "diagnostic.html"), encoding="utf-8") as f:
        return f.read()


def sans_commentaires(h):
    """Les commentaires citent le défaut corrigé : les lire ferait trouver dans
    l'explication ce qu'on cherche dans le contenu."""
    return re.sub(r"<!--.*?-->", " ", re.sub(r"/\*.*?\*/", " ", h, flags=re.S),
                  flags=re.S)


def bloc(nom):
    """Le corps d'une table JavaScript, commentaires retirés."""
    h = sans_commentaires(page())
    i = h.index("var %s=" % nom)
    return h[i:h.index("\n    };", i) + 6]


# ── 1. Les deux entrées existent, et elles sont atteignables ───────────────

def test_le_centre_de_donnees_est_un_secteur_proposable():
    """Un exploitant répondait « autre secteur » et recevait un parcours qui ne
    parlait ni de son cadre ni de son métier."""
    assert 'name="secteur" value="datacenter"' in page()


def test_le_projet_de_centre_de_donnees_est_une_priorite_proposable():
    """L'industriel qui construit sa propre salle n'est pas « du secteur centre
    de données » : sans cette entrée, il n'a aucun moyen de le dire."""
    assert 'name="priorite" value="datacenter"' in page()


@pytest.mark.parametrize("champ", ["secteur", "priorite"])
def test_chaque_valeur_proposee_a_son_libelle(champ):
    """Une valeur sans libellé s'affiche « undefined » dans le résumé du profil
    — et le visiteur lit qu'on n'a pas compris sa réponse."""
    valeurs = set(re.findall(r'name="%s" value="([a-z]+)"' % champ, page()))
    i = page().index("%s:{" % champ)
    declares = set(re.findall(r"(\w+):\"", page()[i:page().index("}", i)]))
    assert valeurs <= declares, sorted(valeurs - declares)


# ── 2. Les deux pans d'offre sont réellement atteints ──────────────────────

@pytest.mark.parametrize("cible", DC_PAGES)
def test_le_diagnostic_conduit_a_chaque_module_de_centre_de_donnees(cible):
    assert '"%s"' % cible in page(), cible


@pytest.mark.parametrize("cible", CT_PAGES)
def test_le_diagnostic_conduit_a_chaque_page_de_conseil_et_transformation(cible):
    """LE CONTRÔLE QUI COMPTE ICI. Ces neuf pages existaient, figuraient au
    menu, et le parcours n'en proposait aucune. Les nommer une par une est
    délibéré : un contrôle sur le NOMBRE de liens se répare en ajoutant
    n'importe lequel, et cesse alors de protéger celui qui manque."""
    assert '"%s"' % cible in page(), cible


def test_aucun_lien_du_diagnostic_ne_pointe_dans_le_vide():
    """Un parcours qui conduit à une adresse inexistante perd le visiteur juste
    après lui avoir demandé quatre réponses."""
    import app as A
    connues = set(A.PAGES)
    h = sans_commentaires(page())
    cites = set(re.findall(r'["\'](/[a-z0-9-]+)["\']', h))
    # /connexion et /admin sont servies par le module d'authentification, hors
    # du registre PAGES : les déclarer inconnues était une faute de mon
    # contrôle, pas un lien mort de la page.
    connues |= {"/connexion", "/inscription", "/mot-de-passe-oublie", "/admin"}
    inconnues = sorted(c for c in cites if c not in connues)
    assert not inconnues, inconnues


# ── 3. Ce sont des blocs DÉCISIONNELS, pas des listes ──────────────────────

def test_chaque_situation_a_son_point_d_entree_dans_le_projet():
    """Proposer d'ouvrir une étude à qui exploite un site depuis dix ans est
    aussi faux que de faire calculer un PUE à qui n'a pas arbitré ses
    objectifs."""
    b = bloc("DC_ENTREE")
    for situation in ("debut", "partiel", "encours", "mature"):
        assert situation + ":{" in b, situation
    modules = set(re.findall(r'cle:"(\w+)"', b))
    assert modules <= {"strategie", "calcul", "moe"}, modules
    assert len(modules) >= 2, (
        "si toutes les situations menaient au même module, le bloc ne "
        "déciderait rien : ce serait une liste avec un préambule")


def test_le_bloc_projet_ne_retire_jamais_un_module_il_le_declasse():
    """Retirer ferait disparaître une étape que le client devra franchir de
    toute façon ; le déclasser dit seulement qu'elle ne vient pas en premier."""
    h = sans_commentaires(page())
    assert 'var DC_ORDRE=["strategie","calcul","moe"]' in h
    i = h.index("var suite=DC_ORDRE.filter")
    assert ".concat(suite)" in h[i:i + 400]


def test_chaque_priorite_appelle_ses_leviers_de_conseil():
    b = bloc("CT_PRIORITE")
    for p in ("conformite", "visibilite", "architecture", "gouvernance", "ia",
              "datacenter"):
        assert p + ":[" in b, p


def test_chaque_levier_porte_LE_MOTIF_de_son_rang():
    """Un lecteur qui n'obtient pas la même liste que son voisin doit pouvoir
    lire pourquoi. Sans motif, le classement paraît arbitraire — et un
    classement arbitraire ne se suit pas."""
    b = bloc("CT_PRIORITE")
    couples = re.findall(r'\["(\w+)","([^"]+)"\]', b)
    assert len(couples) >= 15, len(couples)
    for cle, motif in couples:
        assert len(motif) >= 25, (cle, motif)


def test_chaque_levier_cite_une_page_qui_existe_dans_la_table():
    b, t = bloc("CT_PRIORITE"), bloc("CT")
    declares = set(re.findall(r"^\s*(\w+):\{", t, re.M))
    cites = set(re.findall(r'\["(\w+)",', b))
    assert cites <= declares, sorted(cites - declares)


def test_les_neuf_leviers_sont_TOUS_atteignables_par_au_moins_une_reponse():
    """En déclarer neuf et n'en proposer que quatre remettrait le défaut à
    l'identique — cinq pages que le parcours ne montre jamais."""
    cites = set(re.findall(r'\["(\w+)",', bloc("CT_PRIORITE")))
    cites |= set(re.findall(r'tete:"(\w+)"', bloc("CT_SITUATION")))
    declares = set(re.findall(r"^\s*(\w+):\{", bloc("CT")))
    assert declares <= cites, sorted(declares - cites)


def test_la_situation_reordonne_les_leviers_sans_remplacer_la_liste():
    """Un levier pertinent ne cesse pas de l'être au motif qu'on démarre."""
    h = sans_commentaires(page())
    i = h.index("var sit=CT_SITUATION")
    zone = h[i:i + 700]
    assert "lev.unshift(" in zone, zone[:300]
    assert "lev=[" not in zone, "la liste ne doit pas être remplacée"


# ── 4. Le cadre applicable dit ce que ce métier doit VRAIMENT ──────────────

def test_le_centre_de_donnees_releve_de_l_annexe_I():
    """Fournisseurs de services de centres de données : infrastructure
    numérique, le régime le plus exigeant. C'est une qualification, pas une
    préférence commerciale."""
    h = sans_commentaires(page())
    i = h.index("var ANNEXE1=")
    assert "datacenter:1" in h[i:h.index("\n", i)]


def test_le_cadre_du_centre_de_donnees_NOMME_les_deux_obligations():
    """Un exploitant qui lit « NIS2 » sans lire la directive efficacité
    énergétique repart en croyant son périmètre couvert."""
    h = sans_commentaires(page())
    i = h.index("if(sect==='datacenter')")
    zone = h[i:i + 1400]
    assert "NIS2" in zone
    assert "efficacité énergétique" in zone or "DC_SEUIL" in zone
    assert "62443" in zone, "les installations techniques du site restent en jeu"


def test_LE_SEUIL_RECOPIE_N_A_PAS_DERIVE_DU_REFERENTIEL():
    """LE CONTRÔLE QUI COMPTE LE PLUS DANS CE FICHIER.

    La page recopie un seuil réglementaire — 500 kW — et une référence de
    directive. Le vrai texte vit dans datacenter.py, et rien n'empêche les deux
    de diverger : le jour où le référentiel est corrigé, la page continuerait
    d'annoncer l'ancien chiffre, et une offre bâtie dessus promettrait une
    conformité qu'elle ne pourrait pas tenir. On compare donc à la source."""
    eed = dc.CADRE_UE["eed_reporting"]
    seuils = [s for s in dc.SUGGESTIONS["puissance_it_kw"]
              if s["nature"] == "referentiel_externe"]
    assert seuils, "le référentiel ne porte plus de seuil externe"
    valeur = seuils[0]["valeur"]

    h = sans_commentaires(page())
    i = h.index("var DC_SEUIL=")
    texte = h[i:h.index("\n", i)]
    assert "%d kW" % valeur in texte, (valeur, texte)
    assert "2023/1791" in texte and "2023/1791" in eed["titre"]
    assert "art. 12" in texte and "art. 12" in eed["titre"]


def test_le_seuil_n_est_pas_repete_deux_fois_au_meme_ecran():
    """Le répéter à dix lignes d'intervalle apprend au lecteur à sauter les
    encadrés — et il sautera aussi celui qui compte."""
    h = sans_commentaires(page())
    i = h.index("var deja=(s==='datacenter')")
    assert "seuil.hidden=deja" in h[i:i + 300]


# ── 5. Ce que l'ajout ne devait pas casser ─────────────────────────────────

def test_les_parcours_historiques_restent_entiers():
    """Ajouter deux blocs ne doit pas en retirer un : les cinq priorités
    d'origine gardent leurs lectures et leur démarche."""
    lectures, services = bloc("READS"), bloc("SERVICE")
    for p in ("conformite", "visibilite", "architecture", "gouvernance", "ia"):
        assert p + ":[" in lectures, p
        assert p + ":{" in services, p


def test_la_nouvelle_priorite_a_ses_lectures_ET_sa_demarche():
    """Une priorité sans démarche laisserait le bloc « démarche recommandée »
    vide — le visiteur lirait qu'on n'a rien à lui proposer."""
    assert "datacenter:[" in bloc("READS")
    assert "datacenter:{" in bloc("SERVICE")


def test_le_diagnostic_ne_conduit_qu_a_des_pages_du_site():
    """Toutes les cibles proposées sont des pages réservées ou ouvertes du
    site : aucune adresse externe ne se glisse dans un parcours recommandé."""
    h = sans_commentaires(page())
    for cible in DC_PAGES + CT_PAGES:
        assert acces.statut(cible) in ("direct", "client"), cible
    assert "http://" not in h.replace("http://www.w3.org", ""), (
        "aucun lien externe en clair dans le parcours")


def test_un_projet_de_centre_de_donnees_ne_commence_PAS_par_un_inventaire_OT():
    """LE DÉFAUT QUE LA CAPTURE D'ÉCRAN A MONTRÉ, et qu'aucun contrôle de table
    n'aurait vu.

    « Qui n'a rien de structuré commence par inventorier » est une règle de
    cybersécurité : on ne protège pas ce qu'on ne connaît pas. J'ai ajouté la
    priorité « concevoir un centre de données » sans toucher à cette ligne, et
    le parcours recommandait alors d'inventorier les actifs OT d'un site qui
    n'existe pas encore. Le raccourci logique est le même partout : une règle
    juste dans son domaine devient absurde dès qu'on élargit le domaine sans la
    relire."""
    h = sans_commentaires(page())
    i = h.index("var neuf=")
    ligne = h[i:h.index("\n", i)]
    assert "p!=='datacenter'" in ligne, ligne
    suite = h[i:i + 300]
    assert "var first=neuf?ETAT_LIEUX:SERVICE[p]" in suite, suite[:200]
