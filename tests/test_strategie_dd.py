"""La stratégie DD d'un centre de données — le premier livrable, et sa règle.

CE QUE CE MODULE PRODUIT. Le document qu'on écrit AVANT de calculer : il ne dit
pas combien, il dit sur quoi porte l'étude, ce qu'on écarte, et pourquoi. Un
questionnaire client alimente trois perspectives sur quatre ; la quatrième est
établie par les données.

CE QUE CES TESTS PROTÈGENT, ET LE PREMIER POINT EST TOUT LE SUJET :

  1. LA SCIENCE N'EST PAS UNE OPINION DU CLIENT. Le questionnaire ne la propose
     jamais, et une note glissée dans cette colonne n'a aucun effet. Sans ce
     verrou, la page recueillerait un avis et l'afficherait comme une mesure —
     et les écarts perception/réalité, qui sont l'apport central de la méthode,
     deviendraient indétectables puisque les deux colonnes diraient la même
     chose. On le vérifie en essayant de tricher.

  2. LES DIVERGENCES NE SONT PAS MOYENNÉES. Un enjeu que les données minorent
     et que l'opinion tient pour central reste retenu — tant que l'opinion le
     tient pour l'enjeu principal, c'est un problème à traiter. Et l'inverse,
     plus dangereux parce que silencieux : un enjeu structurant que personne ne
     soulève est retenu aussi. Une moyenne entre 3 et 0 donnerait un tiède 1,5
     qui efface exactement l'information qu'il fallait porter.

  3. L'ABSENCE N'EST PAS UN ZÉRO. Un enjeu non noté est « non instruit » — ni
     retenu ni écarté. Le faire basculer en « écarté » ferait disparaître du
     livrable tout ce qu'on n'a pas regardé, et un document muet sur ses trous
     se lit comme un document complet.

  4. LE CONTEXTE DE SITE RELÈVE, IL N'ABAISSE JAMAIS. Un bassin peu tendu ne
     rend pas l'eau sans objet ; il la rend moins contraignante, et c'est
     l'étude qui le chiffrera. Un formulaire qui abaisserait un niveau
     scientifique laisserait le client désarmer un enjeu par une case.

  5. LA FRONTIÈRE OUVERT / FERMÉ. Le questionnaire et le calcul sont ouverts ;
     l'EXPORT ne l'est pas — le document porte le nom du client, son site et
     ses arbitrages.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import strategie_dd as S  # noqa: E402
import app as A  # noqa: E402

PROFIL = {"puissance_it_kw": 20000, "pays": "FR",
          "refroidissement": "tour_evaporative", "taux_charge": 0.7}


def notes(**kw):
    """Un jeu de réponses : {enjeu: (raison_etre, parties_prenantes, valeur)}."""
    return {"notes": {k: {"raison_etre": v[0], "parties_prenantes": v[1],
                          "valeur": v[2]} for k, v in kw.items()}}


@pytest.fixture
def client():
    return A.app.test_client()


# ── 1. La science n'est pas une opinion du client ──────────────────────────

def test_le_questionnaire_ne_propose_jamais_de_noter_la_science():
    q = S.questionnaire()
    for e in q["enjeux"]:
        assert "science" not in e["a_noter"], e["cle"]
        assert set(e["a_noter"]) == set(S.CLES_CLIENT)


def test_la_perspective_scientifique_est_declaree_etablie_par_les_donnees():
    p = {x["cle"]: x for x in S.questionnaire()["perspectives"]}
    assert p["science"]["source"] == "donnees"
    for autre in ("raison_etre", "parties_prenantes", "valeur"):
        assert p[autre]["source"] == "client"


def test_une_note_scientifique_glissee_par_le_client_reste_sans_effet():
    """LE contrôle du module : on tente exactement la triche redoutée."""
    honnete = S.strategie(notes(pue=(1, 1, 1)))
    triche = dict(notes(pue=(1, 1, 1)))
    triche["notes"]["pue"]["science"] = 0
    force = S.strategie(triche)
    ref = [l for l in honnete["lignes"] if l["cle"] == "pue"][0]
    vu = [l for l in force["lignes"] if l["cle"] == "pue"][0]
    assert vu["notes"]["science"] == ref["notes"]["science"] == 3
    assert vu["verdict"] == ref["verdict"]


def test_le_module_refuse_que_la_science_devienne_une_question_client(monkeypatch):
    persp = []
    for p in S.PERSPECTIVES:
        c = dict(p)
        if c["cle"] == "science":
            c["source"] = "client"
        persp.append(c)
    monkeypatch.setattr(S, "PERSPECTIVES", persp)
    monkeypatch.setattr(S, "_PERSP", {p["cle"]: p for p in persp})
    fautes = S._verifier()
    assert any("ne peut pas être remplie" in f for f in fautes), fautes


def test_la_sante_est_verte_en_etat_normal():
    assert S.sante()["problemes"] == []


# ── 2. Les divergences ne sont pas moyennées ───────────────────────────────

def test_l_opinion_devant_les_donnees_retient_l_enjeu():
    """Le cas de la capsule de café, transposé au bruit : impact global
    modeste, gêne quotidienne réelle. Tant que l'opinion le tient pour l'enjeu
    principal, c'est un problème qui doit être traité."""
    s = S.strategie(notes(bruit=(1, 3, 1)))
    l = [x for x in s["lignes"] if x["cle"] == "bruit"][0]
    assert l["notes"]["science"] == 1
    assert l["verdict"] == "perception", l["verdict"]
    assert l in s["retenus"]


