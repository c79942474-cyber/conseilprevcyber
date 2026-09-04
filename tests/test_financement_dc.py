# -*- coding: utf-8 -*-
"""Qui porte l'enveloppe : les familles, le coût de portage, les pièces dues.

CE QUE CES RÈGLES PROTÈGENT EN PRIORITÉ. Un module qui parle d'argent attire
deux fautes, et elles sont silencieuses toutes les deux.

  · LE TAUX INVENTÉ. Un coût de la dette écrit quelque part dans le code
    devient, en deux lectures, le taux du projet — parce qu'un formulaire déjà
    rempli ne se conteste pas, et qu'un plan de financement bâti dessus se
    présente en comité comme s'il avait été négocié. Une règle interdit donc
    tout taux embarqué, en mesurant le CODE et pas seulement les sorties.

  · LE POURCENTAGE PRIS POUR UNE FRACTION. Le formulaire demande « 5,5 » et le
    calcul attend 0,055. Sans conversion, l'annuité sort cent fois trop grande
    — et reste un nombre, donc crédible. La conversion est mesurée sur la
    route, pas seulement supposée.

ET UNE FAUTE DE CONCEPTION DÉJÀ CORRIGÉE, gardée ici en témoin : le
rapprochement des exigences se faisait sur le TEXTE, rédigé famille par
famille. Aucune formulation n'étant identique, « exigences communes » valait
zéro quel que soit le tour de table, et la fonction la plus utile du module ne
se déclenchait jamais sans que rien ne le signale.
"""
import io
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import financement_dc as F  # noqa: E402


def _lire(nom):
    return io.open(os.path.join(ICI, nom), encoding="utf-8").read()


TOUTES = list(F.ORDRE_SOURCES)


# ══════════════════════════════════════════════════════════════════════════
# 0. Le garde-fou
# ══════════════════════════════════════════════════════════════════════════

def test_le_referentiel_porte_ce_que_les_regles_mesurent():
    assert len(F.SOURCES) >= 6, len(F.SOURCES)
    assert len(F.EXIGENCES) >= 15, len(F.EXIGENCES)
    assert sorted(F.ORDRE_SOURCES) == sorted(F.SOURCES)


# ══════════════════════════════════════════════════════════════════════════
# 1. AUCUN TAUX N'EST EMBARQUÉ — la règle qui tient tout le module
# ══════════════════════════════════════════════════════════════════════════

def test_aucun_taux_ni_rendement_n_est_ecrit_dans_le_module():
    """LA RÈGLE MESURE LE CODE, pas une sortie. Un taux glissé dans une valeur
    par défaut ne se verrait sur aucun résultat tant que personne ne laisse le
    champ vide — et le jour où quelqu'un le laisse vide, il obtient un chiffre
    qu'il croira négocié.

    Elle cherche les FORMES qu'un taux prend : une fraction décimale
    plausible en valeur par défaut d'argument, et les mots du métier associés
    à un nombre.
    """
    src = _lire("financement_dc.py")
    # Aucune valeur par défaut numérique sur les arguments de taux.
    for arg in ("taux_dette", "rendement_fonds_propres", "part_dette"):
        mauvais = re.findall(r"\b%s\s*=\s*([0-9][0-9.,]*)" % arg, src)
        assert not mauvais, (arg, mauvais)
    # AUCUNE FRACTION DÉCIMALE STRICTEMENT ENTRE 0 ET 1, quelle qu'elle soit.
    #
    # LA PREMIÈRE VERSION NE CHERCHAIT QUE `0.0x` : elle attrapait un coût de
    # dette à 5,5 % et laissait passer un rendement de fonds propres à 11 %,
    # écrit `0.11`. Une règle qui ne couvre que la moitié basse de la plage
    # qu'elle prétend interdire est pire qu'absente — elle rassure. Une
    # mutation l'a montré ; le motif porte désormais sur toute la plage.
    #
    # Les bornes `0.0` et `1.0` du contrôle de validité sont admises : ce ne
    # sont pas des taux, ce sont les extrémités d'un intervalle, et les
    # exclure du filtre est déclaré ici plutôt que subi.
    suspects = [x for x in re.findall(r"(?<![\w.])0\.\d+(?![\w.])", src)
                if x not in ("0.0",)]
    assert not suspects, (
        "des fractions ressemblant à des taux figurent dans le module : %s. "
        "Aucun taux ne s'écrit ici : il se relève sur une offre." % suspects)


def test_sans_taux_declare_le_portage_n_est_pas_calcule():
    """Une valeur par défaut deviendrait la réponse."""
    p = F.portage(enveloppe_eur=45_000_000)
    assert p["ok"] is False and p["verdict"] == "indetermine", p
    joints = " ".join(p["manques"])
    assert "taux de la dette" in joints and "rendement" in joints, p["manques"]


