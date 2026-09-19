"""LA CONTRE-EXPERTISE D'UNE USINE IA — CE QU'ELLE MESURE, ET CE QU'ELLE REFUSE.

CE MODULE NE COTE PAS UN SYSTÈME, IL CONTESTE UN PROGRAMME. La distinction
commande tout le reste, et elle est facile à perdre : `chaine_autonomie` dit ce
qu'un système PEUT atteindre, `ia_factory` étudie une usine AVANT de la
construire, et celui-ci arrive quand elle tourne déjà. Sa question n'est pas
« que faudrait-il mettre en place » — c'est « qu'est-ce qui est parti sans son
contrôle, et depuis combien de jours ».

LE DÉFAUT QUE CE FICHIER TRAQUE est celui d'un chiffre qui monte pendant que la
situation se dégrade. Un taux de couverture le fait : il compte les contrôles en
place sur les contrôles du catalogue, et il grimpe pendant que des cas d'usage
partent en service sans contrôle, parce qu'il ne compte pas les cas. C'est
précisément le chiffre qu'on rend en comité quand on veut rassurer, et c'est
celui qui laisse passer la dette. Les règles ci-dessous vérifient que le module
n'en rend aucun, sous aucun nom.

CE QUI EST ÉPROUVÉ :
  1. la dette compte les cas EN SERVICE — un cas à venir n'est pas une dette ;
  2. sans inventaire, elle est INCALCULABLE et le dit, au lieu de rendre zéro ;
  3. aucun pourcentage de couverture n'est rendu, sous aucun nom ;
  4. l'ancienneté est une soustraction de dates, et la date est INJECTÉE —
     le module ne lit jamais l'horloge de la machine dans son calcul ;
  5. la feuille de route respecte les prérequis, et la durée d'un lot est
     celle de son plus long contrôle, jamais la somme ;
  6. l'alerte est une soustraction de deux dates, et elle ne recommande RIEN ;
  7. les trois routes servent, refusent en NOMMANT le motif, et sont déclarées
     dans la politique d'accès ;
  8. l'écran ne recopie AUCUN libellé du module — sinon les deux divergent au
     premier délai révisé, et c'est l'écran qu'on croira ;
  9. le parcours guidé existe pour le rôle ET pour le secteur nommés.
"""
import json
import os
import re
import subprocess
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import acces               # noqa: E402
import contre_expertise_ia as cx   # noqa: E402

JOUR = "2026-09-19"


def _lire(nom):
    with open(os.path.join(ICI, nom), encoding="utf-8") as f:
        return f.read()


def _dossier(cas=(), controles=None, nom="Usine"):
    return {"nom": nom, "cas_usage": list(cas), "controles": dict(controles or {})}


def _cas(type_cle, depuis, en_service=True, nom=None):
    return {"nom": nom or type_cle, "type": type_cle,
            "en_service": en_service, "depuis": depuis}


# ══════════════════════════════════════════════════════════════════════════
#  1. LA DETTE COMPTE CE QUI TOURNE, PAS CE QUI EST PRÉVU
# ══════════════════════════════════════════════════════════════════════════

def test_un_cas_a_venir_n_est_PAS_une_dette():
    """DEUX DOSSIERS QUI NE DIFFÈRENT QUE PAR `en_service`.

    Un module qui compterait les cas DÉCLARÉS rendrait le même chiffre pour les
    deux — et il gonflerait à chaque idée notée en atelier, ce qui apprendrait
    à l'équipe à ne plus rien déclarer. C'est l'inverse de ce qu'on cherche.
    """
    controles = {"inventaire": "2020-01-01"}
    tourne = cx.dette([_cas("vibe_coding", "2025-11-15", True)], controles, JOUR)
    prevu = cx.dette([_cas("vibe_coding", "2025-11-15", False)], controles, JOUR)
    assert tourne["ok"] and prevu["ok"]
    assert tourne["cas_en_dette"] == 1, tourne["cas_en_dette"]
    assert prevu["cas_en_dette"] == 0, (
        "un cas d'usage qui n'est pas en service est compté comme une dette : "
        "le chiffre monterait à chaque idée notée en atelier")
    assert prevu["jours_cumules"] == 0


