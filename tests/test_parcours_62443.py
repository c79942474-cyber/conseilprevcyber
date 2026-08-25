"""LE PARCOURS 62443 — et le mot qu’il refuse d’employer, lui aussi.

CE MODULE EST NÉ D’UNE DEMANDE QU’IL NE TIENT PAS TELLE QUELLE : « donner une
évaluation de la maturité en fonction des réponses ». Il rend une évaluation ;
il ne l’appelle pas maturité, et ce n’est pas un scrupule de vocabulaire.

La CEI 62443-2-4 définit des NIVEAUX DE MATURITÉ (ML 1 à 4) pour le programme
d’un prestataire, la 62443-3-3 des NIVEAUX DE SÉCURITÉ (SL 1 à 4) par exigence
et par zone. Les deux se constatent sur preuves, pour un périmètre donné. Un
compte de cases n’est ni l’un ni l’autre — et « ML 2 » affiché au bas d’un
formulaire finirait cité en réunion, puis en offre, puis devant un auditeur
qui demanderait sur quelle évaluation il repose.

CINQ PROPRIÉTÉS QUE CES CONTRÔLES GARDENT

  1. LE REFUS SURVIT À L’AJOUT DU PARCOURS. Le compte le portait déjà ; le
     danger est qu’une couche au-dessus le reperde en chemin.
  2. L’ORDRE EST UN VRAI ORDRE. Aucune étape ne précède un préalable qui lui
     manque — sans quoi le parcours conseillerait de segmenter avant de
     recenser.
  3. CHAQUE ARÊTE PORTE SA RAISON. Une arête sans raison est une préférence de
     méthode déguisée en contrainte technique.
  4. LE DOCUMENT PORTE LA RÉSERVE AVANT LES CHIFFRES. Il circule sans sa page ;
     reléguée en pied, la réserve arriverait après la décision.
  5. L’EXPORT PASSE PAR LA MÊME PORTE QUE L’ÉCRAN. Un format de sortie ne doit
     jamais devenir le chemin de contournement d’un contrôle.
"""
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import app as A  # noqa: E402
import checklist_62443 as C  # noqa: E402
import parcours_62443 as P  # noqa: E402
from conftest import ADMIN_EMAIL, _assurer_admin  # noqa: E402

H = {"Origin": "http://localhost", "Referer": "http://localhost/x"}


@pytest.fixture
def client():
    _assurer_admin()
    c = A.app.test_client()
    with c.session_transaction() as s:
        s["user_email"] = ADMIN_EMAIL
    A._ip_rate._hits.clear()
    yield c
    A._ip_rate._hits.clear()


def _toutes():
    return [p["cle"] for s in C.SECTIONS for p in s["points"]]


def _apo(s):
    """L'APOSTROPHE EST DROITE DANS LES SOURCES, COURBE AU RENDU. Le module
    écrit `'` — c'est la forme la plus sûre dans une chaîne Python — et
    `livrables_export.typographie` la redresse au moment de composer le
    document. Un contrôle qui cherche l'une des deux formes tombe donc sur la
    moitié des textes sans que rien ne soit cassé."""
    return s.replace("\u2019", "'")


def _plat(x, chemin=""):
    """Toutes les paires (chemin, valeur) d’une structure — pour chercher un
    mot AUSSI BIEN dans une clé que dans une valeur."""
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _plat(v, chemin + "." + str(k))
    elif isinstance(x, (list, tuple)):
        for i, v in enumerate(x):
            yield from _plat(v, chemin + "[%d]" % i)
    else:
        yield chemin, x


# ═══════════════════════════════════════════════════════════════════════════
#  1. CE QUE LE PARCOURS N’EST PAS
# ═══════════════════════════════════════════════════════════════════════════