def test_un_portage_complet_est_calcule_et_l_arithmetique_tient():
    """L'annuité constante, vérifiée contre sa formule — pas contre elle-même.

    UNE RÈGLE QUI RAPPELLERAIT LA FONCTION POUR SE COMPARER À ELLE-MÊME serait
    verte quelle que soit la formule employée."""
    E, d, i, n, ke = 45_000_000.0, 0.65, 0.055, 15.0, 0.11
    p = F.portage(E, d, i, n, ke, puissance_it_kw=10_000)
    dette = E * d
    attendue = dette * i / (1.0 - (1.0 + i) ** (-n))
    assert abs(p["annuite_dette_eur"] - round(attendue, 2)) < 0.01, p
    assert abs(p["dette_eur"] - dette) < 0.01
    assert abs(p["fonds_propres_eur"] - (E - dette)) < 0.01
    assert abs(p["cmpc"] - (d * i + (1 - d) * ke)) < 1e-9
    assert p["cout_annuel_par_kw"] == round(p["cout_annuel_capital_eur"] / 10_000, 2)
    # Le surcoût de la dette est positif à taux positif : un signe inversé
    # ferait annoncer que la dette RAPPORTE.
    assert p["surcout_dette_eur"] > 0, p["surcout_dette_eur"]


def test_un_taux_nul_ne_fait_pas_tomber_le_calcul():
    """La formule générale divise par zéro à taux nul. Un projet financé à
    taux nul est rare, pas impossible — et une exception ferait disparaître
    tout le bloc, pas seulement une ligne."""
    p = F.portage(10_000_000.0, 0.5, 0.0, 10.0, 0.08)
    assert p["ok"] is True
    assert abs(p["annuite_dette_eur"] - 500_000.0) < 0.01, p["annuite_dette_eur"]
    assert abs(p["surcout_dette_eur"]) < 0.01


def test_une_part_de_dette_hors_bornes_est_refusee():
    """Une part saisie en pourcentage plutôt qu'en fraction — 65 au lieu de
    0,65 — donnerait une dette cent fois l'enveloppe, et des fonds propres
    NÉGATIFS. Le calcul continuerait, et le résultat resterait un nombre."""
    for mauvaise in (65.0, -0.2, 1.5):
        with pytest.raises(ValueError):
            F.portage(1_000_000.0, mauvaise, 0.05, 10.0, 0.1)


def test_le_resultat_emporte_ses_hypotheses_et_ses_reserves():
    """Un coût du capital sans ses hypothèses ne se conteste pas — et les
    deux moitiés ne se paient pas de la même façon."""
    p = F.portage(1_000_000.0, 0.5, 0.05, 10.0, 0.1)
    assert p["hypotheses"]["taux_dette"] == 0.05
    joints = " ".join(p["reserves"])
    assert "avant impôt" in joints.lower(), joints
    assert "exigible" in joints, joints
    assert "intérêts pendant la construction" in joints, joints


# ══════════════════════════════════════════════════════════════════════════
# 2. Les familles — ce qu'elles cherchent, et ce qu'elles ne feront pas
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cle", sorted(F.SOURCES))
def test_chaque_famille_dit_ce_qu_elle_cherche_et_ce_qu_elle_refusera(cle):
    """UNE FAMILLE SANS LIMITE laisse croire qu'on peut tout lui demander —
    et c'est ainsi qu'on prépare un dossier pour un interlocuteur qui ne le
    lira pas."""
    v = F.SOURCES[cle]
    for champ in ("cherche", "apporte", "change", "ne_fera_pas"):
        assert len((v.get(champ) or "").strip()) > 60, (cle, champ)
    bas, haut = v["horizon_ans"]
    assert 0 < bas < haut <= 40, (cle, v["horizon_ans"])


@pytest.mark.parametrize("cle", sorted(F.SOURCES))
def test_chaque_famille_designe_des_exigences_du_catalogue(cle):
    """LES EXIGENCES SONT DÉSIGNÉES, JAMAIS RÉDIGÉES SUR PLACE. Rédigées, deux
    familles demandant la même chose l'écrivent différemment et le
    rapprochement ne se fait plus — c'est la faute que ce module a commise."""
    exige = F.SOURCES[cle]["exige"]
    assert exige, cle
    inconnues = [e for e in exige if e not in F.EXIGENCES]
    assert not inconnues, (cle, inconnues)


def test_l_investisseur_public_ne_nomme_aucun_dispositif():
    """LES GUICHETS CHANGENT PLUS VITE QU'UN RÉFÉRENTIEL. Décrire un
    dispositif nommé, c'est publier une information qui sera fausse dans six
    mois et qu'un lecteur opposera à l'institution."""
    v = F.SOURCES["investisseur_public_national"]
    texte = " ".join(str(x) for x in v.values())
    assert v.get("reserve"), "l'investisseur public ne porte aucune réserve"
    assert "vérifie auprès de l'institution" in v["reserve"], v["reserve"]
    # Aucun nom de dispositif, de guichet ou de plan.
    for interdit in ("France 2030", "PIA", "prêt vert", "France Num"):
        assert interdit.lower() not in texte.lower(), interdit


