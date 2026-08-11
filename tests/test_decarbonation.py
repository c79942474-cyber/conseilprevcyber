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
import re
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
    r = client.get("/datacenter")
    assert r.status_code == 200, r.status_code


def test_l_ancienne_adresse_redirige_au_lieu_de_disparaitre():
    """La décarbonation avait sa page ; elle a fusionné. L'adresse a figuré
    dans un sitemap et dans des échanges — la supprimer sèchement ferait perdre
    le lecteur au lieu de le déplacer."""
    r = A.app.test_client().get("/decarbonation-datacenter")
    assert r.status_code == 301, r.status_code
    assert r.headers["Location"].startswith("/datacenter#")


def test_l_ancienne_adresse_ne_figure_plus_au_sitemap(client):
    """Une redirection permanente n'a rien à faire dans un sitemap : on y
    déclare des pages, pas des renvois."""
    x = client.get("/sitemap.xml").get_data(as_text=True)
    assert "/decarbonation-datacenter" not in x
    assert "/datacenter<" in x or "/datacenter</loc>" in x


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


def test_la_page_fusionnee_porte_les_sections_de_la_plateforme():
    h = _lire("datacenter.html")
    for cible in ('id="dk-voies"', 'id="dk-parcours"', 'id="dk-dossier"',
                  'id="dk-hierarchie"', 'id="dk-textes"'):
        assert cible in h, cible


def test_un_seul_formulaire_de_profil_sur_la_page():
    """LE contrôle de la fusion. Les deux pages construisaient chacune le même
    formulaire depuis le même référentiel : le visiteur saisissait deux fois la
    même puissance, et les deux copies divergeaient dès la première frappe."""
    with open(os.path.join(ICI, "decarbonation-dc.js"), encoding="utf-8") as f:
        js = f.read()
    assert "dk-form" not in js, "la décarbonation rebâtit un second formulaire"
    assert '#dc-form [data-champ]' in js
    h = _lire("datacenter.html")
    assert h.count('id="dc-form"') == 1


def test_aucun_lien_ne_pointe_vers_la_page_disparue():
    """Un lien vers une page fusionnée renvoie le lecteur à un endroit qu'il
    vient de quitter."""
    for nom in ("datacenter.html", "strategie-durable-datacenter.html", "nav.js"):
        with open(os.path.join(ICI, nom), encoding="utf-8") as f:
            assert "/decarbonation-datacenter" not in f.read(), nom


def test_le_menu_ne_porte_qu_une_entree_pour_les_deux():
    """L'INTENTION, pas un compte. La première version de ce test figeait
    `nav.count('"/datacenter"') == 2` : ajouter un guide de page qui renvoie
    vers /datacenter l'a fait tomber, alors que le menu n'avait pas bougé. Un
    garde qui compte des occurrences dans un fichier entier se répare
    machinalement et cesse de protéger. On regarde donc la LISTE du tiroir."""
    with open(os.path.join(ICI, "nav.js"), encoding="utf-8") as f:
        nav = f.read()
    entrees = re.findall(r'\[\s*"(/[a-z0-9\-]*datacenter[a-z0-9\-]*)"\s*,\s*"',
                         nav)
    assert entrees.count("/datacenter") == 1, entrees
    assert "/decarbonation-datacenter" not in entrees, entrees
    assert "decarbonation-datacenter" not in nav


def test_la_page_fusionnee_est_indexable():
    h = _lire("datacenter.html")
    assert 'content="index, follow"' in h
    assert "noindex" not in h


def test_le_sommaire_ne_porte_aucune_ancre_morte():
    """La fusion a produit une page longue, d'où le sommaire. Une ancre qui ne
    mène nulle part est pire qu'une ancre absente : elle promet un chapitre et
    laisse le lecteur en haut de page sans rien dire."""
    h = _lire("datacenter.html")
    somm = h[h.index('class="dc-somm"'):h.index("</nav>", h.index('class="dc-somm"'))]
    ancres = re.findall(r'href="#([^"]+)"', somm)
    assert len(ancres) >= 8, ancres
    for a in ancres:
        assert 'id="%s"' % a in h, a


def test_le_sommaire_ne_renvoie_pas_aux_sections_masquees():
    """Résultats et comparaison n'existent qu'après un calcul. Les mettre au
    sommaire donnerait deux liens qui ne font rien tant qu'on n'a rien lancé."""
    h = _lire("datacenter.html")
    somm = h[h.index('class="dc-somm"'):h.index("</nav>", h.index('class="dc-somm"'))]
    for masquee in ("dc-sec-res", "dc-sec-comp"):
        assert masquee not in somm, masquee
    # …mais leur absence est EXPLIQUÉE : un sommaire qui saute deux numéros
    # sans rien dire laisse chercher deux chapitres qui n'existent pas encore.
    assert "calcul lancé" in somm


