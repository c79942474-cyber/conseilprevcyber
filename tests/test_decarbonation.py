"""La plateforme de décarbonation — et la règle qui la gouverne.

CE QUE CETTE PLATEFORME AJOUTE. Le moteur calcule une énergie, une eau, un
carbone. Le cadre de phases dit à quel moment d'un PROJET ces chiffres
deviennent recevables. Il manquait la question du directeur de la durabilité :
dans quel ordre décarbone-t-on, et qu'a-t-on le droit d'en dire ?

CE QUE CES TESTS PROTÈGENT, ET LE PREMIER POINT EST TOUT LE SUJET :

  1. LA COMPENSATION N'EST PAS UNE RÉDUCTION, ET CE N'EST PAS UNE OPINION
     ÉCRITE DANS UN PARAGRAPHE — c'est une contrainte de structure. Un levier
     de rang « compenser » ne peut porter aucun paramètre du moteur, et le
     module refuse de se charger s'il en porte un. Sans ce verrou, la page
     afficherait un « résultat » de compensation au même rang qu'un gain
     d'efficacité, et le lecteur additionnerait les deux — l'addition même que
     les autorités de la publicité sanctionnent. On le vérifie en essayant de
     la violer.

  2. L'ORDRE DE LA HIÉRARCHIE EST L'INFORMATION. `hierarchie()` rend les rangs
     dans l'ordre éviter → réduire → substituer → résiduel, toujours. Un tri
     par gain attendu ferait remonter la compensation, la plus rapide à
     acheter et la seule qui ne réduise rien.

  3. AUCUNE INCERTITUDE N'EST RECOPIÉE. Les postes de substitution sont LUS
     dans `ingenierie_dc`, qui les lit lui-même dans `datacenter`. Une valeur
     retapée ici aurait divergé au premier ajustement du référentiel — et
     c'est le cadre qu'on aurait cru. On le prouve en déplaçant la source et
     en exigeant que la sortie suive.

  4. UN CHAMP PAR DÉFAUT N'EST PAS UN CHAMP RENSEIGNÉ. Une année de référence
     établie sur le taux de charge par défaut d'un formulaire n'est pas une
     référence : toute réduction mesurée contre elle serait fictive. L'étape
     doit rester bloquée.

  5. LA FRONTIÈRE OUVERT / FERMÉ. La plateforme s'ouvre parce que son calcul
     est déterministe et n'appartient à personne. Les pièces du cabinet, elles,
     ne s'ouvrent pas — on vérifie les deux sens.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import datacenter as dc  # noqa: E402
import decarbonation as dk  # noqa: E402
import ingenierie_dc as ig  # noqa: E402
import app as A  # noqa: E402

# Un profil VRAIMENT renseigné : chaque valeur s'écarte du pré-remplissage du
# formulaire, sans quoi les étapes resteraient bloquées pour cette raison-là et
# les contrôles ci-dessous mesureraient autre chose que ce qu'ils annoncent.
PROFIL = {"puissance_it_kw": 50000, "pays": "FR",
          "refroidissement": "tour_evaporative", "taux_charge": 0.72,
          "classe_ashrae": "A3", "part_evaporative": 0.8,
          "cycles_concentration": 6, "part_renouvelable": 0.4,
          "part_chaleur_reutilisee": 0.15, "intensite_reseau_g": 48}


@pytest.fixture
def client():
    return A.app.test_client()


# ── 1. La compensation ne peut pas se déguiser en réduction ────────────────

def test_aucun_levier_de_compensation_ne_porte_un_parametre_du_moteur():
    for lv in dk.LEVIERS:
        if lv["rang"] == "compenser":
            assert not lv.get("champ"), lv["cle"]


def test_le_module_refuse_un_levier_de_compensation_qui_calculerait(monkeypatch):
    """LE contrôle du module. On tente exactement la dérive redoutée : donner un
    paramètre à la compensation pour qu'elle s'affiche comme un levier
    d'ingénierie."""
    trafique = []
    for lv in dk.LEVIERS:
        c = dict(lv)
        if c["rang"] == "compenser":
            c["champ"] = "part_renouvelable"
        trafique.append(c)
    monkeypatch.setattr(dk, "LEVIERS", trafique)
    fautes = dk._verifier()
    assert any("compensation ne peut porter" in f for f in fautes), fautes