def test_les_jours_cumules_sont_la_SOMME_des_anciennetes():
    """LE CHIFFRE MIS EN GROS EST UNE SOMME, ET ELLE DOIT ÊTRE EXACTE.

    Un module qui rendrait une moyenne, un maximum ou un compte déguisé
    passerait toutes les autres règles : il serait cohérent, monotone, et faux.
    On refait donc la soustraction à la main.
    """
    import datetime
    dep = {"vibe_coding": "2025-11-15", "agents_autonomes": "2026-06-01"}
    r = cx.dette([_cas(k, v) for k, v in dep.items()],
                 {"inventaire": "2020-01-01"}, JOUR)
    attendu = sum(
        (datetime.date.fromisoformat(JOUR) - datetime.date.fromisoformat(v)).days
        for v in dep.values())
    assert r["jours_cumules"] == attendu, (
        "les jours cumulés valent %d, la somme des anciennetés vaut %d"
        % (r["jours_cumules"], attendu))


def test_la_date_est_INJECTEE_et_l_anciennete_la_suit():
    """SI LE MODULE LISAIT SON HORLOGE, CETTE RÈGLE NE VERRAIT RIEN CHANGER.

    Deux lectures du même dossier à deux dates rendent deux anciennetés, et
    l'écart entre elles vaut exactement l'écart entre les deux dates. Un module
    qui prendrait `date.today()` dans son calcul rendrait deux fois le même
    chiffre — et la règle qui mesure la dette ne tiendrait pas d'un jour
    à l'autre.
    """
    cas = [_cas("vibe_coding", "2025-11-15")]
    ctrl = {"inventaire": "2020-01-01"}
    a = cx.dette(cas, ctrl, "2026-09-19")
    b = cx.dette(cas, ctrl, "2026-09-29")
    assert b["jours_cumules"] - a["jours_cumules"] == 10, (
        "dix jours plus tard, la dette n'a pas vieilli de dix jours : %d → %d"
        % (a["jours_cumules"], b["jours_cumules"]))


# ══════════════════════════════════════════════════════════════════════════
#  2. SANS INVENTAIRE, LA DETTE N'EST PAS NULLE — ELLE EST INCALCULABLE
# ══════════════════════════════════════════════════════════════════════════

def test_sans_inventaire_la_dette_est_INCALCULABLE_et_non_nulle():
    """ZÉRO SUR UN PÉRIMÈTRE INCONNU EST LE PIRE DES RÉSULTATS.

    Il se lit comme une bonne nouvelle, il est parfaitement cohérent, et il
    porte sur un ensemble que personne n'a établi. Un module qui le rendrait
    ferait exactement ce qu'il est écrit pour dénoncer.
    """
    r = cx.dette([], {}, JOUR)
    assert r["ok"]
    assert r["inventaire_tenu"] is False
    assert r["calculable"] is False, (
        "sans inventaire, le module se déclare capable de calculer la dette")


def test_l_inventaire_absent_COMMANDE_la_restitution():
    """ET IL PASSE DEVANT LA DETTE ELLE-MÊME.

    Un dossier peut porter des cas en dette ET n'avoir pas d'inventaire. Dans
    ce cas la tête de restitution doit nommer l'inventaire, pas la dette :
    discuter d'un nombre de cas devant un périmètre inconnu revient à négocier
    sur un chiffre qu'on vient d'inventer.
    """
    d = _dossier([_cas("vibe_coding", "2025-11-15")], {})
    r = cx.contre_expertise(d, aujourdhui=JOUR)
    assert r["ok"]
    assert r["tete"] == "inventaire_absent", r["tete"]

    # ET AVEC L'INVENTAIRE, LA TÊTE CHANGE — sinon la règle ci-dessus
    # mesurerait « la tête est toujours inventaire_absent », ce qui est vrai
    # pour une raison sans rapport avec ce qu'elle prétend.
    d2 = _dossier([_cas("vibe_coding", "2025-11-15")], {"inventaire": "2020-01-01"})
    assert cx.contre_expertise(d2, aujourdhui=JOUR)["tete"] == "dette"


# ══════════════════════════════════════════════════════════════════════════
#  3. AUCUN POURCENTAGE DE COUVERTURE, SOUS AUCUN NOM
# ══════════════════════════════════════════════════════════════════════════