def test_la_page_ne_repete_pas_trois_fois_qu_elle_ne_decerne_aucun_label():
    """Trois modules portaient chacun leur avertissement ; réunis sur une page,
    ils le disaient trois fois. Une mise en garde répétée cesse d'être lue."""
    h = _lire("datacenter.html")
    assert h.count("aucune conformité") <= 1, h.count("aucune conformité")


def test_le_titre_de_la_page_est_conserve():
    """La fusion ne devait rien coûter au titre : c'est lui qui nomme l'offre."""
    h = _lire("datacenter.html")
    assert "Data Center Sustainability &amp; Decarbonisation" in h
    assert "Énergie, eau et carbone — calculés ensemble" in h


def test_la_page_annonce_la_regle_avant_de_la_faire_appliquer():
    """La règle du module doit être lisible par un humain, pas seulement
    vérifiée par un test."""
    h = _lire("datacenter.html")
    assert "compensation n'est pas une réduction" in h


# ═══════════════════════════════════════════════════════════════════════════
#  LE CHOIX DU RANG — une liste déroulante qui ne doit pas défaire l'ordre
# ═══════════════════════════════════════════════════════════════════════════
# Les quatre rangs et leurs onze leviers se dépliaient d'un coup : un mur de
# plusieurs écrans qu'on parcourt sans le lire. Le rang se choisit maintenant.
#
# LE RISQUE DE CE CHANGEMENT EST DE FOND, PAS D'ERGONOMIE. Cette section
# n'enseigne pas quatre familles de leviers : elle enseigne un ORDRE. Une liste
# qui laisse ouvrir « Compenser » sans avoir jamais vu qu'il existe trois rangs
# au-dessus ferait dire à l'interface le contraire de ce que la page démontre —
# et c'est précisément l'erreur que la page existe pour empêcher.

def test_le_rang_se_choisit_dans_une_liste():
    js = _lire("decarbonation-dc.js")
    assert 'id="dk-rang"' in js
    assert "<select" in js[js.index("function rendreHierarchie"):
                           js.index("function rendreHierarchie") + 2600]


def test_les_options_portent_leur_numero_donc_la_sequence_se_lit_fermee():
    """L'ordre doit rester lisible SANS ouvrir la liste : c'est la seule chose
    que le repliement risquait de faire perdre."""
    js = _lire("decarbonation-dc.js")
    i = js.index("function rendreHierarchie")
    bloc = js[i:i + 2600]
    assert 'r.rang + ". " + r.nom' in bloc, (
        "l'option doit porter le numéro du rang, pas seulement son nom")


def test_le_rang_ouvert_rappelle_sa_position():
    js = _lire("decarbonation-dc.js")
    i = js.index("function rendreHierarchie")
    assert '" sur "' in js[i:i + 3000], "« rang 3 sur 4 » et non « rang 3 »"


def test_le_rappel_des_rangs_amont_est_ecrit_et_atteignable():
    """LE CONTRÔLE QUI COMPTE — mais VÉRIFIÉ AILLEURS, et il faut le dire.

    Sans rappel des rangs amont, la liste transformerait une condition de
    recevabilité en menu de self-service. Ce test-ci ne peut cependant
    constater que la PRÉSENCE des chaînes dans le fichier : j'ai désactivé la
    branche qui les affiche — « if (amont.length) » remplacé par « if (false) »
    — et il est resté vert. Un test qui lit le source ne voit pas ce qui est
    devenu inatteignable, et il aurait rendu le défaut permanent.

    Ce qui prouve réellement l'affichage est dans recette_decarbonation.js, qui
    choisit le rang 4 dans la vraie page et exige d'y lire les trois rangs
    amont. Ce test ne garde donc que le matériau ; la preuve est au navigateur.
    """
    js = _lire("decarbonation-dc.js")
    i = js.index("function rendreHierarchie")
    bloc = js[i:i + 3600]
    assert "x.rang < r.rang" in bloc, "les rangs amont doivent être calculés"
    assert "À instruire avant ce rang" in bloc
    assert "data-dk-rang-go" in bloc, "et chacun doit être atteignable d'un clic"


def test_la_liste_s_ouvre_sur_le_premier_rang():
    """Commencer ailleurs qu'en haut de la hiérarchie apprendrait le contraire
    de la méthode dès le premier écran."""
    js = _lire("decarbonation-dc.js")
    i = js.index("function rendreHierarchie")
    assert "RANG_VU = rangs[0].rang" in js[i:i + 1400]


def test_la_page_dit_toujours_pourquoi_l_ordre_s_impose():
    """Le texte de la section porte la justification ; la liste ne doit pas
    l'avoir emportée avec le dépliement."""
    h = _lire("datacenter.html")
    assert "n'est pas une préférence morale" in h
    assert "ISO 14068-1" in h