def test_les_donnees_devant_l_opinion_retiennent_l_enjeu():
    """Le cas symétrique, et le plus dangereux parce qu'il est silencieux :
    le carbone incorporé est structurant et personne ne le soulève."""
    s = S.strategie(notes(carbone_incorpore=(1, 0, 1)))
    l = [x for x in s["lignes"] if x["cle"] == "carbone_incorpore"][0]
    assert l["notes"]["science"] == 3
    assert l["verdict"] == "donnees", l["verdict"]
    assert l in s["retenus"]


def test_les_deux_ecarts_sont_nommes_dans_la_tension():
    s = S.strategie(notes(bruit=(1, 3, 1), carbone_incorpore=(1, 0, 1)))
    t = [x for x in s["tensions"] if x["cle"] == "perception_realite"][0]
    assert [x["cle"] for x in t["opinion_devant_les_donnees"]] == ["bruit"]
    assert "carbone_incorpore" in [x["cle"] for x in t["donnees_devant_l_opinion"]]
    assert "silencieux" in t["lecture"]


def test_la_raison_d_etre_seule_suffit_a_retenir_un_enjeu():
    """Ni les parties prenantes ni le compte de résultat ne l'imposent :
    l'entreprise le porte parce qu'il correspond à ce qu'elle défend."""
    s = S.strategie(notes(emploi_local=(3, 1, 0)))
    l = [x for x in s["lignes"] if x["cle"] == "emploi_local"][0]
    assert l["verdict"] == "raison_etre"
    t = [x for x in s["tensions"] if x["cle"] == "exterieur_interieur"][0]
    assert "emploi_local" in [x["cle"] for x in t["porte_de_l_interieur"]]


def test_un_enjeu_tire_du_dehors_est_signale_comme_tel():
    s = S.strategie(notes(raccordement=(0, 3, 3)))
    t = [x for x in s["tensions"] if x["cle"] == "exterieur_interieur"][0]
    assert "raccordement" in [x["cle"] for x in t["tire_du_dehors"]]
    assert "sans conviction" in t["lecture"]


# ── 3. L'absence n'est pas un zéro ─────────────────────────────────────────

def test_un_enjeu_non_note_est_non_instruit_et_non_ecarte():
    s = S.strategie({"notes": {}})
    for l in s["lignes"]:
        assert l["verdict"] == "non_instruit", l["cle"]
    assert s["retenus"] == []
    assert s["par_verdict"]["ecarte"] == []


def test_une_perspective_manquante_suffit_a_rendre_l_enjeu_non_instruit():
    s = S.strategie({"notes": {"pue": {"raison_etre": 3,
                                       "parties_prenantes": 3}}})
    l = [x for x in s["lignes"] if x["cle"] == "pue"][0]
    assert l["verdict"] == "non_instruit"
    assert l["manquantes"] == ["Valeur commerciale"]


def test_les_non_instruits_figurent_au_programme_d_etude():
    """Un trou qui n'apparaît pas dans le plan de travail ne se comblera
    jamais."""
    s = S.strategie(notes(pue=(3, 3, 3)))
    cles = [t["cle"] for t in s["programme"]]
    assert "bruit" in cles
    ligne = [t for t in s["programme"] if t["cle"] == "bruit"][0]
    assert ligne["motif"] == "Non instruit"
    assert "Instruire" in ligne["outil"]


def test_le_client_ne_peut_pas_ecarter_un_enjeu_que_les_donnees_portent():
    """Noter zéro partout n'efface pas ce que les données établissent : l'enjeu
    passe « à surveiller », jamais « écarté »."""
    s = S.strategie(notes(frigorigenes=(0, 0, 0)))
    l = [x for x in s["lignes"] if x["cle"] == "frigorigenes"][0]
    assert l["notes"]["science"] == 2
    assert l["verdict"] == "surveiller", l["verdict"]