def test_la_contre_expertise_ne_rend_AUCUN_taux_de_couverture():
    """LA RÈGLE REGARDE LES VALEURS, PAS SEULEMENT LES NOMS DE CHAMPS.

    Interdire la clé « couverture » ne suffirait pas : le même chiffre
    réapparaîtrait sous « maturite », « score » ou « avancement ». On cherche
    donc tout nombre qui VAUT la proportion de contrôles en place — c'est lui
    qu'on refuse, quel que soit le nom qu'on lui donne.
    """
    en_place = {c["cle"]: "2020-01-01" for c in list(cx.CONTROLES)[:9]}
    r = cx.contre_expertise(
        _dossier([_cas("vibe_coding", "2025-11-15")], en_place), aujourdhui=JOUR)
    assert r["ok"]
    taux = 100.0 * 9 / len(cx.CONTROLES)          # 47,36…
    interdits = {round(taux, 0), round(taux, 1), round(taux, 2),
                 round(9.0 / len(cx.CONTROLES), 2), 9.0 / len(cx.CONTROLES)}

    trouves = []

    def fouiller(x, chemin):
        if isinstance(x, dict):
            for k, v in x.items():
                fouiller(v, chemin + "." + str(k))
        elif isinstance(x, list):
            for i, v in enumerate(x):
                fouiller(v, "%s[%d]" % (chemin, i))
        elif isinstance(x, float) and x in interdits:
            trouves.append(chemin + " = " + repr(x))

    fouiller(r, "r")
    assert not trouves, (
        "un taux de couverture est rendu : %s" % ", ".join(trouves))


# ══════════════════════════════════════════════════════════════════════════
#  4. LA FEUILLE DE ROUTE EST DÉRIVÉE, PAS ÉCRITE
# ══════════════════════════════════════════════════════════════════════════

def test_un_controle_ne_precede_JAMAIS_son_prerequis():
    """L'ORDRE N'EST PAS UNE PRÉFÉRENCE, C'EST UNE CONTRAINTE.

    Un lot qui livrerait la validation de modèles avant la chaîne qui versionne
    ces modèles décrirait un travail qui ne peut pas se faire — et il se
    lirait parfaitement en comité, parce qu'une feuille de route ne dit jamais
    d'elle-même qu'elle est infaisable.
    """
    r = cx.feuille_de_route({}, depart=JOUR)
    assert r["ok"]
    rang = {}
    for lot in r["lots"]:
        for c in lot["controles"]:
            rang[c["cle"]] = lot["rang"]
    fautes = []
    for c in cx.CONTROLES:
        for p in c["prerequis"]:
            if p in rang and rang.get(c["cle"], -1) <= rang[p]:
                fautes.append("%s (lot %d) ne suit pas %s (lot %d)"
                              % (c["cle"], rang[c["cle"]], p, rang[p]))
    assert not fautes, "; ".join(fautes)


def test_la_duree_d_un_lot_est_celle_du_PLUS_LONG_pas_la_somme():
    """CE QUI SE FAIT EN PARALLÈLE NE S'ADDITIONNE PAS.

    Additionner les délais d'un lot produirait une trajectoire deux fois trop
    longue, qu'on présenterait en comité comme « le temps que ça demande » —
    et on se verrait refuser un budget pour un calendrier qu'on a soi-même
    gonflé.
    """
    r = cx.feuille_de_route({}, depart=JOUR)
    vus = 0
    for lot in r["lots"]:
        delais = [cx.CONTROLES_PAR_CLE[c["cle"]]["delai_jours"]
                  for c in lot["controles"]]
        if len(delais) < 2:
            continue
        vus += 1
        assert lot["duree_jours"] == max(delais), (
            "le lot %d dure %d j pour un plus long contrôle à %d j"
            % (lot["rang"], lot["duree_jours"], max(delais)))
        assert lot["duree_jours"] != sum(delais)
    assert vus >= 1, "aucun lot ne porte deux contrôles : la règle n'a rien mesuré"


def test_un_controle_DEJA_en_place_ne_revient_pas_dans_la_route():
    """SINON LA TRAJECTOIRE REDEMANDE CE QUI EST DÉJÀ PAYÉ.

    Et le premier effet n'est pas financier : l'équipe qui tient déjà ce
    contrôle cesse de croire le reste du document.
    """
    sans = cx.feuille_de_route({}, depart=JOUR)
    avec = cx.feuille_de_route({"inventaire": "2020-01-01",
                                "politique_usage": "2020-01-01"}, depart=JOUR)
    places = {c["cle"] for l in avec["lots"] for c in l["controles"]}
    assert "inventaire" not in places and "politique_usage" not in places
    assert set(avec["deja_en_place"]) == {"inventaire", "politique_usage"}
    # ET LA ROUTE S'EST RÉELLEMENT RACCOURCIE : sans cette seconde mesure, la
    # règle passerait aussi sur un module qui aurait simplement oublié ces
    # deux contrôles partout.
    tous = {c["cle"] for l in sans["lots"] for c in l["controles"]}
    assert len(tous) - len(places) == 2


