# -*- coding: utf-8 -*-
"""Le parcours guidé d'une réponse à appel d'offres — mesuré, pas raconté.

CE QUI DISTINGUE UN PARCOURS D'UNE LISTE DE CONSEILS, et ce que ces règles
tiennent : chaque étape se dit faite ou non faite SUR UN NOMBRE. « Le dossier
semble incomplet » n'aide personne à décider s'il peut déposer ; « 7 pièces sur
12, 2 bloquantes manquantes » si.

LE DÉFAUT QUE CES RÈGLES EXISTENT POUR EMPÊCHER : un parcours qui rend
toujours la même chose. Sept étapes rédigées à la main auraient l'air d'un
guide, seraient plus faciles à écrire, et diraient la même chose d'un dossier
vide et d'un dossier prêt. La règle centrale ici est donc celle qui compare
DEUX états et exige que la mesure ait bougé.
"""
import ast
import io
import os
import re
import sys

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import ao_dc                                                       # noqa: E402
import ao_parcours                                                 # noqa: E402
from conftest import ORIGINE                                       # noqa: E402


def _src(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


DOCS = [
    {"nom": "reglement-de-consultation.pdf",
     "texte": "Article 5 — Critères de jugement : prix 40 %, valeur technique 60 %."},
    {"nom": "CCAP.pdf", "texte": "Article 12 — Pénalités de retard : 1/1000 par jour."},
    {"nom": "CCTP.pdf", "texte": "Le titulaire fournit les groupes froids."},
    {"nom": "plan-masse.dwg", "texte": ""},
]


def _etat_avance():
    a = ao_dc.analyser(DOCS)
    fiche = {c["cle"]: "valeur" for c in ao_dc.CHAMPS_CANDIDAT}
    fiche["siret"] = "73282932000074"
    return {"analyse": a, "fiche": fiche,
            "remplissage": ao_dc.remplir(fiche=fiche, analyse=a, saisies={})}


# ── 1. LA MESURE, ET RIEN QUE LA MESURE ──────────────────────────────────

def test_chaque_etape_rend_un_NOMBRE_et_pas_une_impression():
    """Une étape sans chiffre n'est pas une étape franchie : c'est un
    encouragement, et un encouragement ne dit pas si l'on peut déposer.

    LA SEULE ÉCHAPPATOIRE EST NOMMÉE : une étape que ce site NE PEUT PAS
    mesurer — les attestations d'un client, qu'il ne détient pas — le dit en
    toutes lettres. C'est une réponse, pas une impression, et elle ne peut pas
    servir à en couvrir une : le libellé exigé est précis."""
    for e in ao_parcours.parcours(_etat_avance())["etapes"]:
        assert (re.search(r"\d", e["mesure"])
                or e["mesure"].startswith("non mesurée ici")
                or e["mesure"].startswith("non mesurable")), (
            "l'étape « %s » se prononce sans compter et sans dire qu'elle ne "
            "peut pas mesurer : « %s »" % (e["id"], e["mesure"]))
        if not re.search(r"\d", e["mesure"]):
            assert not e["fait"], (
                "l'étape « %s » se déclare faite sans avoir rien compté"
                % e["id"])


def test_le_parcours_CHANGE_quand_l_etat_change():
    """LA RÈGLE CENTRALE. Sept étapes rédigées à la main auraient l'air d'un
    guide et diraient la même chose d'un dossier vide et d'un dossier prêt."""
    vide = ao_parcours.parcours({})
    plein = ao_parcours.parcours(_etat_avance())
    assert plein["faites"] > vide["faites"], (
        "le parcours rend %d étapes faites dans les deux cas : il ne mesure "
        "rien" % vide["faites"])
    mv = {e["id"]: e["mesure"] for e in vide["etapes"]}
    mp = {e["id"]: e["mesure"] for e in plein["etapes"]}
    bougees = [k for k in mv if mv[k] != mp[k]]
    assert len(bougees) >= 5, (
        "seules %d mesures sur %d bougent entre un dossier vide et un dossier "
        "instruit : %s" % (len(bougees), len(mv), sorted(bougees)))


def test_aucune_etape_n_est_faite_sur_un_etat_vide():
    p = ao_parcours.parcours({})
    faites = [e["id"] for e in p["etapes"] if e["fait"]]
    assert not faites, "déclarées faites sans rien savoir : %s" % faites
    assert p["pret"] is False and p["ou_en_est"] == "consultation"


def test_une_piece_bloquante_manquante_empeche_l_etape_de_se_dire_faite():
    """LA RÈGLE QUI MANQUAIT, ET UNE MUTATION L'A MONTRÉ. « Aucune étape n'est
    faite sur un état VIDE » laissait passer un « fait: True » écrit en dur :
    sur un état vide, la mesure sort par un autre chemin. Il faut donc un
    dossier RÉEL mais incomplet — c'est le cas courant, et c'est celui où une
    étape complaisante ferait déposer une candidature irrecevable."""
    p = ao_parcours.parcours(_etat_avance())
    e = next(x for x in p["etapes"] if x["id"] == "consultation")
    assert e["reste"], "le dossier d'essai ne manque plus de rien : la règle "\
                       "ne mesure plus rien"
    assert e["fait"] is False, (
        "l'étape se dit faite alors qu'il manque %s" % ", ".join(e["reste"]))
    # ET L'INVERSE SE VÉRIFIE : rien qui manque, l'étape est faite. Sans ce
    # second volet, un « fait: False » écrit en dur passerait aussi.
    a = dict(_etat_avance()["analyse"])
    a["manquantes"] = [m for m in a["manquantes"] if m["gravite"] != "bloquante"]
    e2 = next(x for x in ao_parcours.parcours({"analyse": a})["etapes"]
              if x["id"] == "consultation")
    assert e2["fait"] is True


def test_une_etape_non_mesurable_n_est_JAMAIS_declaree_faite(monkeypatch):
    """Le pire des deux sens possibles serait de déclarer prêt un dossier dont
    on ne sait rien."""
    casse = [dict(e) for e in ao_parcours.ETAPES]
    casse[0]["mesurer"] = lambda e: (_ for _ in ()).throw(RuntimeError("x"))
    monkeypatch.setattr(ao_parcours, "ETAPES", casse)
    p = ao_parcours.parcours(_etat_avance())
    dce = next(e for e in p["etapes"] if e["id"] == "consultation")
    assert dce["fait"] is False
    assert "non mesurable" in dce["mesure"]


def test_ou_en_est_designe_la_PREMIERE_etape_non_faite_MEME_non_bloquante():
    """Désigner la première BLOQUANTE sauterait « lire ce qui départage », qui
    ne bloque pas la remise mais décide de la gagner.

    L'ÉTAT EST CHOISI POUR QUE LES DEUX LECTURES DIVERGENT. Sur le dossier
    d'essai ordinaire, la première non faite EST la première bloquante : les
    deux réponses coïncident, et une mutation qui désigne la bloquante passait
    inaperçue. On construit donc un dossier complet côté pièces, dont il reste
    seulement une pièce non dépouillée — étape « lire », qui ne bloque pas."""
    a = dict(_etat_avance()["analyse"])
    a["manquantes"] = [m for m in a["manquantes"] if m["gravite"] != "bloquante"]
    p = ao_parcours.parcours({"analyse": a})
    ordre = [e["id"] for e in p["etapes"]]
    premiere = next(e["id"] for e in p["etapes"] if not e["fait"])
    assert premiere == "lire", ordre
    assert "lire" not in p["bloquants"], (
        "l'état d'essai ne sépare plus les deux lectures")
    assert p["ou_en_est"] == "lire", (
        "« où en est » a sauté l'étape qui ne bloque pas et désigne %s"
        % p["ou_en_est"])


def test_pret_ne_vaut_que_si_aucune_bloquante_ne_manque():
    p = ao_parcours.parcours(_etat_avance())
    assert p["pret"] == (not p["bloquants"])
    assert p["bloquants"], "le dossier d'essai n'a plus rien de bloquant : la "\
                           "règle ne mesure plus rien"
    for i in p["bloquants"]:
        e = next(x for x in p["etapes"] if x["id"] == i)
        assert e["bloquant"] and not e["fait"]


def test_ce_qui_manque_est_NOMME_et_pas_compte():
    """« Il reste 3 choses » n'aide personne à savoir lesquelles, et c'est
    précisément l'information qu'on cherche à cette étape."""
    p = ao_parcours.parcours(_etat_avance())
    dce = next(e for e in p["etapes"] if e["id"] == "consultation")
    assert dce["reste"] and all(isinstance(x, str) and x for x in dce["reste"])


# ── 2. L'ORDRE EST CELUI DU RISQUE ───────────────────────────────────────

def test_ce_qui_met_des_semaines_a_venir_passe_avant_ce_qui_prend_une_heure():
    """C'est la seule étape qu'on ne peut pas rattraper la dernière nuit : une
    attestation fiscale se demande, elle ne se rédige pas."""
    ids = [e["id"] for e in ao_parcours.ETAPES]
    assert ids.index("attestations") < ids.index("remplir") < ids.index("emporter")
    assert ids.index("consultation") == 0, "on ne remplit pas avant d'avoir le dossier"


def test_chaque_etape_designe_un_controle_qui_EXISTE():
    """Une étape qui dit quoi faire sans dire OÙ renvoie chercher dans une page
    longue — et c'est là qu'on abandonne un parcours. La règle a servi dès son
    écriture : deux ancres sur sept pointaient vers un identifiant inventé."""
    page = _src("ingenierie-datacenter.html")
    js = _src("ingenierie-dc.js")
    app = _src("app.py")
    for e in ao_parcours.etapes():
        a = e["ancre"]
        if a.startswith("#"):
            trouve = ('id="%s"' % a[1:]) in page or ('id="%s"' % a[1:]) in js
            assert trouve, "l'étape « %s » désigne %s, qui n'existe nulle part" \
                           % (e["id"], a)
        else:
            assert ('@app.route("%s")' % a) in app, (
                "l'étape « %s » renvoie à %s, qui n'est pas une page servie"
                % (e["id"], a))


def test_chaque_etape_nomme_son_piege_et_sa_raison_d_etre():
    for e in ao_parcours.etapes():
        # LE TITRE EST COURT PAR NATURE — « Lire ce qui départage » fait
        # vingt et un signes et c'est un bon titre. La longueur se demande à
        # la prose, pas à l'intitulé.
        assert 8 <= len(e.get("nom") or "") <= 60, e["id"]
        for champ in ("question", "pourquoi", "geste", "piege"):
            assert len(e.get(champ) or "") > 25, (
                "l'étape « %s » n'a rien à dire sur « %s »" % (e["id"], champ))


def test_le_parcours_porte_sa_reserve():
    """Un parcours entièrement vert ne dit pas que l'offre est bonne."""
    r = ao_parcours.parcours({})["reserve"]
    assert "ne juge pas" in r.lower() and "mesurable" in r


# ── 3. IL NE MESURE PAS LA MAUVAISE ENTREPRISE ───────────────────────────

def test_le_module_n_atteint_PAS_le_dossier_de_la_maison():
    """`dossier_entreprise` porte les attestations de CONSEILPREV et est
    réservé à l'administrateur. Un client répond à SA consultation avec SES
    attestations : y lire la table de la maison mesurerait la mauvaise
    entreprise, en plus de faire fuiter la bonne."""
    arbre = ast.parse(_src("ao_parcours.py"))
    importes = set()
    for n in ast.walk(arbre):
        if isinstance(n, ast.Import):
            importes |= {x.name for x in n.names}
        elif isinstance(n, ast.ImportFrom):
            importes.add(n.module)
    assert "dossier_entreprise" not in importes, importes


def test_sans_attestations_remises_l_etape_le_DIT_au_lieu_de_se_prononcer():
    e = next(x for x in ao_parcours.parcours(_etat_avance())["etapes"]
             if x["id"] == "attestations")
    assert e["fait"] is False
    assert "ne détient pas" in e["mesure"]


def test_des_attestations_remises_sont_mesurees():
    at = {"total": 5, "valides": ["a", "b", "c", "d", "e"],
          "absentes": [], "perimees": []}
    e = next(x for x in ao_parcours.parcours(dict(_etat_avance(),
                                                  attestations=at))["etapes"]
             if x["id"] == "attestations")
    assert e["fait"] is True and "5 attestation(s) valide(s) sur 5" in e["mesure"]


# ── 4. LA ROUTE, ET CE QU'ELLE DONNE À QUI ───────────────────────────────

def _demander(cl, corps=None):
    r = cl.post("/api/datacenter/marche/parcours",
                json=corps or {"fiche": {"raison_sociale": "X"}},
                headers=ORIGINE)
    assert r.status_code == 200, r.data[:300]
    return r.get_json()["parcours"]


def test_la_route_rend_les_sept_etapes_mesurees(marche):
    p = _demander(marche)
    assert len(p["etapes"]) == len(ao_parcours.ETAPES) == 7
    assert p["ou_en_est"] == "consultation" and p["pret"] is False


def test_le_parcours_REFUSE_un_compte_client(connecte):
    """LA DÉCISION D'ACCÈS, MESURÉE ICI COMME AILLEURS. La réponse à
    consultation est un outil interne : les douze interfaces de la section
    sont déclarées dans `acces.API_ADMIN`, et le service refuse de démarrer si
    l'une d'elles s'ouvrait."""
    r = connecte.post("/api/datacenter/marche/parcours", json={},
                      headers=ORIGINE)
    assert r.status_code == 403, r.status_code


def test_les_attestations_de_la_maison_NE_SORTENT_QUE_si_on_les_donne():
    """LE SECOND VERROU, QUI SURVIT AU PREMIER.

    CETTE RÈGLE A CHANGÉ DE NIVEAU, DÉLIBÉRÉMENT. Elle mesurait naguère que le
    client voyait « non mesurée ici » et l'administrateur l'état réel. Ce
    contraste n'est plus observable PAR LA ROUTE : elle est désormais fermée à
    l'administration, un client n'y accède plus du tout, et la règle ci-dessus
    tient ce côté-là.

    CE QUI RESTE À TENIR, ET QUI COMPTE PLUS. `dossier_entreprise` porte les
    attestations de CONSEILPREV, jamais celles du client. Le jour où cette
    section se rouvrirait aux comptes clients, c'est cette branche — et elle
    seule — qui empêcherait de servir à un client l'état d'une entreprise qui
    n'est pas la sienne. On la mesure donc là où elle vit : dans le calcul du
    parcours, avec et sans la clé."""
    base = {"remplissage": ao_dc.remplir(fiche={"raison_sociale": "X"},
                                         analyse=None, saisies={})}
    sans = next(e["mesure"] for e in ao_parcours.parcours(base)["etapes"]
                if e["id"] == "attestations")
    import dossier_entreprise
    avec_cle = dict(base, attestations=dossier_entreprise.etat_attestations())
    avec = next(e["mesure"] for e in ao_parcours.parcours(avec_cle)["etapes"]
                if e["id"] == "attestations")
    assert "ne détient pas" in sans, sans
    assert "attestation(s) valide(s)" in avec and "ne détient pas" not in avec, avec


def test_la_route_ne_donne_les_attestations_QU_AU_ROLE_administrateur(marche):
    """Et le contrôle de rôle reste posé dans la route, alors même que le
    décorateur le rend aujourd'hui toujours vrai. Une défense en profondeur
    qu'on retire parce qu'elle « ne sert plus » est exactement celle qui
    manquera au prochain assouplissement."""
    m = next(e["mesure"] for e in _demander(marche)["etapes"]
             if e["id"] == "attestations")
    assert "attestation(s) valide(s)" in m, m
    src = io.open(os.path.join(ICI, "app.py"), encoding="utf-8").read()
    bloc = src[src.index("def api_datacenter_marche_parcours("):]
    bloc = bloc[:bloc.index("\n@app.route")]
    assert 'role") or "user") == "admin"' in bloc, (
        "la route ne vérifie plus le rôle avant de servir le dossier de la "
        "maison : le décorateur devient le seul verrou")


def test_la_route_est_fermee_a_l_anonyme(anonyme):
    r = anonyme.post("/api/datacenter/marche/parcours", json={}, headers=ORIGINE)
    assert r.status_code in (401, 403)


def test_la_route_ne_conserve_rien(marche):
    """Comme /export, /formulaire et /dossier.zip : la fiche arrive dans la
    requête et repart dans la réponse. Deux appels identiques rendent le même
    parcours ; un troisième avec une fiche vide ne garde rien du premier."""
    fiche = {c["cle"]: "valeur" for c in ao_dc.CHAMPS_CANDIDAT}
    plein = _demander(marche, {"fiche": fiche})
    apres = _demander(marche, {"fiche": {}})
    mp = next(e["mesure"] for e in plein["etapes"] if e["id"] == "fiche")
    ma = next(e["mesure"] for e in apres["etapes"] if e["id"] == "fiche")
    assert mp != ma and ma.startswith("0 champ")


# ── 5. IL EST ATTEIGNABLE, ET DISTINCT DE CELUI DES PHASES ───────────────

def test_le_parcours_est_atteignable_depuis_la_page():
    page = _src("ingenierie-datacenter.html")
    js = _src("ingenierie-dc.js")
    assert 'id="ig-aop-go"' in page and 'id="ig-aop-out"' in page
    assert "/api/datacenter/marche/parcours" in js
    assert 'if ((b = $("#ig-aop-go")))' in js, (
        "le bouton existe sans écouteur : un bouton vivant en apparence et "
        "mort en réalité")


def test_le_bloc_ne_partage_aucun_prefixe_avec_ses_voisins():
    """« ig-ao-p » existe déjà pour les cartes de pièce. Deux blocs qui se
    partagent un préfixe se partagent aussi les règles — défaut déjà payé une
    fois sur cette page."""
    page = _src("ingenierie-datacenter.html")
    for regle in re.findall(r"^\s*\.(ig-aop[\w-]*)", page, re.M):
        assert not regle.startswith("ig-ao-"), (
            "la classe « %s » déborde sur le bloc des pièces" % regle)
    assert ".ig-aop{" in page, "le bloc n'a pas sa feuille"


def test_les_deux_parcours_ne_se_confondent_pas():
    """Celui des phases suit la production documentaire d'un projet ; celui-ci
    suit l'ordre du risque d'une remise. Plaquer l'un sur l'autre aurait donné
    un parcours qui a l'air juste et ne correspond à rien."""
    import ingenierie_dc
    phases = {p["code"] for p in ingenierie_dc.PHASES}
    ids = {e["id"] for e in ao_parcours.ETAPES}
    assert not (ids & {c.lower() for c in phases})
    doc = ao_parcours.__doc__ or ""
    assert "ingenierie_dc.guide" in doc, (
        "le module ne dit pas pourquoi il ne réutilise pas le parcours existant")