def test_LE_POINT_QUI_DECIDE_aucune_cle_de_resultat_ne_parle_de_maturite():
    """LE DANGER N’EST PAS LA PHRASE DE RÉSERVE, C’EST LA CLÉ. Un client d’API
    qui lirait `maturite` ou `niveau` afficherait « maturité » quoi qu’en dise
    la note d’à côté — et la note, elle, ne voyage pas jusqu’au tableau de
    bord de quelqu’un d’autre.

    La clé `ou_la_maturite_se_constate` est l’exception NOMMÉE : elle existe
    précisément pour dire où le mot est légitime, et son contenu l’envoie au
    seul point de la liste où un ML se constate."""
    for r in (P.evaluer(["politique"]), P.parcours(["politique", "inventaire"])):
        for chemin, _ in _plat(r):
            bas = chemin.lower()
            if "ou_la_maturite_se_constate" in bas:
                continue
            for interdit in ("maturite", "maturité", "niveau_", "score",
                             "note", "ml_", "sl_"):
                assert interdit not in bas, "clé douteuse : %s" % chemin


def test_le_refus_est_publie_et_nomme_ce_qu_il_refuse():
    """Réduit à « ceci est indicatif », il ne protégerait plus de rien : c’est
    en NOMMANT ML 1–4 et SL 1–4 qu’il dit ce qu’il n’est pas."""
    r = P.evaluer([])
    refus = r["ce_que_ce_n_est_pas"]
    for mot in ("62443-2-4", "62443-3-3", "ML 1 à 4", "SL 1 à 4", "preuves"):
        assert mot in refus, mot
    assert "état de préparation" in refus.lower()


def test_le_lecteur_qui_cherche_la_maturite_est_envoye_quelque_part():
    """Éconduire n’est pas répondre. La liste elle-même dit où un niveau de
    maturité se constate — au point `eval_fournisseurs`, et « seulement
    ici » —, et le parcours reprend ce renvoi plutôt que de le laisser
    enfoui dans un champ `preuve`."""
    assert P.OU_LA_MATURITE_SE_CONSTATE == "eval_fournisseurs"
    preuve = next(p["preuve"] for s in C.SECTIONS for p in s["points"]
                  if p["cle"] == "eval_fournisseurs")
    assert "seulement ici" in preuve.lower(), preuve
    m = P.evaluer([])["ou_la_maturite_se_constate"]
    assert m["cle"] == "eval_fournisseurs" and m["fait"] is False
    assert P.evaluer(["eval_fournisseurs"])["ou_la_maturite_se_constate"]["fait"] is True


# ═══════════════════════════════════════════════════════════════════════════
#  2. L’ORDRE EST UN VRAI ORDRE
# ═══════════════════════════════════════════════════════════════════════════

def test_aucune_etape_ne_precede_un_prealable_qui_lui_manque():
    """SANS CETTE PROPRIÉTÉ, LE PARCOURS CONSEILLERAIT DE SEGMENTER AVANT DE
    RECENSER. C’est la seule chose qu’un ordre doit garantir, et elle se
    vérifie sur les vagues rendues, pas sur la table qui les produit."""
    for depart in ([], ["inventaire"], ["politique", "responsable", "inventaire"]):
        d = P.parcours(depart)
        acquis = set(depart)
        for v in d["vagues"]:
            for e in v["etapes"]:
                for pre, _ in P.PREALABLES.get(e["cle"], []):
                    assert pre in acquis, \
                        "%s proposé avant %s (départ %s)" % (e["cle"], pre, depart)
            acquis |= {e["cle"] for e in v["etapes"]}
        assert acquis == set(_toutes()), depart
        assert d["bloques_hors_vague"] == []


def test_ce_qui_libere_le_plus_remonte_dans_sa_vague():
    """Un classement qui ne classe rien est décoratif. À l’intérieur d’une
    vague, l’ordre est celui du nombre de points libérés — c’est ce qui rend
    la première ligne actionnable."""
    d = P.parcours([])
    premiere = d["vagues"][0]["etapes"]
    liberes = [e["libere"] for e in premiere]
    assert liberes == sorted(liberes, reverse=True), liberes
    assert premiere[0]["cle"] == "inventaire", premiere[0]["cle"]