def test_un_enjeu_que_rien_ne_porte_est_ecarte_explicitement():
    """L'arbitrage doit être possible — sinon le document ne dit jamais non."""
    s = S.strategie(notes(emploi_local=(0, 0, 0)))
    l = [x for x in s["lignes"] if x["cle"] == "emploi_local"][0]
    assert l["notes"]["science"] == 1
    assert l["verdict"] == "ecarte"


# ── 4. Le contexte relève, il n'abaisse jamais ─────────────────────────────

def test_le_contexte_de_site_releve_le_niveau_scientifique():
    base = S.strategie(notes(bruit=(1, 1, 1)))
    tendu = S.strategie(dict(notes(bruit=(1, 1, 1)),
                             contexte={"voisinage": "tres_eleve"}))
    n0 = [l for l in base["lignes"] if l["cle"] == "bruit"][0]["notes"]["science"]
    n1 = [l for l in tendu["lignes"] if l["cle"] == "bruit"][0]["notes"]["science"]
    assert n0 == 1 and n1 == 3, (n0, n1)


def test_aucun_contexte_n_abaisse_un_niveau_scientifique():
    """Le contrôle qui compte : on balaie TOUTES les options de TOUS les
    contextes et on exige qu'aucune ne fasse descendre un enjeu. Une case du
    formulaire qui désarmerait un enjeu serait une porte de sortie."""
    ref = {l["cle"]: l["notes"]["science"]
           for l in S.strategie({"notes": {}})["lignes"]}
    for c in S.CONTEXTE:
        for opt, _ in c["options"]:
            s = S.strategie({"notes": {}, "contexte": {c["cle"]: opt}})
            for l in s["lignes"]:
                assert l["notes"]["science"] >= ref[l["cle"]], (
                    c["cle"], opt, l["cle"])


def test_un_contexte_non_renseigne_le_dit_au_lieu_de_supposer():
    s = S.strategie({"notes": {}})
    l = [x for x in s["lignes"] if x["cle"] == "eau_site"][0]
    assert l["science_motif"] and "non renseigné" in l["science_motif"]


def test_le_module_refuse_un_contexte_qui_ne_module_rien(monkeypatch):
    ctx = list(S.CONTEXTE) + [{"cle": "orphelin", "nom": "Sans effet",
                               "options": [("faible", "Faible")],
                               "pourquoi": "…"}]
    monkeypatch.setattr(S, "CONTEXTE", ctx)
    monkeypatch.setattr(S, "_CONTEXTE", {c["cle"]: c for c in ctx})
    fautes = S._verifier()
    assert any("sans effet" in f for f in fautes), fautes


# ── 5. Le registre, et ce qui le rend utilisable ───────────────────────────

def test_chaque_enjeu_porte_son_piege_et_son_outil():
    """Le piège est ce qui distingue un registre d'une liste de mots ; l'outil
    est ce qui relie le document à l'étude qui suit."""
    for e in S.ENJEUX:
        assert len(e["piege"]) > 60, e["cle"]
        assert len(e["outil"]) > 20, e["cle"]
        assert len(e["dit"]) > 60, e["cle"]


def test_les_enjeux_qui_debordent_l_entreprise_appellent_une_coalition():
    """Traiter seul un enjeu de réseau, de bassin ou de filière revient à en
    porter le coût sans en obtenir l'effet."""
    s = S.strategie(notes(raccordement=(3, 3, 3), pue=(3, 3, 3)))
    par = {l["cle"]: l for l in s["lignes"]}
    assert par["raccordement"]["mode"] == "coalition"
    assert par["pue"]["mode"] == "investir"


def test_le_registre_couvre_les_sept_familles():
    assert set(S.sante()["par_famille"]) == set(S.FAMILLES)


def test_les_grandeurs_du_moteur_sont_chiffrees_quand_le_profil_existe():
    s = S.strategie(notes(pue=(3, 3, 3)), PROFIL)
    l = [x for x in s["lignes"] if x["cle"] == "pue"][0]
    assert s["profil_chiffre"] is True
    assert l["chiffre"] and l["chiffre"]["valeur"]


def test_sans_profil_aucune_grandeur_n_est_inventee():
    s = S.strategie(notes(pue=(3, 3, 3)))
    assert s["profil_chiffre"] is False
    assert all(l["chiffre"] is None for l in s["lignes"])


# ── 6. Les alertes disent ce qu'on préférerait ne pas lire ─────────────────

def test_la_dispersion_est_signalee_au_dela_du_seuil():
    """Une stratégie qui retient vingt enjeux n'en retient aucun."""
    tout = {c: (3, 3, 3) for c in [e["cle"] for e in S.ENJEUX]}
    s = S.strategie(notes(**tout))
    assert len(s["retenus"]) > S.SEUIL_DISPERSION
    assert any("dispersion" in a["titre"] for a in s["alertes"]), s["alertes"]