def test_le_levier_sans_parametre_dit_pourquoi():
    """Une absence non expliquée se lit comme un oubli, et un oubli se
    « corrige » en inventant un paramètre."""
    for lv in dk.LEVIERS:
        if not lv.get("champ"):
            assert len(lv.get("sans_champ") or "") > 80, lv["cle"]


def test_le_module_refuse_un_levier_muet_sur_son_absence(monkeypatch):
    trafique = []
    for lv in dk.LEVIERS:
        c = dict(lv)
        c.pop("sans_champ", None)
        trafique.append(c)
    monkeypatch.setattr(dk, "LEVIERS", trafique)
    fautes = dk._verifier()
    assert any("sans paramètre et sans explication" in f for f in fautes), fautes


def test_la_sante_est_verte_en_etat_normal():
    assert dk.sante()["problemes"] == []


# ── 2. L'ordre de la hiérarchie ────────────────────────────────────────────

def test_la_hierarchie_sort_toujours_dans_son_ordre():
    h = dk.hierarchie()
    assert [r["cle"] for r in h] == ["eviter", "reduire", "substituer", "compenser"]
    assert [r["rang"] for r in h] == [1, 2, 3, 4]


def test_les_quatre_rangs_portent_chacun_au_moins_un_levier():
    """Un rang vide donnerait une hiérarchie amputée sans que rien ne le
    signale."""
    for r in dk.hierarchie():
        assert r["leviers"], r["cle"]


def test_les_etapes_de_la_voie_reduire_suivent_la_hierarchie():
    """C'est la colonne de la voie : éviter, puis réduire, puis substituer,
    puis le résiduel. Un levier de substitution rattaché à l'étape d'évitement
    ferait lire la page à l'envers — l'inversion même qu'on reproche aux plans
    de décarbonation."""
    vus = []
    for e in sorted([x for x in dk.ETAPES if x["voie"] == "trajectoire"],
                    key=lambda x: x["rang"]):
        rangs = {dk._LEVIER[c]["rang"] for c in e.get("leviers", [])}
        if rangs:
            assert len(rangs) == 1, (e["code"], rangs)
            vus.append(rangs.pop())
    assert vus == ["eviter", "reduire", "substituer", "compenser"]


def test_le_module_refuse_un_levier_range_a_contre_ordre(monkeypatch):
    etapes = []
    for e in dk.ETAPES:
        c = dict(e)
        if c["code"] == "EVIT":
            c["leviers"] = ["contrat"]          # substitution rangée en évitement
        if c["code"] == "SUBST":
            c["leviers"] = ["puissance", "charge", "pays", "chaleur",
                            "reseau_contrat"]
        etapes.append(c)
    monkeypatch.setattr(dk, "ETAPES", etapes)
    fautes = dk._verifier()
    assert any("rang" in f for f in fautes), fautes


def test_chaque_levier_dit_ce_qu_il_ne_fait_pas_et_son_piege():
    """Un levier qui n'annonce que son gain est un argumentaire."""
    for lv in dk.LEVIERS:
        assert len(lv["ne_fait_pas"]) > 60, lv["cle"]
        assert len(lv["piege"]) > 60, lv["cle"]


def test_chaque_levier_relie_au_moteur_nomme_un_champ_qui_existe():
    champs = {c["id"] for c in dc.CHAMPS}
    for lv in dk.LEVIERS:
        if lv.get("champ"):
            assert lv["champ"] in champs, (lv["cle"], lv["champ"])


def test_aucun_levier_ne_pend_dans_le_vide():
    """Un levier dont le paramètre n'est jamais exigé conseillerait d'agir sur
    une grandeur que le parcours ne demande jamais de renseigner."""
    exiges = set()
    for e in dk.ETAPES:
        if e["voie"] == "trajectoire":
            exiges |= set(e["exige"])
    for lv in dk.LEVIERS:
        if lv.get("champ"):
            assert lv["champ"] in exiges, lv["cle"]


# ── 3. Rien n'est recopié du moteur ────────────────────────────────────────