# ═══════════════════════════════════════════════════════════════════════════
#  LE CHOIX DE LA PORTÉE — une liste qui ne doit pas cacher ce qui oblige
# ═══════════════════════════════════════════════════════════════════════════
# Dix-sept textes se dépliaient d'un coup. La portée se choisit maintenant.
#
# LE RISQUE EST LE SUJET MÊME DE LA SECTION. Elle n'aligne pas dix-sept
# références : elle enseigne qu'elles NE PÈSENT PAS PAREIL. Un lecteur qui
# n'ouvrirait que « méthode de place » ignorerait qu'il existe cinq textes qui
# l'obligent — exactement l'erreur que la page existe pour empêcher.

def test_l_ordre_de_poids_est_declare_et_non_deduit():
    """`PORTEES` est écrit dans le bon ordre, mais la sérialisation JSON TRIE
    les clés : servi tel quel, le vocabulaire arrivait à la page par ordre
    ALPHABÉTIQUE — « engagement de place » avant « texte contraignant »."""
    assert dk.PORTEES_ORDRE[0] == "contraignant"
    assert sorted(dk.PORTEES_ORDRE) == sorted(dk.PORTEES)


def test_le_module_refuse_de_charger_si_l_ordre_n_ouvre_pas_sur_ce_qui_oblige():
    """PROUVÉ, PAS AFFIRMÉ. Ce garde est plus fort qu'un test : le site ne
    démarre pas avec un vocabulaire mal classé."""
    sauve = list(dk.PORTEES_ORDRE)
    try:
        dk.PORTEES_ORDRE[:] = ["auto_regulation", "contraignant", "methode", "norme"]
        f = dk._verifier()
        assert any("commence pas par ce qui oblige" in x for x in f), f
    finally:
        dk.PORTEES_ORDRE[:] = sauve
    assert dk._verifier() == []


def test_une_portee_ajoutee_sans_etre_classee_est_refusee():
    """Elle sortirait en fin de liste par hasard, ou pas du tout — et
    l'interface s'ouvrirait alors sur autre chose que ce qui oblige."""
    sauve = dict(dk.PORTEES)
    try:
        dk.PORTEES["recommandation"] = "Recommandation sans portée juridique."
        f = dk._verifier()
        assert any("ne couvre pas le" in x for x in f), f
    finally:
        dk.PORTEES.clear()
        dk.PORTEES.update(sauve)
    assert dk._verifier() == []


def test_le_referentiel_sert_l_ordre_comme_une_liste():
    """Une liste survit à la sérialisation ; un dictionnaire, non."""
    r = dk.referentiel()
    assert [x["cle"] for x in r["portees_ordre"]] == dk.PORTEES_ORDRE
    assert all(x["texte"] for x in r["portees_ordre"])


def test_les_textes_sortent_dans_l_ordre_de_poids():
    r = dk.referentiel()
    rangs = [dk.PORTEES_ORDRE.index(t["portee"]) for t in r["textes"]]
    assert rangs == sorted(rangs), [t["portee"] for t in r["textes"]]


def test_le_contraignant_n_est_pas_vide():
    """Une portée « contraignant » sans texte ferait ouvrir la section sur une
    page blanche — et laisserait croire que rien n'oblige."""
    r = dk.referentiel()
    assert len([t for t in r["textes"] if t["portee"] == "contraignant"]) >= 3


def test_la_page_rappelle_ce_qui_oblige_hors_du_contraignant():
    """Contrôle de MATÉRIAU seulement : la branche d'affichage est vérifiée par
    recette_decarbonation.js, qui choisit une portée non contraignante dans le
    vrai document et exige d'y lire le rappel. Un test qui lit le source ne
    voit pas ce qui est devenu inatteignable — la leçon du rang de la
    hiérarchie, où « if (false) » avait laissé le test vert."""
    js = _lire("decarbonation-dc.js")
    i = js.index("function rendreTextes")
    bloc = js[i:i + 4200]
    assert 'p.cle !== "contraignant"' in bloc
    assert "n’oblige pas par elle-même" in bloc
    assert "data-dk-portee-go" in bloc


def test_la_definition_de_portee_n_est_pas_repetee_sous_chaque_texte():
    """Elle est énoncée une fois en tête. L'écrire sous chacun des six textes
    la ferait lire zéro fois. Elle reste en revanche indispensable dans le
    dossier d'une étape, qui mêle des portées différentes."""
    js = _lire("decarbonation-dc.js")
    assert "function bloctexte(t, sansPortee)" in js
    assert "bloctexte(t, true)" in js, "la section 8 la supprime"
    assert "h += bloctexte(t);" in js, "le dossier d'étape la conserve"