# ══════════════════════════════════════════════════════════════════════════
#  5. L'ALERTE EST UNE SOUSTRACTION, PAS UN AVIS
# ══════════════════════════════════════════════════════════════════════════

def test_reculer_la_date_cible_reduit_l_ecart_D_AUTANT():
    """LE CŒUR DU MÉTIER, ET LA RAISON POUR LAQUELLE IL SE DÉFEND.

    « Ce n'est pas mon avis contre le vôtre, c'est le 3 mars contre le
    31 décembre. » Si l'écart ne suivait pas la date au jour près, la phrase
    deviendrait fausse au premier comité où quelqu'un ferait le calcul.
    """
    amb = {"intitule": "Agents clients", "cas_usage": ["agents_autonomes"]}
    a = cx.alerte(dict(amb, date_cible="2026-12-31"), {}, JOUR)
    b = cx.alerte(dict(amb, date_cible="2027-01-30"), {}, JOUR)
    assert a["ok"] and b["ok"]
    assert a["ecart_jours"] - b["ecart_jours"] == 30, (
        "trente jours de plus réduisent l'écart de %d jours"
        % (a["ecart_jours"] - b["ecart_jours"]))


def test_l_alerte_ne_RECOMMANDE_aucune_des_trois_issues():
    """CHOISIR N'APPARTIENT PAS À LA SÉCURITÉ.

    Un module qui trancherait produirait exactement le réflexe qu'on cherche à
    éviter : contourner la sécurité plutôt que décider avec elle. Les trois
    issues sont donc rendues à égalité, sans marque, sans ordre de préférence
    et sans champ qui en désignerait une.
    """
    r = cx.alerte({"intitule": "X", "date_cible": "2026-12-31",
                   "cas_usage": ["agents_autonomes"]}, {}, JOUR)
    assert r["ok"] and len(r["issues"]) == 3
    marques = ("recommand", "conseill", "preconis", "préconis", "a_retenir",
               "prefer", "préfér", "meilleur")
    for i in r["issues"]:
        texte = json.dumps(i, ensure_ascii=False).lower()
        for m in marques:
            assert m not in texte, (
                "l'issue « %s » porte une marque de recommandation : %s"
                % (i["cle"], m))


def test_un_controle_en_place_RACCOURCIT_l_ecart():
    """SANS CETTE RÈGLE, L'ALERTE POURRAIT IGNORER L'ÉTAT RÉEL.

    Elle rendrait le même écart à une maison qui n'a rien et à une maison qui a
    déjà tout sauf un contrôle — et l'équipe qui a travaillé cesserait de la
    lire.
    """
    amb = {"intitule": "X", "date_cible": "2026-12-31",
           "cas_usage": ["agents_autonomes"]}
    nu = cx.alerte(amb, {}, JOUR)
    # `mcp` commande l'écart parce qu'il attend `iam_agents` : poser les deux
    # doit le faire tomber.
    equipe = cx.alerte(amb, {"iam_agents": "2020-01-01", "mcp": "2020-01-01"}, JOUR)
    assert nu["ecart_jours"] > equipe["ecart_jours"], (
        "poser deux des contrôles requis ne change pas l'écart : %d → %d"
        % (nu["ecart_jours"], equipe["ecart_jours"]))


@pytest.mark.parametrize("corps,motif", [
    ({}, "intitule_manquant"),
    ({"intitule": "X"}, "date_cible_manquante"),
    ({"intitule": "X", "date_cible": "2026-12-31"}, "aucun_controle_requis"),
])
def test_l_alerte_NOMME_son_refus(corps, motif):
    """UN REFUS ANONYME EST UN REFUS QU'ON NE CORRIGE PAS.

    L'écran doit pouvoir dire au lecteur CE QUI manque, pas « la demande n'a
    pas abouti ».
    """
    r = cx.alerte(corps, {}, JOUR)
    assert r["ok"] is False and r["motif"] == motif, r