def test_le_cadrage_dit_qu_il_n_est_pas_un_conseil_financier():
    t = F.SOURCES_SOURCE
    assert "pas un conseil financier" in t.lower(), t
    assert "aucun taux" in t.lower(), t


# ══════════════════════════════════════════════════════════════════════════
# 3. Les exigences — le rapprochement se fait, et il sert à quelque chose
# ══════════════════════════════════════════════════════════════════════════

def test_le_rapprochement_des_exigences_se_declenche_reellement():
    """LE TÉMOIN DE LA FAUTE CORRIGÉE. Le rapprochement se faisait sur le
    texte : « exigences communes » valait zéro quel que soit le tour de table,
    et la fonction la plus utile du module ne servait jamais. Une règle qui
    n'aurait vérifié que la présence de la clé « communes » serait restée
    verte pendant tout ce temps."""
    e = F.exigences(TOUTES)
    assert e["ok"] is True
    assert len(e["communes"]) >= 3, e["communes"]
    # Et la plus demandée l'est par plusieurs familles nommées.
    tete = e["exigences"][0]
    assert tete["nombre"] >= 3, tete
    assert len(set(tete["demandee_par"])) == tete["nombre"], tete


def test_les_exigences_sont_triees_par_nombre_de_demandeurs():
    """Une pièce demandée par un seul se négocie ; une pièce demandée par tous
    ne se négocie pas. C'est ce qui décide de l'ordre de production."""
    liste = F.exigences(TOUTES)["exigences"]
    nombres = [x["nombre"] for x in liste]
    assert nombres == sorted(nombres, reverse=True), nombres


def test_les_livrables_d_ingenierie_sortent_a_part():
    """C'EST LA PARTIE QUI CONCERNE UN INGÉNIEUR. Ces pièces se commandent en
    phase d'étude ou ne se produisent pas à temps ; noyées dans une liste de
    quatorze, elles se découvrent au tour de table."""
    e = F.exigences(TOUTES)
    techniques = e["livrables_techniques"]
    assert len(techniques) >= 4, techniques
    assert all(x["nature"] == "technique" for x in techniques)
    # Et elles portent la raison d'être qui justifie de les commander tôt.
    for x in techniques:
        assert len(x["pourquoi"]) > 80, x["cle"]


def test_sans_famille_retenue_rien_n_est_affirme():
    """Les pièces à produire dépendent ENTIÈREMENT de qui les demande : en
    rendre une liste par défaut ferait préparer un dossier pour personne."""
    e = F.exigences([])
    assert e["ok"] is False
    assert e["exigences"] == []


@pytest.mark.parametrize("cle", sorted(F.EXIGENCES))
def test_chaque_exigence_dit_sa_nature_et_pourquoi_elle_est_demandee(cle):
    v = F.EXIGENCES[cle]
    assert v["nature"] in F.NATURES_EXIGENCE, (cle, v["nature"])
    assert len(v["intitule"]) > 30, cle
    assert len(v["pourquoi"]) > 80, cle


def test_aucune_exigence_du_catalogue_n_est_orpheline():
    """Une exigence que personne ne demande a survécu à la famille qui la
    demandait : elle gonfle le catalogue sans jamais sortir."""
    demandees = set()
    for v in F.SOURCES.values():
        demandees.update(v["exige"])
    orphelines = sorted(set(F.EXIGENCES) - demandees)
    assert not orphelines, orphelines


# ══════════════════════════════════════════════════════════════════════════
# 4. Les horizons — la sortie s'organise au montage, pas en cours de vie
# ══════════════════════════════════════════════════════════════════════════

def test_un_horizon_plus_court_que_la_detention_fait_ressortir_une_sortie():
    h = F.horizon_compatible(["dette_privee", "fonds_pension"], 25)
    a_organiser = [l["cle"] for l in h["a_organiser"]]
    assert "dette_privee" in a_organiser, h["lignes"]
    assert "fonds_pension" not in a_organiser, h["lignes"]


def test_un_horizon_plus_long_que_le_projet_est_signale_aussi():
    """LE TÉMOIN NÉGATIF : un module qui ne verrait que les sorties trop
    courtes laisserait préparer un dossier pour un fonds de pension sur un
    projet de cinq ans, qui ne sera pas instruit."""
    h = F.horizon_compatible(["fonds_pension"], 5)
    assert h["lignes"][0]["ecart"] == "horizon_plus_long_que_le_projet", h