def test_le_verrou_principal_est_l_inventaire_et_le_nombre_est_mesure():
    """La liste le dit dans ses propres termes : « CE POINT COMMANDE TOUS LES
    AUTRES ». Le parcours doit le retrouver par le calcul, pas le poser à la
    main — sinon le jour où la table changerait, la phrase resterait vraie
    à l’écran et fausse dans les faits."""
    preuve = next(p["preuve"] for s in C.SECTIONS for p in s["points"]
                  if p["cle"] == "inventaire")
    assert "COMMANDE TOUS LES AUTRES" in preuve
    s = P.sante()
    assert s["verrou_principal"]["cle"] == "inventaire"
    assert s["verrou_principal"]["bloque"] >= 10, s["verrou_principal"]
    d = P.evaluer([])
    assert d["verrous"][0]["cle"] == "inventaire"
    assert str(d["verrous"][0]["bloque"]) in d["lecture_parcours"]


def test_une_liste_entierement_cochee_n_a_plus_de_parcours():
    d = P.parcours(_toutes())
    assert d["vagues"] == [] and d["verrous"] == []
    assert "s'arrête ici" in _apo(d["lecture_parcours"])


# ═══════════════════════════════════════════════════════════════════════════
#  3. LA TABLE DES PRÉALABLES SE DÉFEND ARÊTE PAR ARÊTE
# ═══════════════════════════════════════════════════════════════════════════

def test_le_module_refuse_de_se_charger_sur_une_table_douteuse():
    """Une faute ici ne se voit pas à l’écran : elle se voit dans un parcours
    qui conseille l’ordre inverse, ce qui est pire qu’un parcours absent. Le
    contrôle vérifie que le REFUS FONCTIONNE, plutôt que de faire confiance à
    sa présence."""
    P._verifier()
    garde = P.PREALABLES
    raison = "Une raison assez longue pour passer le seuil des soixante signes exigés."
    fautes = [
        # préalable posé sur un point qui n’existe pas
        dict(garde, **{"zzz": [("inventaire", raison)]}),
        # préalable vers un point inconnu
        dict(garde, **{"veille": [("zzz", raison)]}),
        # point préalable de lui-même
        dict(garde, **{"veille": [("veille", raison)]}),
        # arête sans raison écrite : une préférence déguisée en contrainte
        dict(garde, **{"veille": [("inventaire", "parce que.")]}),
        # préalable en double
        dict(garde, **{"veille": [("inventaire", raison), ("inventaire", raison)]}),
        # CYCLE : rien ne serait jamais atteignable, et la page afficherait
        # « rien à faire » à qui n’a rien fait.
        dict(garde, **{"inventaire": [("politique", raison)],
                       "politique": [("inventaire", raison)]}),
    ]
    try:
        for f in fautes:
            P.PREALABLES = f
            try:
                P._verifier()
            except ValueError:
                continue
            raise AssertionError("table douteuse acceptée : %r" % (f.get("veille") or f,))
    finally:
        P.PREALABLES = garde
    P._verifier()


def test_chaque_arete_dit_pourquoi_elle_contraint():
    """Un préalable n’est pas une préférence de méthode : c’est un point sans
    lequel un autre NE PEUT PAS ÊTRE PROUVÉ. La raison écrite est ce qui
    distingue les deux, et elle est servie au client avec l’étape."""
    for cle, aretes in P.PREALABLES.items():
        for pre, pourquoi in aretes:
            assert len(pourquoi.strip()) >= 60, (cle, pre)
    d = P.parcours(["inventaire"])
    avec = [e for v in d["vagues"] for e in v["etapes"] if e["prealables"]]
    assert avec, "aucune étape ne montre ses préalables"
    for e in avec:
        for pre in e["prealables"]:
            assert pre["pourquoi"] and pre["libelle"]