# ══════════════════════════════════════════════════════════════════════════
#  6. LES ROUTES
# ══════════════════════════════════════════════════════════════════════════

ROUTES = ["/api/ai-factory/referentiel", "/api/ai-factory/contre-expertise",
          "/api/ai-factory/alerte"]


@pytest.mark.parametrize("route", ROUTES)
def test_la_route_est_DECLAREE_dans_la_politique_d_acces(route):
    """app.py refuse de démarrer si une route n'est pas classée. Cette règle
    dit en plus DANS QUEL SENS elle l'est : une route de démonstration rangée
    par mégarde parmi les pages réservées s'annoncerait ouverte sur la page et
    rendrait un formulaire de connexion."""
    assert route in acces.API_OUVERTES, (
        "%s n'est pas déclarée ouverte : la page /securite-ia est ouverte, "
        "son interface doit l'être aussi" % route)


def test_les_trois_routes_servent_et_refusent_en_NOMMANT_le_motif():
    """UN 500 SUR UN CORPS MALFORMÉ SERAIT UNE FUITE ET UNE IMPASSE.

    Une pile d'exécution dans la réponse renseigne un attaquant, et n'apprend
    rien au lecteur légitime. Chaque refus porte donc un motif nommé.
    """
    import gzip
    import app as application

    entetes = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept-Language": "fr-FR,fr;q=0.9", "Accept-Encoding": "gzip, deflate",
        "Origin": "http://localhost", "Referer": "http://localhost/securite-ia"}
    c = application.app.test_client()

    def corps(rep):
        b = (gzip.decompress(rep.data)
             if rep.headers.get("Content-Encoding") == "gzip" else rep.data)
        return json.loads(b)

    r = c.get("/api/ai-factory/referentiel", headers=entetes)
    assert r.status_code == 200
    ref = corps(r)["referentiel"]
    assert len(ref["controles"]) == len(cx.CONTROLES)

    for route, envoi, motif in (
            ("/api/ai-factory/contre-expertise", {}, "nom_manquant"),
            ("/api/ai-factory/contre-expertise", {"dossier": "x"},
             "dossier_illisible"),
            ("/api/ai-factory/alerte", {"ambition": {"intitule": "X"}},
             "date_cible_manquante")):
        rep = c.post(route, json=envoi, headers=entetes)
        assert rep.status_code == 400, (route, rep.status_code)
        assert corps(rep)["motif"] == motif, (route, corps(rep))


def test_la_route_prend_la_date_du_CLIENT_et_non_son_horloge():
    """DEUX APPELS, DEUX DATES, DEUX ANCIENNETÉS.

    Si la route prenait l'horloge du serveur, cette règle rendrait deux fois le
    même chiffre — et un lecteur à Nouméa et un lecteur à Paris liraient deux
    dettes différentes sur le même dossier sans savoir pourquoi.
    """
    import gzip
    import app as application
    entetes = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept-Language": "fr-FR,fr;q=0.9", "Accept-Encoding": "gzip, deflate",
        "Origin": "http://localhost", "Referer": "http://localhost/securite-ia"}
    c = application.app.test_client()
    d = _dossier([_cas("vibe_coding", "2025-11-15")], {"inventaire": "2020-01-01"})
    j = []
    for date in ("2026-09-19", "2026-10-19"):
        rep = c.post("/api/ai-factory/contre-expertise",
                     json={"date": date, "dossier": d}, headers=entetes)
        assert rep.status_code == 200
        brut = (gzip.decompress(rep.data)
                if rep.headers.get("Content-Encoding") == "gzip" else rep.data)
        j.append(json.loads(brut)["dette"]["jours_cumules"])
    assert j[1] - j[0] == 30, (
        "un mois plus tard, la route rend %d jours de dette de plus" % (j[1] - j[0]))


# ══════════════════════════════════════════════════════════════════════════
#  7. L'ÉCRAN NE RECOPIE RIEN
# ══════════════════════════════════════════════════════════════════════════

def test_aucun_nom_de_controle_n_est_ECRIT_dans_la_page():
    """UN LIBELLÉ RECOPIÉ DIVERGE AU PREMIER REMANIEMENT.

    Et il diverge en silence : la page continue d'afficher l'ancien nom, le
    moteur calcule avec le nouveau, et c'est la page qu'on croit parce que
    c'est elle qu'on regarde.
    """
    page = _lire("securite-ia.html")
    fautes = [c["nom"] for c in cx.CONTROLES if c["nom"] in page]
    assert not fautes, (
        "%d nom(s) de contrôle recopiés dans la page : %s"
        % (len(fautes), " | ".join(fautes)))