def test_les_incertitudes_sont_lues_et_non_recopiees(monkeypatch):
    """LE contrôle du point 3 : on déplace la valeur À LA SOURCE et on exige
    que la sortie suive. Si elle ne bouge pas, c'est qu'une copie dort ici."""
    postes = {k: dict(v) for k, v in ig.POSTES.items()}
    postes["incorpore"]["incertitude"] = "±99 %"
    monkeypatch.setattr(ig, "POSTES", postes)
    a = dk.aptitude(PROFIL, "VERIF")
    vu = [s["incertitude"] for s in a["substitutions_a_faire"]
          if s["cle"] == "incorpore"]
    assert vu == ["±99 %"], vu


def test_les_substitutions_nomment_des_postes_qui_existent():
    for e in dk.ETAPES:
        for s in e["substitutions"]:
            assert s in ig.POSTES, (e["code"], s)


def test_les_postes_qui_bloquent_une_grandeur_existent():
    """Une clé inventée ici ne lève rien : elle ne correspond à aucune
    substitution, la grandeur reste « recevable » quoi qu'il arrive, et
    l'avertissement qu'on croyait avoir posé n'est jamais affiché."""
    for g, postes in dk._ENGAGE.items():
        for cle in postes:
            assert cle in ig.POSTES, (g, cle)


def test_une_grandeur_bloquee_le_dit_et_nomme_ce_qui_la_bloque():
    d = dk.dossier(PROFIL, "KPI")
    par_cle = {g["cle"]: g for g in d["grandeurs"]}
    assert par_cle["pue"]["statut"] == "a_remplacer"
    assert par_cle["pue"]["postes_bloquants"], par_cle["pue"]
    # L'eau de site ne dépend d'aucun poste bloquant à cette étape : elle doit
    # rester recevable, sinon l'avertissement perd tout pouvoir de distinction.
    assert par_cle["eau_site"]["statut"] == "recevable"


# ── 4. Un champ par défaut n'est pas un champ renseigné ────────────────────

def test_l_annee_de_reference_reste_bloquee_sur_un_taux_de_charge_par_defaut():
    """Une référence établie sur le pré-remplissage d'un formulaire n'est pas
    une référence : toute réduction mesurée contre elle serait fictive."""
    defaut = next(c for c in dc.CHAMPS if c["id"] == "taux_charge")["defaut"]
    p = dict(PROFIL, taux_charge=defaut)
    a = dk.aptitude(p, "REF")
    assert not a["franchissable"]
    assert any(m["id"] == "taux_charge" and m["etat"] == "defaut"
               for m in a["entrees_manquantes"]), a["entrees_manquantes"]


def test_la_meme_etape_passe_des_que_la_valeur_est_choisie():
    """La moitié qui prouve que le contrôle précédent discrimine : en changeant
    la seule valeur en cause, l'étape doit s'ouvrir."""
    a = dk.aptitude(PROFIL, "REF")
    assert a["franchissable"], a["verdict"]


def test_une_dette_heritee_est_distinguee_d_un_oubli_propre():
    """On ne traite pas de la même façon un oubli de l'étape en cours et une
    dette laissée par la précédente."""
    a = dk.aptitude({"puissance_it_kw": 50000}, "REDUI")
    origines = {m["origine"] for m in a["entrees_manquantes"]}
    assert origines == {"propre", "heritee"}, origines


def test_le_parcours_designe_le_premier_blocage_et_pas_un_autre():
    p = dk.parcours({"puissance_it_kw": 50000}, "trajectoire")
    assert p["premier_blocage"] == "DIAG"
    assert p["n_franchissables"] == 0
    # Le profil complet débloque les trois premières étapes ; il bute sur
    # l'efficacité, qui réclame une courbe d'équipement et non une plage de
    # conception. Le blocage a donc AVANCÉ, ce qui est le comportement utile.
    p2 = dk.parcours(PROFIL, "trajectoire")
    assert p2["premier_blocage"] == "REDUI", p2["premier_blocage"]
    assert p2["n_franchissables"] == 3