def test_les_racines_sont_ce_par_quoi_on_peut_commencer_un_lundi():
    """Une première vague vide rendrait le parcours inutilisable pour qui
    part de zéro — et c’est exactement le cas d’usage."""
    racines = P.sante()["racines"]
    assert "inventaire" in racines and "politique" in racines
    assert 4 <= len(racines) <= 10, racines
    assert P.parcours([])["vagues"][0]["n"] == len(racines)


# ═══════════════════════════════════════════════════════════════════════════
#  4. LE DOCUMENT EMPORTÉ
# ═══════════════════════════════════════════════════════════════════════════

def test_le_document_porte_la_reserve_AVANT_les_chiffres():
    """Il circule sans sa page : transféré, imprimé, joint à un comité, relu
    six mois plus tard par quelqu’un qui n’a jamais vu ce site. Reléguée en
    pied, la réserve arriverait après la décision."""
    md = _apo(P.markdown(["politique", "inventaire"]))
    i_refus = md.index("Ce que ce document n'est pas")
    i_chiffres = md.index("Où vous en êtes")
    assert i_refus < i_chiffres, (i_refus, i_chiffres)
    assert "ML 1 à 4" in md and "SL 1 à 4" in md
    # ET IL DIT OÙ LE MOT EST LÉGITIME.
    assert "Où un niveau de maturité se constate" in md


def test_le_document_porte_les_preuves_et_l_ordre():
    """Une liste de tâches sans la preuve à produire est une liste de bonnes
    intentions ; c’est la preuve qu’un auditeur demande."""
    md = P.markdown([])
    assert "Preuve à produire" in md
    assert "Vague 1" in md and "Vague 2" in md
    assert "Libère" in md
    # LES VINGT-SEPT POINTS Y SONT, aucun perdu en route.
    for cle in _toutes():
        lib = next(p["libelle"] for s in C.SECTIONS for p in s["points"]
                   if p["cle"] == cle)
        assert lib in md, cle


def test_le_document_refuse_une_liste_qui_ne_se_recoupe_pas():
    assert P.markdown(["point_qui_n_existe_pas"]) is None


# ═══════════════════════════════════════════════════════════════════════════
#  5. LES ROUTES
# ═══════════════════════════════════════════════════════════════════════════

def test_les_deux_routes_sont_fermees_aux_visiteurs():
    """Le reste du menu l’est ; une route neuve qui ne l’est pas ouvre le
    périmètre sans que personne ne le décide."""
    c = A.app.test_client()
    for u in ("/api/62443/checklist/parcours", "/api/62443/checklist/emporter"):
        assert c.post(u, json={"coches": []}).status_code in (401, 403), u


def test_le_parcours_est_servi_et_porte_son_refus(client):
    r = client.post("/api/62443/checklist/parcours",
                    json={"coches": ["politique", "inventaire"]}, headers=H)
    assert r.status_code == 200
    d = r.get_json()
    assert d["ok"] and d["n_vagues"] >= 1
    assert "ML 1 à 4" in d["ce_que_ce_n_est_pas"]
    assert d["etat_preparation"]["coches"] == 2


def test_un_point_inconnu_est_refuse_sur_les_deux_routes(client):
    """La même porte que l’écran. Un format de sortie ne doit jamais devenir
    le chemin de contournement d’un contrôle — c’est la règle du site, et une
    route neuve est l’endroit exact où on l’oublie."""
    for u in ("/api/62443/checklist/parcours", "/api/62443/checklist/emporter"):
        r = client.post(u, json={"coches": ["inventaire", "zzz"]}, headers=H)
        assert r.status_code == 400, u
        assert r.get_json()["erreur"] == "points_inconnus", u