def test_aucune_question_d_architecture_n_est_ECRITE_dans_la_page():
    """MÊME MOTIF, ET LE MÊME SILENCE."""
    page = _lire("securite-ia.html")
    fautes = [q["question"] for q in cx.ARCHITECTURE if q["question"] in page]
    assert not fautes, "question(s) recopiée(s) : %s" % " | ".join(fautes)


def test_la_page_APPELLE_bien_les_trois_routes():
    """SANS CETTE RÈGLE, LA PRÉCÉDENTE SERAIT TRIVIALEMENT VRAIE.

    Une page qui n'appellerait aucune route ne recopierait évidemment aucun
    libellé — et elle n'afficherait rien. La règle d'au-dessus ne vaut que
    parce que celle-ci tient en même temps.
    """
    page = _lire("securite-ia.html")
    for r in ROUTES:
        assert r in page, "la page n'appelle pas %s" % r


# ══════════════════════════════════════════════════════════════════════════
#  8. LE PARCOURS GUIDÉ — LE RÔLE ET LE SECTEUR
# ══════════════════════════════════════════════════════════════════════════

def _parcours():
    with open(os.path.join(ICI, "tests", "_cx_lire_parcours.js"), "w",
              encoding="utf-8") as f:
        f.write("const m=require('%s/parcours.js');"
                "process.stdout.write(JSON.stringify("
                "{p:m.PARCOURS,s:m.SECTEURS}));" % ICI)
    try:
        out = subprocess.run(["node", os.path.join(ICI, "tests",
                                                   "_cx_lire_parcours.js")],
                             capture_output=True, text=True, timeout=60)
        assert out.returncode == 0, out.stderr
        return json.loads(out.stdout)
    finally:
        os.remove(os.path.join(ICI, "tests", "_cx_lire_parcours.js"))


def test_le_role_securite_IA_existe_et_mene_a_la_contre_expertise():
    """UN MODULE QU'AUCUN PARCOURS NE DÉSIGNE N'EST TROUVÉ PAR PERSONNE.

    Il existe, il fonctionne, et le seul chemin qui y mène est de connaître son
    adresse. C'est la façon la plus discrète de ne pas livrer un travail.
    """
    mod = _parcours()
    role = [p for p in mod["p"] if p["id"] == "securite-ia"]
    assert role, "aucun parcours par rôle ne sert la sécurité de l'IA"
    urls = [e["url"] for e in role[0]["etapes"]]
    assert "/securite-ia" in urls
    assert len(role[0]["etapes"]) >= 5


def test_le_secteur_finance_MENE_a_la_contre_expertise_et_la_commente():
    """LE SECTEUR NOMMÉ PAR LA DEMANDE, ET CELUI QUE LE MODULE VISE.

    Un secteur qui renverrait vers la page sans note laisserait le lecteur
    bancaire devant un instrument générique — alors que c'est justement là que
    DORA, NIS 2 et l'annexe III du règlement IA ne se répondent pas.
    """
    mod = _parcours()
    fin = [s for s in mod["s"] if s["id"] == "finance"]
    assert fin, "le secteur finance a disparu"
    fin = fin[0]
    assert "/securite-ia" in [e["url"] for e in fin["etapes"]], (
        "le parcours du secteur financier ne passe pas par la sécurité de l'IA")
    assert "/securite-ia" in fin["notes"], (
        "le secteur financier ne dit rien de particulier sur cette page")


def test_le_role_securite_IA_n_est_PAS_un_doublon_d_un_autre_parcours():
    """DOUZE PARCOURS QUI SE RESSEMBLENT NE SERVENT PLUS À CHOISIR.

    Un rôle dont toutes les étapes se retrouvent dans un autre n'ajoute rien :
    il allonge la liste, et il fait hésiter là où il devrait orienter.
    """
    mod = _parcours()
    par_id = {p["id"]: {e["url"] for e in p["etapes"]} for p in mod["p"]}
    mien = par_id.pop("securite-ia")
    for autre, urls in par_id.items():
        assert not mien.issubset(urls), (
            "le parcours sécurité IA est entièrement contenu dans « %s »" % autre)