def test_l_absence_d_arbitrage_est_signalee():
    s = S.strategie(notes(pue=(3, 3, 3)))
    assert any("Aucun enjeu écarté" in a["titre"] for a in s["alertes"])


def test_les_non_instruits_sont_signales_en_alerte_haute():
    s = S.strategie({"notes": {}})
    al = [a for a in s["alertes"] if "non instruit" in a["titre"]]
    assert al and al[0]["gravite"] == "haute"


# ── 7. Le livrable rédigé ──────────────────────────────────────────────────

def test_le_livrable_porte_les_chapitres_de_la_methode():
    s = S.strategie(notes(pue=(3, 3, 3), bruit=(1, 3, 1),
                          emploi_local=(0, 0, 0)), PROFIL)
    md = S.markdown(s)
    for titre in ["Ce que nous défendons",
                  "Ce que les parties prenantes nous disent",
                  "Ce que les données disent",
                  "Ce qui affecte nos résultats",
                  "Les deux tensions",
                  "La matérialité au croisement des quatre perspectives",
                  "Ce que nous écartons",
                  "Ce qui n'a pas été instruit",
                  "Le programme d'étude"]:
        assert titre in md, titre


def test_le_livrable_nomme_ce_qui_est_ecarte():
    """La moitié difficile : sans elle, le document n'a pas arbitré."""
    md = S.markdown(S.strategie(notes(emploi_local=(0, 0, 0), pue=(3, 3, 3))))
    assert "Emploi local" in md.split("Ce que nous écartons")[1][:900]


def test_le_livrable_dit_qu_il_ne_decerne_aucun_label():
    md = S.markdown(S.strategie({"notes": {}}))
    assert "aucune conformité" in md and "vérificateur accrédité" in md


def test_le_livrable_dit_pourquoi_la_science_n_a_pas_ete_demandee():
    md = S.markdown(S.strategie({"notes": {}}))
    assert "ne vous a pas été demandée" in md


def test_les_nombres_du_livrable_sont_ecrits_en_francais():
    """Une virgule oubliée fait passer un livrable pour une traduction
    automatique, et c'est ce qu'un évaluateur voit avant le fond."""
    md = S.markdown(S.strategie(notes(pue=(3, 3, 3)), PROFIL))
    ligne = [l for l in md.split("\n") if "Énergie totale annuelle" in l]
    assert ligne, "grandeur absente du livrable"
    assert "." not in ligne[0].split(":")[-1].split("MWh")[0], ligne[0]


# ── 8. La frontière ouvert / fermé ─────────────────────────────────────────

def test_la_page_et_le_questionnaire_sont_ouverts(client):
    for chemin in ("/strategie-durable-datacenter",
                   "/api/datacenter/strategie/questionnaire"):
        r = client.get(chemin)
        assert r.status_code == 200, (chemin, r.status_code)


def test_le_calcul_est_ouvert(client):
    r = client.post("/api/datacenter/strategie",
                    headers={"Origin": "http://localhost"},
                    json=notes(pue=(3, 3, 3)))
    assert r.status_code == 200
    assert r.get_json()["ok"] is True


def test_l_export_du_livrable_reste_ferme(client):
    """Le document porte le nom du client, son site et ses arbitrages : c'est
    une pièce de dossier, pas une page publique."""
    r = client.post("/api/datacenter/strategie/export",
                    headers={"Origin": "http://localhost"},
                    json=dict(notes(pue=(3, 3, 3)), format="docx"))
    assert r.status_code == 401, r.status_code


def test_ouvrir_le_questionnaire_n_a_rien_ouvert_d_autre(client):
    for chemin in ("/api/datacenter/ingenierie/dossier",
                   "/api/datacenter/export"):
        r = client.post(chemin, headers={"Origin": "http://localhost"}, json={})
        assert r.status_code == 401, chemin


def test_la_page_conduit_depuis_la_page_sustainability():
    with open(os.path.join(ICI, "datacenter.html"), encoding="utf-8") as f:
        assert 'href="/strategie-durable-datacenter"' in f.read()


def test_la_page_porte_les_sections_du_questionnaire():
    with open(os.path.join(ICI, "strategie-durable-datacenter.html"),
              encoding="utf-8") as f:
        h = f.read()
    for cible in ('id="sd-persp"', 'id="sd-identite"', 'id="sd-contexte"',
                  'id="sd-ouvertes"', 'id="sd-enjeux"', 'id="sd-resultat"'):
        assert cible in h, cible
    assert 'content="index, follow"' in h