def test_les_deux_formats_sont_servis_et_le_troisieme_est_refuse(client):
    # LA SIGNATURE, PAS UNE TRANCHE FIXE : un .docx est une archive ZIP et
    # commence par PK\x03\x04, un PDF par %PDF-. Comparer quatre octets à deux
    # échouait sur le seul format qui n'a pas la même longueur de marque.
    for fmt, debut in (("pdf", b"%PDF"), ("docx", b"PK\x03\x04")):
        r = client.post("/api/62443/checklist/emporter",
                        json={"coches": ["inventaire"], "format": fmt}, headers=H)
        assert r.status_code == 200, (fmt, r.get_data()[:200])
        assert r.data.startswith(debut), fmt
        assert len(r.data) > 1000, fmt
        assert "attachment" in r.headers.get("Content-Disposition", "")
    r = client.post("/api/62443/checklist/emporter",
                    json={"coches": [], "format": "odt"}, headers=H)
    assert r.status_code == 400 and r.get_json()["error"] == "format_inconnu"


# ═══════════════════════════════════════════════════════════════════════════
#  6. LA PAGE EMPRUNTE LES JETONS DU SITE, PAS DES COULEURS À ELLE
# ═══════════════════════════════════════════════════════════════════════════

def test_le_parcours_n_ecrit_aucun_repli_de_couleur_clair():
    """DÉFAUT VU À L'ÉCRAN, ET IL NE S'ÉTAIT PAS ENCORE DÉCLENCHÉ. Les styles
    du parcours ont d'abord été écrits `var(--teal,#0e6d7c)` et
    `var(--bg2,#f6f8f9)` — deux valeurs de repli CLAIRES, sur un site dont le
    fond est un bordeaux (#6E2A18) et l'encre une crème (#F6F0E8).

    Elles ne se déclenchaient pas, les variables existant toutes. Elles
    n'attendaient qu'un renommage pour poser du texte crème sur du blanc. Un
    repli qu'on n'a pas mesuré sur le vrai thème n'est pas un filet de
    sécurité : c'est une panne différée, et elle ne se verrait que chez le
    lecteur."""
    html = open(os.path.join(ICI, "checklist-62443.html"), encoding="utf-8").read()
    # LE COMMENTAIRE A LE DROIT DE LES NOMMER — c'est son travail d'expliquer
    # ce qui a été écarté. Le CODE, non.
    sans_com = re.sub(r"/\*.*?\*/", "", html, flags=re.S)
    replis = re.findall(r"var\(--[a-z0-9-]+\s*,\s*([^)]+)\)", sans_com)
    assert not replis, "repli de couleur écrit à la main : %s" % replis

    # ET LES CLASSES DU PARCOURS EXISTENT VRAIMENT, avec les jetons du site.
    for classe in (".ck-vg{", ".ck-vg-t{", ".ck-et{", ".ck-vr{"):
        assert classe in sans_com, classe
    for jeton in ("var(--panel)", "var(--panel2)", "var(--line)",
                  "var(--ink)", "var(--muted)", "var(--cyan)"):
        assert jeton in sans_com, jeton


def test_la_page_appelle_les_deux_routes_neuves():
    """Une route servie que la page n'appelle pas est une route morte ; un
    bouton qui n'appelle rien est pire."""
    html = open(os.path.join(ICI, "checklist-62443.html"), encoding="utf-8").read()
    assert "/api/62443/checklist/parcours" in html
    assert "/api/62443/checklist/emporter" in html
    # LES DEUX BOUTONS SONT ÉCRITS DÉSACTIVÉS, comme les deux autres, et
    # s'ouvrent quand le référentiel est là : un clic pendant le chargement
    # enverrait une liste vide et rendrait un document qui ne dit rien.
    for bid in ("ck-pdf", "ck-docx"):
        i = html.index('id="%s"' % bid)
        assert "disabled" in html[i:i + 120], bid
        assert '$("#%s").disabled = false' % bid in html, bid