def test_sans_duree_de_detention_aucun_ecart_n_est_affirme():
    h = F.horizon_compatible(["dette_privee"], None)
    assert h["lignes"][0]["ecart"] is None
    assert h["note"], h


# ══════════════════════════════════════════════════════════════════════════
# 5. La route et la page
# ══════════════════════════════════════════════════════════════════════════

def test_la_route_convertit_les_pourcentages_en_fractions(connecte):
    """LE PIÈGE SILENCIEUX. Le formulaire demande « 5,5 » et le calcul attend
    0,055. Sans conversion, l'annuité sort cent fois trop grande — et reste un
    nombre, donc crédible. On mesure la SORTIE, pas la présence d'une
    fonction."""
    r = connecte.post("/api/datacenter/financement", json={
        "enveloppe_eur": 10_000_000, "part_dette_pct": 50,
        "taux_dette_pct": 5, "duree_dette_ans": 10,
        "rendement_fonds_propres_pct": 10,
    }, headers={"Origin": "http://localhost"})
    assert r.status_code == 200, r.status_code
    p = r.get_json()["etude"]["portage"]
    assert p["ok"] is True, p
    assert p["hypotheses"]["taux_dette"] == 0.05, p["hypotheses"]
    assert p["hypotheses"]["part_dette"] == 0.5, p["hypotheses"]
    # 5 M€ à 5 % sur 10 ans : l'annuité tient dans la centaine de milliers,
    # pas dans les dizaines de millions.
    assert 600_000 < p["annuite_dette_eur"] < 700_000, p["annuite_dette_eur"]


def test_la_route_refuse_une_part_de_dette_absurde_sans_tomber(connecte):
    r = connecte.post("/api/datacenter/financement",
                      json={"enveloppe_eur": 1_000_000, "part_dette_pct": 650,
                            "taux_dette_pct": 5, "duree_dette_ans": 10,
                            "rendement_fonds_propres_pct": 10},
                      headers={"Origin": "http://localhost"})
    assert r.status_code == 400, r.status_code
    assert r.get_json()["error"] == "saisie"


def test_un_visiteur_anonyme_n_atteint_pas_la_route(anonyme):
    r = anonyme.post("/api/datacenter/financement", json={},
                     headers={"Origin": "http://localhost"})
    assert r.status_code in (401, 403), r.status_code


def test_le_bloc_existe_dans_la_section_du_chiffrage():
    """Le financement est une LECTURE de l'enveloppe : hors de la section qui
    la produit, il redemanderait un montant déjà calculé."""
    h = _lire("ingenierie-datacenter.html")
    deb = h.index('id="ig-eco"')
    corps = h[deb:h.index("</section>", deb)]
    for ancre in ('id="ig-fin"', 'id="ig-fin-familles"', 'id="ig-fin-env"',
                  'id="ig-fin-go"', 'id="ig-fin-out"'):
        assert ancre in corps, ancre


def test_la_page_ne_propose_aucun_taux_par_defaut():
    """UN PLACEHOLDER CHIFFRÉ FAIT OFFICE DE RECOMMANDATION au bout de deux
    lectures — et il ne se conteste pas, puisqu'il n'est affirmé nulle part."""
    h = _lire("ingenierie-datacenter.html")
    deb = h.index('id="ig-fin"')
    corps = h[deb:h.index("</details>", deb)]
    for champ in ("ig-fin-td", "ig-fin-rfp", "ig-fin-pd"):
        i = corps.index('id="%s"' % champ)
        balise = corps[corps.rindex("<input", 0, i):corps.index(">", i) + 1]
        assert "value=" not in balise, (champ, balise)
        m = re.search(r'placeholder="([^"]*)"', balise)
        assert m and not re.search(r"\d", m.group(1)), (champ, balise)


def test_un_total_de_maintenance_n_est_pas_repris_en_enveloppe():
    """UNE MAINTENANCE REND UN COÛT ANNUEL. Le porter en enveloppe
    d'investissement produirait un plan de financement sur un nombre qui ne
    veut rien dire — et il aurait l'air juste. Le refus doit être DIT : un
    champ qui reste vide sans explication se remplit à la main avec le même
    mauvais chiffre."""
    h = _lire("ingenierie-datacenter.html")
    i = h.index("document.addEventListener('ig-chiffrage'")
    corps = h[i:i + 1800]
    assert "d.annuel" in corps, corps[:300]
    assert "MAINTENANCE" in corps, corps[:600]


def test_le_referentiel_du_financement_est_servi_avec_celui_de_l_economiste(connecte):
    """Servi par un second appel, la liste des familles s'afficherait APRÈS le
    résultat du chiffrage — c'est-à-dire après que le lecteur a refermé."""
    j = connecte.get("/api/datacenter/economiste").get_json()
    assert j["ok"] and j.get("financement"), sorted(j)
    assert set(j["financement"]["sources"]) == set(F.SOURCES)