def test_une_substitution_que_le_formulaire_satisfait_cesse_de_bloquer():
    """Contrepartie exacte de la règle « un défaut n'est pas une saisie » : une
    valeur réellement choisie doit COMPTER. Sans cela, le parcours reste
    infranchissable quoi qu'on saisisse — et une frise où rien ne peut passer
    au vert n'apprend rien à personne."""
    sans = dk.aptitude({k: v for k, v in PROFIL.items()
                        if k != "intensite_reseau_g"}, "CIBLE")
    assert [s["cle"] for s in sans["substitutions_a_faire"]] == ["intensite"]
    assert not sans["franchissable"]

    avec = dk.aptitude(PROFIL, "CIBLE")
    assert avec["substitutions_a_faire"] == []
    assert [s["cle"] for s in avec["substitutions_faites"]] == ["intensite"]
    assert avec["franchissable"]


def test_une_substitution_qu_aucun_champ_ne_satisfait_reste_ouverte():
    """L'autre moitié, et la plus importante : le carbone incorporé vient de
    déclarations produit, pas d'un formulaire. Aucune saisie ne doit pouvoir
    fermer cette étape — sinon la plateforme délivrerait une allégation de
    neutralité sur un dossier vide."""
    complet = dict(PROFIL, pue_cible=1.25)
    a = dk.aptitude(complet, "RESID")
    assert not a["franchissable"]
    assert [s["cle"] for s in a["substitutions_a_faire"]] == ["incorpore"]
    assert "incorpore" not in dk.SATISFAIT_PAR


def test_la_satisfaction_ne_se_declenche_pas_sur_un_pre_remplissage():
    """`pue_cible` n'a pas de valeur par défaut ; `taux_charge` en a une. Le
    contrôle porte sur le mécanisme : c'est l'état SAISI de profil_dc qui
    décide, jamais la simple présence d'une clé."""
    p = dict(PROFIL)
    p["intensite_reseau_g"] = ""
    a = dk.aptitude(p, "CIBLE")
    assert [s["cle"] for s in a["substitutions_a_faire"]] == ["intensite"]


# ── 5. Les textes, et ce qu'ils pèsent ─────────────────────────────────────

def test_chaque_texte_porte_une_portee_connue():
    for cle, t in dk.TEXTES.items():
        assert t["portee"] in dk.PORTEES, cle


def test_la_portee_survit_jusqu_au_referentiel_servi():
    """Un règlement européen et un engagement de place ne s'opposent pas de la
    même façon. Perdre l'étiquette en chemin ferait promettre une obligation là
    où il n'y a qu'un engagement — ou l'inverse, plus grave."""
    for t in dk.referentiel()["textes"]:
        assert t["portee"] in dk.PORTEES
        assert t["portee_texte"], t["cle"]


def test_aucun_texte_n_est_cite_par_zero_etape():
    appeles = {t for e in dk.ETAPES for t in e["textes"]}
    assert set(dk.TEXTES) == appeles, set(dk.TEXTES) - appeles


def test_le_module_refuse_un_texte_que_personne_n_appelle(monkeypatch):
    textes = dict(dk.TEXTES)
    textes["inutile"] = {"nom": "Texte non appelé", "portee": "norme",
                         "dit": "…"}
    monkeypatch.setattr(dk, "TEXTES", textes)
    fautes = dk._verifier()
    assert any("cité par aucune étape" in f for f in fautes), fautes


def test_les_quatre_portees_sont_effectivement_servies():
    """Si toutes les sources tombaient dans une seule catégorie, la
    distinction ne distinguerait plus rien."""
    vues = {t["portee"] for t in dk.TEXTES.values()}
    assert vues == set(dk.PORTEES), vues


# ── 6. La structure des deux voies ─────────────────────────────────────────

def test_aucune_etape_fantome():
    """Une étape qui n'ajoute ni entrée, ni substitution, ni texte allonge la
    frise et donne le sentiment d'un travail là où il n'y en a pas."""
    for v in dk.VOIES:
        vus_e, vus_s, vus_t = set(), set(), set()
        for e in sorted([x for x in dk.ETAPES if x["voie"] == v],
                        key=lambda x: x["rang"]):
            neuf = ((set(e["exige"]) - vus_e) | (set(e["substitutions"]) - vus_s)
                    | (set(e["textes"]) - vus_t))
            assert neuf, e["code"]
            vus_e |= set(e["exige"])
            vus_s |= set(e["substitutions"])
            vus_t |= set(e["textes"])


def test_les_rendez_vous_pointent_vers_des_etapes_reelles():
    for r in dk.RENDEZ_VOUS:
        for voie in ("inventaire", "trajectoire"):
            e = dk._PAR_CODE.get(r[voie])
            assert e is not None, r
            assert e["voie"] == voie, r
        assert len(r["lien"]) > 60, r


def test_chaque_etape_dit_ce_qu_elle_verrouille_et_ce_qui_la_prouve():
    for e in dk.ETAPES:
        assert len(e["verrouille"]) > 40, e["code"]
        assert len(e["preuve"]) > 60, e["code"]
        assert e["livrable"], e["code"]


def test_les_champs_exiges_existent_dans_le_moteur():
    champs = {c["id"] for c in dc.CHAMPS}
    for e in dk.ETAPES:
        for cid in e["exige"]:
            assert cid in champs, (e["code"], cid)


# ── 7. La frontière ouvert / fermé ─────────────────────────────────────────

def test_la_page_est_ouverte_sans_compte(client):
    r = client.get("/decarbonation-datacenter")
    assert r.status_code == 200, r.status_code


def test_le_referentiel_est_ouvert(client):
    r = client.get("/api/datacenter/decarbonation")
    assert r.status_code == 200
    j = r.get_json()
    assert j["ok"] is True
    assert len(j["referentiel"]["hierarchie"]) == 4


@pytest.mark.parametrize("chemin,charge", [
    ("/api/datacenter/decarbonation/parcours", dict(PROFIL)),
    ("/api/datacenter/decarbonation/dossier", dict(PROFIL, etape="SUBST")),
])
def test_le_parcours_et_le_dossier_sont_ouverts(client, chemin, charge):
    r = client.post(chemin, headers={"Origin": "http://localhost"}, json=charge)
    assert r.status_code == 200, (chemin, r.status_code)
    assert r.get_json()["ok"] is True


def test_ouvrir_la_plateforme_n_a_rien_ouvert_d_autre(client):
    """La moitié du contrôle qui compte vraiment."""
    for chemin in ("/api/datacenter/ingenierie/dossier",
                   "/api/datacenter/ingenierie/export",
                   "/api/datacenter/export"):
        r = client.post(chemin, headers={"Origin": "http://localhost"}, json={})
        assert r.status_code == 401, (chemin, r.status_code)


def test_le_dossier_refuse_une_etape_inconnue(client):
    r = client.post("/api/datacenter/decarbonation/dossier",
                    headers={"Origin": "http://localhost"},
                    json=dict(PROFIL, etape="NEXISTEPAS"))
    assert r.status_code == 404


def test_le_parcours_refuse_un_profil_sans_puissance(client):
    r = client.post("/api/datacenter/decarbonation/parcours",
                    headers={"Origin": "http://localhost"}, json={"pays": "FR"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "puissance_absente"


def test_la_plateforme_ouverte_est_plafonnee():
    """Ouvrir une surface de calcul sans plafond, c'est offrir un
    amplificateur."""
    assert "/api/datacenter/" in [p for p, _, _ in A._RATE_FAMILY]


# ── 8. La page, et le chemin qui y mène ────────────────────────────────────

def _lire(nom):
    with open(os.path.join(ICI, nom), encoding="utf-8") as f:
        return f.read()


def test_la_page_porte_les_quatre_sections_de_la_plateforme():
    h = _lire("decarbonation-datacenter.html")
    for cible in ('id="dk-form"', 'id="dk-voies"', 'id="dk-parcours"',
                  'id="dk-dossier"', 'id="dk-hierarchie"', 'id="dk-textes"'):
        assert cible in h, cible


def test_la_page_sustainability_conduit_a_la_plateforme():
    """Une plateforme qu'on n'atteint pas depuis la page dont elle dépend
    n'existe que pour qui connaît son adresse."""
    assert 'href="/decarbonation-datacenter"' in _lire("datacenter.html")


def test_la_plateforme_est_indexable():
    h = _lire("decarbonation-datacenter.html")
    assert 'content="index, follow"' in h
    assert "noindex" not in h


def test_la_page_annonce_la_regle_avant_de_la_faire_appliquer():
    """La règle du module doit être lisible par un humain, pas seulement
    vérifiée par un test."""
    h = _lire("decarbonation-datacenter.html")
    assert "compensation n'est pas une réduction" in h
